import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'python'))
from anchor_core import check_html


# Expectations describe browser-visible article targets, not implementation steps.
CASES = [
    ("valid", '<a href="#ok">go</a><h2 id="ok">OK</h2>', []),
    ("missing", '<a href="#gone">go</a>', ["missing_target"]),
    ("arabic", '<a href="#مقارنة">go</a><h2 id="مقارنة">OK</h2>', []),
    ("encoded_arabic", '<a href="#%D9%85%D9%82%D8%A7%D8%B1%D9%86%D8%A9">go</a><h2 id="مقارنة">OK</h2>', []),
    ("entities", '<a href="#a&amp;b">go</a><h2 id="a&#38;b">OK</h2>', []),
    ("decode_once", '<a href="#%2520">go</a><h2 id="%20">OK</h2>', []),
    ("literal_percent", '<a href="#a%20b">go</a><h2 id="a%20b">OK</h2>', []),
    ("id_not_decoded", '<a href="#a b">go</a><h2 id="a%20b">OK</h2>', ["missing_target"]),
    ("plus_literal", '<a href="#a+b">go</a><h2 id="a+b">OK</h2>', []),
    ("case_sensitive", '<a href="#FOO">go</a><h2 id="foo">OK</h2>', ["missing_target"]),
    ("duplicate", '<h2 id="x">x</h2><h3 id="x">x</h3>', ["duplicate_id", "duplicate_id"]),
    ("ambiguous", '<a href="#x">x</a><h2 id="x">x</h2><h3 id="x">x</h3>', ["ambiguous_target", "duplicate_id", "duplicate_id"]),
    ("empty_fragment", '<a href="#">top</a>', []),
    ("top", '<a href="#TOP">top</a>', []),
    ("text_fragment", '<a href="#:~:text=hello">find</a>', []),
    ("text_fragment_target", '<a href="#gone:~:text=hello">find</a>', ["missing_target"]),
    ("encoded_directive", '<a href="#x%3A~%3Atext%3Dy">go</a><h2 id="x:~:text=y">OK</h2>', []),
    ("external", '<a href="https://example.com/#gone">go</a>', []),
    ("relative_page", '<a href="other.html#gone">go</a>', []),
    ("comments", '<!-- <a href="#gone"><h2 id="x"> --><h2 id="x">x</h2>', []),
    ("script", '<script>var x = \'<a href="#gone"><h2 id="x">\';</script><h2 id="x">x</h2>', []),
    ("style", '<style>a{content:\'<a href="#gone">\'}</style>', []),
    ("textarea", '<textarea><a href="#gone"><h2 id="x"></textarea><h2 id="x">x</h2>', []),
    ("title", '<title><a href="#gone"></title>', []),
    ("template", '<template><h2 id="x">x</h2><a href="#gone">g</a></template><a href="#x">g</a>', ["missing_target"]),
    ("template_element", '<template id="tpl"><b id="hidden">x</b></template><a href="#tpl">g</a>', []),
    ("nested_template", '<template><template><h2 id="x">x</h2></template></template><a href="#x">g</a>', ["missing_target"]),
    ("legacy_name", '<a href="#old">g</a><a name="old"></a>', []),
    ("single_unquoted", "<a href='#yes'>go</a><h2 id=yes>OK</h2>", []),
    ("upper_attributes", '<A HREF="#x">g</A><H2 ID="x">x</H2>', []),
    ("gutenberg_json_only", '<!-- wp:heading {"anchor":"x"} --><h2>x</h2><!-- /wp:heading --><a href="#x">g</a>', ["missing_target"]),
    ("base", '<base href="https://example.com/"><a href="#x">g</a>', ["base_href"]),
    ("empty_base", '<base href=""><a href="#x">g</a><h2 id="x">x</h2>', []),
    ("duplicate_attributes_first", '<h2 id="x" id="y">x</h2><a href="#x" href="#gone">g</a>', []),
    ("url_whitespace", '<a href=" \n#x\t ">g</a><h2 id="x">x</h2>', []),
    ("hash_in_id", '<a href="#a%23b">g</a><h2 id="a#b">x</h2>', []),
    ("area", '<area href="#gone">', ["missing_target"]),
    ("unicode_not_normalized", '<a href="#e\u0301">g</a><h2 id="é">x</h2>', ["missing_target"]),
    ("empty_ids", '<h2 id="">x</h2><h3 id="">x</h3>', []),
    ("greater_than_quoted", '<a title="a > b" href="#x">g</a><h2 id="x">x</h2>', []),
]


class ArticleChecks(unittest.TestCase):
    def test_positions_after_arabic_and_crlf(self):
        source = 'نص عربي 😀\r\n<a\r\n href="&#35;missing">go</a>'
        issue = check_html(source).issues[0]
        self.assertEqual(source[issue.start:issue.end], "&#35;missing")
        self.assertEqual((issue.line, issue.column), (3, 8))

    def test_literal_id_precedes_decoded_id(self):
        source = '<a href="#x%20y">g</a><b id="x%20y"></b><i id="x y"></i><em id="x y"></em>'
        self.assertEqual([x.kind for x in check_html(source).issues],
                         ["duplicate_id", "duplicate_id"])

    def test_literal_legacy_name_precedes_decoded_id(self):
        source = '<a href="#x%20y">g</a><a name="x%20y"></a><i id="x y"></i><em id="x y"></em>'
        self.assertEqual([x.kind for x in check_html(source).issues],
                         ["duplicate_id", "duplicate_id"])

    def test_counts(self):
        result = check_html('<a href="#ok">g</a><a href="#">t</a><a href="/else#x">e</a><h2 id="ok">x</h2>')
        self.assertEqual((result.links_checked, result.ids_count, result.links_skipped), (1, 1, 1))

    def test_example_is_useful(self):
        source = (pathlib.Path(__file__).resolve().parents[1] / 'examples' / 'article.html').read_text(encoding='utf-8')
        result = check_html(source)
        self.assertEqual(result.links_checked, 4)
        self.assertEqual(len(result.issues), 4)
        self.assertEqual([x.target for x in result.issues if x.kind == 'missing_target'], ['missing'])

    def test_base_still_checks_duplicate_ids(self):
        result = check_html('<base href="/other"><a href="#missing">g</a><b id="x"></b><i id="x"></i>')
        self.assertEqual((result.links_checked, result.links_skipped), (0, 1))
        self.assertEqual(sorted(x.kind for x in result.issues), ['base_href', 'duplicate_id', 'duplicate_id'])


def _case_test(source, expected):
    def test(self):
        self.assertEqual([x.kind for x in check_html(source).issues], expected)
    return test


for name, source, expected in CASES:
    setattr(ArticleChecks, 'test_' + name, _case_test(source, expected))

if __name__ == '__main__':
    unittest.main()
