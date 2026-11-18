"""Local TCP demonstration; intentionally includes a failed target check."""
import argparse
import json
import socket

from netcheck.config import parse_config
from netcheck.runner import run_suite


def main():
    parser = argparse.ArgumentParser(description='Reproducible local demo: one open and one closed TCP port')
    parser.add_argument('--output', default='artifacts')
    args = parser.parse_args()
    with socket.socket() as listener, socket.socket() as closed:
        listener.bind(('127.0.0.1', 0))
        listener.listen()
        closed.bind(('127.0.0.1', 0))  # Reserve this port, but deliberately do not listen.
        data = {'checks': [
            {'name': 'local-open', 'type': 'tcp', 'host': '127.0.0.1', 'port': listener.getsockname()[1], 'timeout': 2},
            {'name': 'local-closed', 'type': 'tcp', 'host': '127.0.0.1', 'port': closed.getsockname()[1], 'timeout': 2}
        ]}
        report, output = run_suite(parse_config(data), args.output)
        (output / 'demo-config.json').write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
    for row in report['results']:
        print(f"{row['status']} {row['name']} port={row['port']} reason={row['reason']}")
    print('This demo intentionally includes a closed port; suite exit code 1 is expected.')
    print(f'Reports: {output.resolve()}')
    return report['summary']['exit_code']


if __name__ == '__main__':
    raise SystemExit(main())
