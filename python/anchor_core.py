"""Local, read-only fragment checks for static HTML article source."""

import bisect
import re
from collections import namedtuple
from html import unescape
from html.parser import HTMLParser
from urllib.parse import unquote


Issue = namedtuple("Issue", "kind target start end line column message")
Report = namedtuple("Report", "issues links_checked ids_count links_skipped")
Attribute = namedtuple("Attribute", "value start end")
_TAG = re.compile(r"<\s*[^\s/>]+")
_ATTR = re.compile(
    r'''([^\s=/>]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+)))?'''
)
_RAW = frozenset(("script", "style", "textarea", "title", "xmp", "iframe",
                  "noembed", "noframes", "plaintext"))


def _attributes(raw, offset):
    """Keep the first attribute, as HTML does, with source-value positions."""
    result = {}
    tag = _TAG.match(raw)
    if not tag:
        return result
    for match in _ATTR.finditer(raw, tag.end()):
        name = match.group(1).lower()
        if name in result:
            continue
        group = next((i for i in (2, 3, 4) if match.group(i) is not None), None)
        if group is None:
            result[name] = Attribute("", offset + match.start(1), offset + match.end(1))
        else:
            result[name] = Attribute(unescape(match.group(group)),
                                     offset + match.start(group), offset + match.end(group))
    return result


class _ArticleParser(HTMLParser):
    # These raw-text/RCDATA elements contain text, not article link markup.
    CDATA_CONTENT_ELEMENTS = tuple(_RAW)

    def __init__(self, source):
        HTMLParser.__init__(self, convert_charrefs=True)
        self.line_starts = [0] + [m.end() for m in re.finditer("\n", source)]
        self.ids = {}
        self.names = set()
        self.links = []
        self.base = None
        self.template_depth = 0

    def handle_starttag(self, tag, unused_attrs):
        if self.template_depth:
            if tag == "template":
                self.template_depth += 1
            return
        line, column = self.getpos()
        attrs = _attributes(self.get_starttag_text(), self.line_starts[line - 1] + column)
        if "id" in attrs and attrs["id"].value:
            attr = attrs["id"]
            self.ids.setdefault(attr.value, []).append(attr)
        if tag == "a" and "name" in attrs and attrs["name"].value:
            self.names.add(attrs["name"].value)
        if tag in ("a", "area") and "href" in attrs:
            attr = attrs["href"]
            value = attr.value.translate({9: None, 10: None, 13: None}).strip(" \f")
            if value.startswith("#"):
                self.links.append((value[1:].split(":~:", 1)[0], attr))
        if tag == "base" and "href" in attrs and self.base is None:
            self.base = attrs["href"]
        if tag == "template":
            self.template_depth += 1

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        # In HTML, a slash does not close non-void elements (including template).
        if tag in _RAW:
            self.set_cdata_mode(tag)

    def handle_endtag(self, tag):
        if tag == "template" and self.template_depth:
            self.template_depth -= 1


def check_html(source):
    """Return source diagnostics. ID values are never percent-decoded or normalized.

    Fragments match literally first, then after a single UTF-8 percent decode.
    HTML entities are decoded once by the attribute reader. Case is significant.
    """
    parser = _ArticleParser(source)
    parser.feed(source)
    parser.close()
    issues = []

    def issue(kind, target, attr, message):
        row = bisect.bisect_right(parser.line_starts, attr.start) - 1
        issues.append(Issue(kind, target, attr.start, attr.end, row + 1,
                            attr.start - parser.line_starts[row] + 1, message))

    for target, attrs in parser.ids.items():
        if len(attrs) > 1:
            for attr in attrs:
                issue("duplicate_id", target, attr, "Duplicate id: " + target)

    # Without a document URL, any nonempty base href can change what # refers to.
    base_uncertain = parser.base is not None and parser.base.value.strip()
    checked = skipped = 0
    if base_uncertain and parser.links:
        issue("base_href", parser.base.value, parser.base,
              "Base href present: fragment destinations cannot be verified locally")
    for fragment, attr in parser.links:
        if not fragment:  # # and text-only fragments intentionally require no ID.
            skipped += 1
            continue
        if base_uncertain:
            skipped += 1
            continue
        checked += 1
        candidates = (fragment, unquote(fragment, encoding="utf-8", errors="replace"))
        # Try literal ID/name first, then decoded ID/name, as HTML specifies.
        target = None
        is_id = False
        for candidate in candidates:
            if candidate in parser.ids:
                target, is_id = candidate, True
                break
            if candidate in parser.names:
                target = candidate
                break
        if target is None and any(x.lower() == "top" for x in candidates):
            continue  # Browser-defined document-top fallback.
        if target is None:
            issue("missing_target", candidates[1], attr,
                  "Missing fragment target: #" + candidates[1])
        elif is_id and len(parser.ids[target]) > 1:
            issue("ambiguous_target", target, attr,
                  "Fragment points to a duplicate id: #" + target)
    return Report(tuple(sorted(issues, key=lambda x: (x.start, x.kind))),
                  checked, sum(len(v) for v in parser.ids.values()), skipped)
