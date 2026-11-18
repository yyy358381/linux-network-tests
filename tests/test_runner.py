import csv
import io
import json
import socket
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest.mock import patch
from netcheck.__main__ import main
from netcheck.checks import Result
from netcheck.config import Check
from netcheck.runner import csv_cell, exit_code, run_suite


def result(status):
    return Result('one', 'tcp', 'localhost', 80, 1, status, 'test_reason', 'a,b\nquoted "detail"', '2026-01-01T00:00:00+00:00', 5.0)


class RunnerTests(unittest.TestCase):
    def test_exit_code_precedence(self):
        for states, code in [(['PASS'], 0), (['PASS', 'FAIL'], 1), (['FAIL', 'ERROR'], 2)]:
            with self.subTest(states=states):
                self.assertEqual(exit_code([result(state) for state in states]), code)

    @patch('netcheck.runner.run_check', return_value=result('FAIL'))
    def test_report_files_and_unique_run_folders(self, run):
        with tempfile.TemporaryDirectory() as folder:
            report, output = run_suite([Check('one', 'tcp', 'localhost', 1, 80)], folder)
            self.assertEqual(report['summary'], {'total': 1, 'PASS': 0, 'FAIL': 1, 'ERROR': 0, 'exit_code': 1})
            saved = json.loads((output / 'results.json').read_text())
            self.assertEqual(saved, report)
            with (output / 'results.csv').open(newline='') as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual(rows[0]['detail'], report['results'][0]['detail'])
            log = (output / 'run.log').read_text()
            for event in ('run_started', 'check_started', 'check_finished', 'run_finished'):
                self.assertIn(event, log)
            _, second = run_suite([Check('one', 'tcp', 'localhost', 1, 80)], folder)
            self.assertNotEqual(output, second)
            self.assertTrue((output / 'results.json').exists())

    def test_csv_formula_prefixes(self):
        for value in ('=SUM(1,2)', '+cmd', '-x', '@x', '  =1'):
            self.assertTrue(csv_cell(value).startswith("'"))
        self.assertEqual(csv_cell('hello'), 'hello')

    def test_bad_config_cli_returns_two_without_reports(self):
        with tempfile.TemporaryDirectory() as folder:
            config = Path(folder) / 'bad.json'
            config.write_text('{')
            output = Path(folder) / 'reports'
            with redirect_stderr(io.StringIO()):
                self.assertEqual(main(['--config', str(config), '--output', str(output)]), 2)
            self.assertFalse(output.exists())

    @patch('netcheck.__main__.run_suite', side_effect=PermissionError('read only'))
    def test_unwritable_output_returns_two(self, run):
        with tempfile.TemporaryDirectory() as folder:
            config = Path(folder) / 'valid.json'
            config.write_text(json.dumps({'checks': [{'name': 'one', 'type': 'ping', 'host': 'localhost'}]}))
            with redirect_stderr(io.StringIO()):
                self.assertEqual(main(['--config', str(config)]), 2)

    def test_cli_real_local_checks(self):
        with tempfile.TemporaryDirectory() as folder, socket.socket() as listener, socket.socket() as closed:
            listener.bind(('127.0.0.1', 0))
            listener.listen()
            closed.bind(('127.0.0.1', 0))
            config = Path(folder) / 'local.json'
            config.write_text(json.dumps({'checks': [
                {'name': 'open', 'type': 'tcp', 'host': '127.0.0.1', 'port': listener.getsockname()[1]},
                {'name': 'closed', 'type': 'tcp', 'host': '127.0.0.1', 'port': closed.getsockname()[1]}
            ]}))
            output = Path(folder) / 'reports'
            completed = subprocess.run([sys.executable, '-m', 'netcheck', '--config', str(config), '--output', str(output)], capture_output=True, text=True, timeout=10)
            self.assertEqual(completed.returncode, 1, completed.stderr)
            report = json.loads(next(output.glob('*/results.json')).read_text())
            self.assertEqual([row['status'] for row in report['results']], ['PASS', 'FAIL'])
            self.assertIn('Reports:', completed.stdout)

    def test_cli_missing_ping_writes_error_report(self):
        import os
        with tempfile.TemporaryDirectory() as folder:
            config = Path(folder) / 'ping.json'
            config.write_text(json.dumps({'checks': [{'name': 'ping', 'type': 'ping', 'host': '127.0.0.1'}]}))
            output = Path(folder) / 'reports'
            completed = subprocess.run([sys.executable, '-m', 'netcheck', '--config', str(config), '--output', str(output)],
                                       env={**os.environ, 'PATH': ''}, capture_output=True, text=True, timeout=5)
            self.assertEqual(completed.returncode, 2)
            report = json.loads(next(output.glob('*/results.json')).read_text())
            self.assertEqual(report['results'][0]['reason'], 'missing_ping')
