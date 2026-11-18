import errno
import socket
import subprocess
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
from netcheck._tcp_probe import probe
from netcheck.checks import run_check
from netcheck.config import Check


class CheckTests(unittest.TestCase):
    def setUp(self):
        self.ping = Check('ping', 'ping', '127.0.0.1', 0.2)
        self.tcp = Check('tcp', 'tcp', '127.0.0.1', 2, 8080)

    @patch('netcheck.checks.shutil.which', return_value='/usr/bin/ping')
    @patch('netcheck.checks.subprocess.run')
    def test_ping_pass_uses_arguments_and_timeout(self, run, which):
        run.return_value = subprocess.CompletedProcess([], 0, '1 received', '')
        result = run_check(self.ping)
        self.assertEqual((result.status, result.reason), ('PASS', 'reply_received'))
        args, kwargs = run.call_args
        self.assertIsInstance(args[0], list)
        self.assertEqual(args[0][-1], '127.0.0.1')
        self.assertEqual(kwargs['timeout'], 0.2)
        self.assertNotIn('shell', kwargs)

    @patch('netcheck.checks.shutil.which', return_value='/usr/bin/ping')
    @patch('netcheck.checks.subprocess.run')
    def test_ping_no_reply_and_tool_error(self, run, which):
        for code, expected in [(1, ('FAIL', 'no_reply')), (2, ('ERROR', 'ping_error'))]:
            with self.subTest(code=code):
                run.return_value = subprocess.CompletedProcess([], code, '', 'ping output')
                result = run_check(self.ping)
                self.assertEqual((result.status, result.reason), expected)

    @patch('netcheck.checks.shutil.which', return_value=None)
    @patch('netcheck.checks.subprocess.run')
    def test_missing_ping_is_environment_error(self, run, which):
        result = run_check(self.ping)
        self.assertEqual((result.status, result.reason), ('ERROR', 'missing_ping'))
        run.assert_not_called()

    @patch('netcheck.checks.shutil.which', return_value='/usr/bin/ping')
    @patch('netcheck.checks.subprocess.run', side_effect=subprocess.TimeoutExpired('probe', 0.2))
    def test_overall_deadline_for_ping_and_tcp(self, run, which):
        for check in (self.ping, self.tcp):
            with self.subTest(type=check.type):
                result = run_check(check)
                self.assertEqual((result.status, result.reason), ('FAIL', 'timeout'))

    @patch('netcheck.checks.subprocess.run', side_effect=PermissionError())
    def test_subprocess_permission_error(self, run):
        result = run_check(self.tcp)
        self.assertEqual((result.status, result.reason), ('ERROR', 'execution_error'))

    @patch('netcheck.checks.subprocess.run')
    def test_invalid_child_output_is_error(self, run):
        for stdout in ('not json', '[]', '{}', '{"status":"MAYBE","reason":"x","detail":"x"}'):
            with self.subTest(stdout=stdout):
                run.return_value = subprocess.CompletedProcess([], 0, stdout, '')
                result = run_check(self.tcp)
                self.assertEqual((result.status, result.reason), ('ERROR', 'probe_error'))
        run.return_value = subprocess.CompletedProcess([], 1, '', 'crash')
        self.assertEqual(run_check(self.tcp).status, 'ERROR')

    @patch('netcheck._tcp_probe.socket.create_connection')
    def test_tcp_failure_classification(self, connect):
        cases = [(ConnectionRefusedError(), 'connection_refused'),
                 (TimeoutError(), 'timeout'), (socket.gaierror(), 'dns_error'),
                 (OSError(errno.ENETUNREACH, 'unreachable'), 'unreachable'),
                 (OSError(errno.EIO, 'other'), 'network_error')]
        for error, reason in cases:
            with self.subTest(reason=reason):
                connect.side_effect = error
                self.assertEqual(probe('localhost', 80, 1)['reason'], reason)

    def test_real_tcp_open_and_closed_ports(self):
        with socket.socket() as listener, socket.socket() as closed:
            listener.bind(('127.0.0.1', 0))
            listener.listen()
            closed.bind(('127.0.0.1', 0))
            for sock, expected in ((listener, ('PASS', 'connected')), (closed, ('FAIL', 'connection_refused'))):
                result = run_check(Check('local', 'tcp', '127.0.0.1', 2, sock.getsockname()[1]))
                self.assertEqual((result.status, result.reason), expected)
                self.assertGreaterEqual(result.duration_ms, 0)

    @patch('netcheck.checks.shutil.which', return_value='/usr/bin/ping')
    @patch('netcheck.checks.subprocess.run')
    def test_ping_detail_is_bounded(self, run, which):
        run.return_value = subprocess.CompletedProcess([], 0, 'x' * 5000, '')
        self.assertEqual(len(run_check(self.ping).detail), 2000)

    def test_real_process_timeout_including_blocked_dns(self):
        original = str(Path(__file__).resolve().parents[1] / 'netcheck' / '_tcp_probe.py')
        with tempfile.TemporaryDirectory() as folder:
            wrapper = Path(folder) / 'blocked_dns.py'
            wrapper.write_text('import socket, time, runpy\n'
                               'def blocked(*a, **k):\n    time.sleep(5)\n'
                               'socket.getaddrinfo = blocked\n'
                               f'runpy.run_path({original!r}, run_name="__main__")\n')
            with patch('netcheck.checks.Path') as path:
                path.return_value.with_name.return_value.resolve.return_value = wrapper
                result = run_check(Check('blocked-dns', 'tcp', 'localhost', 0.2, 80))
            self.assertEqual((result.status, result.reason), ('FAIL', 'timeout'))
            self.assertLess(result.duration_ms, 1500)
