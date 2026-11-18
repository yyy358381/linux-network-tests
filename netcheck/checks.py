import json
import math
import shutil
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from .config import Check


@dataclass
class Result:
    name: str
    type: str
    host: str
    port: int | None
    timeout: float
    status: str
    reason: str
    detail: str
    started_at: str
    duration_ms: float

    def to_dict(self):
        return asdict(self)


def run_check(check: Check):
    started_at = datetime.now(timezone.utc).isoformat()
    started = time.monotonic()
    try:
        if check.type == 'ping':
            outcome = ping(check)
        else:
            outcome = tcp(check)
    except subprocess.TimeoutExpired:
        outcome = dict(status='FAIL', reason='timeout', detail='Overall check deadline exceeded')
    except OSError as exc:
        outcome = dict(status='ERROR', reason='execution_error', detail=f'Cannot execute probe: {type(exc).__name__}')
    return Result(check.name, check.type, check.host, check.port, check.timeout,
                  started_at=started_at, duration_ms=round((time.monotonic() - started) * 1000, 3), **outcome)


def ping(check):
    executable = shutil.which('ping')
    if executable is None:
        return dict(status='ERROR', reason='missing_ping', detail='ping executable not found on PATH')
    # Linux iputils syntax. No shell, one packet, numeric output. Parent owns the deadline.
    command = [executable, '-n', '-c', '1', '-W', str(math.ceil(check.timeout)), check.host]
    completed = subprocess.run(command, capture_output=True, text=True, errors='replace', timeout=check.timeout)
    detail = (completed.stdout + '\n' + completed.stderr).strip()[:2000]
    if completed.returncode == 0:
        return dict(status='PASS', reason='reply_received', detail=detail)
    if completed.returncode == 1:
        return dict(status='FAIL', reason='no_reply', detail=detail)
    return dict(status='ERROR', reason='ping_error', detail=detail or f'ping exited {completed.returncode}')


def tcp(check):
    script = str(Path(__file__).with_name('_tcp_probe.py').resolve())
    command = [sys.executable, '-I', script, check.host, str(check.port), str(check.timeout)]
    # The child isolates potentially blocking DNS and multi-address connection attempts.
    # run() kills/reaps the child on timeout; no background DNS thread remains.
    completed = subprocess.run(command, capture_output=True, text=True, timeout=check.timeout)
    if completed.returncode != 0:
        return dict(status='ERROR', reason='probe_error', detail=f'TCP probe exited {completed.returncode}')
    try:
        data = json.loads(completed.stdout)
        if not isinstance(data, dict) or set(data) != {'status', 'reason', 'detail'}:
            raise ValueError('invalid fields')
        if data['status'] not in ('PASS', 'FAIL') or not all(isinstance(v, str) for v in data.values()):
            raise ValueError('invalid values')
        return data
    except (ValueError, TypeError):
        return dict(status='ERROR', reason='probe_error', detail='TCP probe returned invalid JSON result')
