"""Internal one-shot process; the parent enforces the overall DNS/connect deadline."""
import errno
import json
import socket
import sys


def probe(host, port, timeout):
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return {'status': 'PASS', 'reason': 'connected', 'detail': 'TCP connection established'}
    except socket.gaierror:
        return {'status': 'FAIL', 'reason': 'dns_error', 'detail': 'Hostname could not be resolved'}
    except TimeoutError:
        return {'status': 'FAIL', 'reason': 'timeout', 'detail': 'TCP connection timed out'}
    except ConnectionRefusedError:
        return {'status': 'FAIL', 'reason': 'connection_refused', 'detail': 'TCP connection refused'}
    except OSError as exc:
        reason = 'unreachable' if exc.errno in (errno.EHOSTUNREACH, errno.ENETUNREACH) else 'network_error'
        return {'status': 'FAIL', 'reason': reason, 'detail': f'TCP connection failed (errno={exc.errno})'}


if __name__ == '__main__':
    print(json.dumps(probe(sys.argv[1], int(sys.argv[2]), float(sys.argv[3]))))
