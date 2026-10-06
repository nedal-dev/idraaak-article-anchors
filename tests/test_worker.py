import json
import pathlib
import subprocess
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'python'))
from check_article import report

class WorkerChecks(unittest.TestCase):
    def test_utf8_byte_columns(self):
        source = 'نص 😀 <a href="#مفقود">go</a>'
        issue = report(source)['issues'][0]
        self.assertEqual(issue['column'], len(source[:source.index('#')].encode('utf-8')) + 1)
        self.assertEqual(issue['target'], 'مفقود')

    def test_multiline_entity_position(self):
        source = 'عربي\n<a\n href="&#35;missing">go</a>'
        issue = report(source)['issues'][0]
        self.assertEqual((issue['line'], issue['column']), (3, 8))

    def test_utf8_size_limit(self):
        with self.assertRaises(ValueError):
            report('ع' * 1048577)

    def test_diagnostic_limit(self):
        result = report('<a href="#missing">g</a>\n' * 501)
        self.assertEqual((len(result['issues']), result['total_issues'], result['truncated']), (500, 501, True))

    def test_real_worker_process(self):
        source = '<a href="#%D9%82%D8%B3%D9%85">go</a><h2 id="قسم">ok</h2>'
        worker = pathlib.Path(__file__).resolve().parents[1] / 'python' / 'check_article.py'
        done = subprocess.run([sys.executable, '-I', '-B', str(worker)], input=json.dumps({'source': source}).encode('utf-8'), capture_output=True, timeout=5)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(json.loads(done.stdout)['issues'], [])

    def test_invalid_request_is_an_error_not_a_clean_article(self):
        worker = pathlib.Path(__file__).resolve().parents[1] / 'python' / 'check_article.py'
        done = subprocess.run([sys.executable, '-I', '-B', str(worker)], input=b'{bad json', capture_output=True, timeout=5)
        self.assertEqual(done.returncode, 1)
        self.assertFalse(json.loads(done.stdout)['ok'])

if __name__ == '__main__':
    unittest.main()
