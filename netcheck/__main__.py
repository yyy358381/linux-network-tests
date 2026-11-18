import argparse
import json
import sys

from .config import load_config
from .runner import run_suite


def main(argv=None):
    parser = argparse.ArgumentParser(description='Linux ping and TCP automation tests')
    parser.add_argument('--config', required=True, help='JSON configuration file')
    parser.add_argument('--output', default='artifacts', help='parent directory for unique run folders')
    args = parser.parse_args(argv)
    try:
        checks = load_config(args.config)
    except (OSError, ValueError, UnicodeError) as exc:
        print(f'Configuration error: {exc}', file=sys.stderr)
        return 2
    try:
        report, output = run_suite(checks, args.output)
    except OSError as exc:
        print(f'Output or execution error: {exc}', file=sys.stderr)
        return 2
    for result in report['results']:
        endpoint = result['host'] + (f":{result['port']}" if result['port'] else '')
        print(f"{result['status']:5} {result['name']} {endpoint} {result['reason']} {result['duration_ms']}ms")
    print(json.dumps(report['summary']))
    print(f'Reports: {output.resolve()}')
    return report['summary']['exit_code']


if __name__ == '__main__':
    raise SystemExit(main())
