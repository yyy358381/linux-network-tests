# Project Validation Records

## Initial Development Validation (2026-11-12)

The following historical records were included with the project. They do not represent work independently performed by me. References to the initial environment refer to the environment used during initial development.

- Environment: Linux, Python 3.12.14.
- Test command: `python3 -m unittest discover -s tests -v`.
- Result: All 24 tests passed; exit code 0. Full output: `docs/evidence/automated-tests.txt`.
- Demo command: `python3 demo.py --output sample-results`.
- Demo result: PASS=1, FAIL=1, ERROR=0; exit code 1, as expected. Run ID: `20261112T181925-4b78f416`.

### Checks Executed During Initial Development

- A subprocess connected to a listening local TCP port, then closed the connection.
- A subprocess attempted to connect to a local port that was bound but not listening; the connection was refused.
- The CLI read a configuration, ran probes, saved log/JSON/CSV reports, and returned the expected failure exit code.
- A controlled replacement blocked the subprocess DNS resolution path for 5 seconds. With a 0.2-second timeout, the parent terminated and reaped the subprocess. The test allowed an elapsed-time upper bound of 1.5 seconds.
- In an environment without `ping`, the CLI returned exit code 2 and saved an ERROR result.
- The invalid-hostname defect was reproduced before the fix, and regression checks passed after the fix.

### Mock-Based Validation and Initial Limitations

- The initial environment had no `ping` executable. Real ICMP success and no-response paths were not executed there; command arguments, exit codes, timeouts, and classification branches were tested with mocks.
- DNS failures, unreachable routes, and some permission errors were produced with mocks. Host networking and firewall settings were not modified.
- IPv6 and hostname configuration validation were tested; real IPv6 network integration was not verified.
- Load testing and ping compatibility across Linux distributions were not verified.
- Local TCP results establish connection behavior, not application-level business functionality.

## Personal Ubuntu Validation (2026-11-17)

I performed the following activities with guidance:

- Used Ubuntu with Python 3.12.3.
- Ran the complete automated test suite; all 24 tests passed.
- Ran the local TCP demonstration; the listening port passed and the non-listening port failed, as expected.
- Reviewed `run.log`, `results.json`, and `results.csv`.
- Used `configs/local.json` to verify a successful real ping to `127.0.0.1`.
- Started and stopped a local HTTP server and verified that TCP results changed with its listening state.
- Changed the target port from 8000 to 8001 and verified that the configuration took effect.
- Set `timeout` to 0 and verified configuration rejection with exit code 2.
- Ran the invalid-timeout automated test; it passed.
- Reviewed the NET-001 historical report and pre-fix evidence, then ran post-fix checks and valid-hostname regression checks; both passed.

This personal validation added coverage of the real ICMP success path. Real ICMP no-response behavior, real IPv6 networking, and compatibility with other Linux distributions remain unverified.

See `docs/my_validation.txt` for the personal validation checklist. The bundled evidence and sample reports retain their original development dates and environment details.
