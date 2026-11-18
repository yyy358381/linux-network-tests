# Defect and Incident Reports

## NET-001: Hostname Validation Accepts an Invalid Name with Consecutive Trailing Dots

| Field | Details |
| --- | --- |
| Type / source | Bundled, previously fixed implementation defect; found by automated testing during initial development. |
| Status | Closed; fixed and regression checks passed. |
| Environment | Linux, Python 3.12.14; initial development version. |
| Severity | Minor: a configuration validation gap allows an invalid target to reach network checks. |
| Priority | P2: fix before delivery. |
| Trigger | Set `host` to `x..`, which contains consecutive trailing dots. |
| Frequency | Consistently reproducible before the fix. |

### Preconditions

Use the pre-fix implementation of `valid_host()`.

### Steps to Reproduce

1. Set `host` to `x..`.
2. Call `valid_host('x..')`, or run `python3 -m unittest discover -s tests -p test_config.py -v`.
3. Inspect the `host='x..'` subtest in `test_invalid_targets`.

**Expected:** Return `False` and reject the configuration.

**Actual:** Return `True`, causing `AssertionError: True is not false`.

### Root Cause and Fix

`host.rstrip('.')` removed all trailing dots, incorrectly normalizing `x..` to `x`.

The fix uses `host.removesuffix('.')` to remove only one trailing dot allowed in an absolute DNS name. For `x..`, the remaining dot causes the subsequent empty-label validation to reject the input. A valid name such as `app.example.test.` remains accepted.

### Regression Verification

- `test_invalid_targets` verifies that `x..` is rejected.
- `test_valid_hosts_and_default_timeout` verifies that valid names with a trailing dot remain accepted.
- All 24 tests passed in the final development test run.

### Evidence

- `docs/evidence/NET-001-before-fix.txt`: historical pre-fix failure output.
- `docs/evidence/automated-tests.txt`: complete post-fix automated test output.

### My Verification

I reviewed this historical report and the pre-fix failure evidence, then ran post-fix invalid-hostname checks and valid-hostname regression checks on Ubuntu with Python 3.12.3. Both passed. I was not the original discoverer of this defect.

## LAB-001: Expected Service Port Is Not Listening

This is a **simulated environment incident report**. `demo.py` intentionally creates a local port that is bound but not listening, to practice documenting a failure. It is neither a defect in the testing tool nor a defect discovered in a production system. The TCP failure evidence comes from a real local connection attempt.

| Field | Details |
| --- | --- |
| Type / source | Simulated service environment issue; controlled failure. |
| Status | Reproduced; no external service was modified. |
| Severity | If this were a required application port, connections would be blocked. The exercise has no business impact. |
| Target | `127.0.0.1:45685`, valid only for the recorded demo run. |
| Check | `local-closed` |
| Run ID | `20261112T181925-4b78f416` |

### Steps to Reproduce

1. Run `python3 demo.py` from the project root.
2. Inspect the terminal output and the generated `results.json`.
3. Verify that `local-open` is PASS and `local-closed` is FAIL.

**Expected under the hypothetical service requirement:** The application port accepts TCP connections.

**Actual:** `FAIL / connection_refused`; suite exit code 1. The historical JSON report records a duration of 20.493 ms.

### Confirmed Cause

The demo calls `bind()` on the port but does not call `listen()`.

For an actual external system, `connection_refused` alone is insufficient to establish that the service is stopped. Process state, listening address, and network policies should also be checked.

### Suggested Action and Retest

In a real environment, confirm that the service is running and listening on the intended address and port, then rerun the same service configuration.

Each demo run assigns new ports; old dynamic ports are not stable retest targets. This report does not claim that an actual business service was repaired.

### Evidence

The following files are in `sample-results/20261112T181925-4b78f416/`:

- `results.json`
- `results.csv`
- `run.log`
- `demo-config.json`
