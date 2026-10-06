"""JSON stdin/stdout bridge for Vim. Runs locally and never opens a URL."""
import json
import pathlib
import sys

# -I ignores user packages/environment; import only the bundled parser.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from anchor_core import check_html

MAX_BYTES = 2097152
MAX_ISSUES = 500

def report(source):
    if not isinstance(source, str):
        raise ValueError('Source must be a string')
    if len(source.encode('utf-8')) > MAX_BYTES:
        raise ValueError('Source exceeds the 2 MiB limit')
    checked = check_html(source)
    lines = source.split('\n')
    issues = []
    for issue in checked.issues[:MAX_ISSUES]:
        # Vim quickfix columns count UTF-8 bytes, not Unicode code points.
        column = len(lines[issue.line - 1][:issue.column - 1].encode('utf-8')) + 1
        issues.append({'kind': issue.kind, 'line': issue.line, 'column': column,
                       'target': issue.target, 'message': issue.message})
    return {'ok': True, 'issues': issues, 'links_checked': checked.links_checked,
            'links_skipped': checked.links_skipped, 'ids_count': checked.ids_count,
            'total_issues': len(checked.issues), 'truncated': len(checked.issues) > MAX_ISSUES}

def main():
    try:
        # Escaped JSON can occupy up to six bytes per input byte.
        raw = sys.stdin.buffer.read(MAX_BYTES * 6 + 1025)
        if len(raw) > MAX_BYTES * 6 + 1024:
            raise ValueError('Input is too large')
        request = json.loads(raw.decode('utf-8'))
        result = report(request['source'])
    except (ValueError, KeyError, TypeError) as error:
        result = {'ok': False, 'error': str(error)}
    sys.stdout.buffer.write((json.dumps(result, ensure_ascii=True) + '\n').encode('ascii'))
    return 0 if result['ok'] else 1

if __name__ == '__main__':
    sys.exit(main())
