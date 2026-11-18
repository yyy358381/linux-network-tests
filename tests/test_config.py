import json
import tempfile
import unittest
from pathlib import Path
from netcheck.config import load_config, parse_config, valid_host


class ConfigTests(unittest.TestCase):
    def valid(self, **kwargs):
        return dict(dict(name='web', type='tcp', host='127.0.0.1', port=8000), **kwargs)

    def test_valid_hosts_and_default_timeout(self):
        for host in ('127.0.0.1', '::1', 'localhost', 'app.example.test', 'app.example.test.'):
            with self.subTest(host=host):
                check = parse_config({'checks': [self.valid(host=host)]})[0]
                self.assertEqual(check.host, host)
                self.assertEqual(check.timeout, 2.0)

    def test_invalid_targets(self):
        for host in ('-c5', 'localhost;id', 'a\nb', 'http://localhost', 'host:80',
                     '999.1.1.1', '', 'x..y', 'x..', 'fe80::1%eth0', 'a b', None):
            with self.subTest(host=host):
                self.assertFalse(valid_host(host))

    def test_invalid_timeouts(self):
        for timeout in (0, -1, True, '2', float('nan'), float('inf'), 61, 0.01, 10 ** 400):
            with self.subTest(timeout=timeout), self.assertRaises(ValueError):
                parse_config({'checks': [self.valid(timeout=timeout)]})

    def test_port_boundaries_and_invalid_ports(self):
        for port in (1, 65535):
            self.assertEqual(parse_config({'checks': [self.valid(port=port)]})[0].port, port)
        for port in (None, True, 0, 65536, '80', 2.5):
            with self.subTest(port=port), self.assertRaises(ValueError):
                parse_config({'checks': [self.valid(port=port)]})

    def test_invalid_structure_and_duplicate_names(self):
        item = self.valid()
        for data in ([], {}, {'checks': []}, {'checks': 'x'}, {'checks': [None]},
                     {'checks': [item, item]}, {'checks': [item], 'extra': 1},
                     {'checks': [dict(item, extra=1)]}, {'checks': [dict(item, name='bad\nname')]},
                     {'checks': [dict(item, type='udp')]}, {'checks': [dict(item, type='ping')]},
                     {'checks': [item] * 101}):
            with self.subTest(data=data), self.assertRaises(ValueError):
                parse_config(data)

    def test_valid_ping_has_no_port(self):
        check = parse_config({'checks': [{'name': 'ping-1', 'type': 'ping', 'host': 'localhost'}]})[0]
        self.assertIsNone(check.port)

    def test_load_file_and_malformed_json(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'config.json'
            path.write_text(json.dumps({'checks': [self.valid()]}))
            self.assertEqual(len(load_config(path)), 1)
            path.write_text('{')
            with self.assertRaises(ValueError):
                load_config(path)
