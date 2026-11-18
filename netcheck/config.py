import ipaddress
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Check:
    name: str
    type: str
    host: str
    timeout: float = 2.0
    port: int | None = None


def valid_host(host):
    if not isinstance(host, str) or not host or len(host) > 253:
        return False
    try:
        ipaddress.ip_address(host)
        return '%' not in host  # Scoped IPv6 is outside this small project's scope.
    except ValueError:
        # Numeric dotted addresses should be valid IPs, not accidental DNS lookups.
        if re.fullmatch(r'[0-9.]+', host):
            return False
        return all(re.fullmatch(r'[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?', label)
                   for label in host.removesuffix('.').split('.'))


def parse_config(data):
    if not isinstance(data, dict) or set(data) != {'checks'}:
        raise ValueError('configuration must contain only a checks array')
    items = data['checks']
    if not isinstance(items, list) or not 1 <= len(items) <= 100:
        raise ValueError('checks must contain between 1 and 100 entries')
    checks, names = [], set()
    for index, item in enumerate(items):
        prefix = f'checks[{index}]'
        if not isinstance(item, dict):
            raise ValueError(f'{prefix} must be an object')
        if not {'name', 'type', 'host'} <= set(item) or set(item) - {'name', 'type', 'host', 'port', 'timeout'}:
            raise ValueError(f'{prefix} has missing or unknown fields')
        name = item['name']
        if not isinstance(name, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,79}', name):
            raise ValueError(f'{prefix}.name must be 1–80 letters, digits, dots, underscores or hyphens; start with letter/digit')
        if name in names:
            raise ValueError(f'duplicate check name: {name}')
        names.add(name)
        kind = item['type']
        if kind not in ('ping', 'tcp'):
            raise ValueError(f'{prefix}.type must be ping or tcp')
        if not valid_host(item['host']):
            raise ValueError(f'{prefix}.host must be an IP address or hostname without a URL or options')
        timeout = item.get('timeout', 2.0)
        if type(timeout) not in (int, float) or not 0.05 <= timeout <= 60 or not math.isfinite(timeout):
            raise ValueError(f'{prefix}.timeout must be a finite number between 0.05 and 60 seconds')
        port = item.get('port')
        if kind == 'tcp' and (type(port) is not int or not 1 <= port <= 65535):
            raise ValueError(f'{prefix}.port must be an integer between 1 and 65535')
        if kind == 'ping' and 'port' in item:
            raise ValueError(f'{prefix}: ping does not accept port')
        checks.append(Check(name, kind, item['host'], float(timeout), port))
    return checks


def load_config(path):
    path = Path(path)
    if path.stat().st_size > 1024 * 1024:
        raise ValueError('configuration exceeds 1 MiB')
    return parse_config(json.loads(path.read_text(encoding='utf-8')))
