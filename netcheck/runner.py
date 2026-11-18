import csv
import json
import logging
import platform
import time
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from . import __version__
from .checks import Result, run_check


def exit_code(results):
    if any(result.status == 'ERROR' for result in results):
        return 2
    return 1 if any(result.status == 'FAIL' for result in results) else 0


def csv_cell(value):
    # Preserve text as text when CSV is opened in spreadsheet programs.
    if isinstance(value, str) and value.lstrip().startswith(('=', '+', '-', '@')):
        return "'" + value
    return value


def run_suite(checks, output_root='artifacts'):
    started_at = datetime.now(timezone.utc).isoformat()
    run_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S') + '-' + uuid.uuid4().hex[:8]
    output = Path(output_root) / run_id
    output.mkdir(parents=True, exist_ok=False)
    logger = logging.getLogger('netcheck.' + run_id)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    handler = logging.FileHandler(output / 'run.log', encoding='utf-8')
    handler.setFormatter(logging.Formatter('%(asctime)sZ level=%(levelname)s %(message)s'))
    handler.formatter.converter = time.gmtime
    logger.addHandler(handler)
    results = []
    try:
        logger.info('event=run_started run_id=%s checks=%d', run_id, len(checks))
        for check in checks:
            logger.info('event=check_started name=%s type=%s host=%s port=%s timeout=%s',
                        check.name, check.type, check.host, check.port, check.timeout)
            result = run_check(check)
            results.append(result)
            level = logging.INFO if result.status == 'PASS' else logging.WARNING
            logger.log(level, 'event=check_finished name=%s status=%s reason=%s duration_ms=%s',
                       result.name, result.status, result.reason, result.duration_ms)
        counts = Counter(result.status for result in results)
        code = exit_code(results)
        report = {
            'schema_version': 1, 'run_id': run_id, 'started_at': started_at,
            'finished_at': datetime.now(timezone.utc).isoformat(),
            'environment': {'system': platform.system(), 'release': platform.release(),
                            'python': platform.python_version(), 'tool_version': __version__},
            'summary': {'total': len(results), **{status: counts[status] for status in ('PASS', 'FAIL', 'ERROR')}, 'exit_code': code},
            'results': [result.to_dict() for result in results],
        }
        (output / 'results.json').write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
        with (output / 'results.csv').open('w', encoding='utf-8', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=list(Result.__dataclass_fields__))
            writer.writeheader()
            for result in results:
                writer.writerow({key: csv_cell(value) for key, value in result.to_dict().items()})
        logger.info('event=run_finished total=%s pass=%s fail=%s error=%s exit_code=%s',
                    len(results), counts['PASS'], counts['FAIL'], counts['ERROR'], code)
        return report, output
    finally:
        logger.removeHandler(handler)
        handler.close()
