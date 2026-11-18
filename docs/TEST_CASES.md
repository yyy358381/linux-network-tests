# Test Plan and Test Cases

## Scope and Pass Criteria

Validate configuration parsing, ping invocation, TCP connections, timeouts, failure classification, report generation, and command-line exit codes. All automated tests for the tool should pass. A target check returning FAIL is an expected connectivity result in some scenarios; it does not mean an automated test failed.

Coverage includes normal behavior, controlled failures, boundaries, and environment errors. The suite uses `unittest` and `unittest.mock`, real local sockets for TCP checks, and a controlled blocked DNS path in a subprocess for timeout verification. No public internet access is required.

Real ping success was also verified manually in the personal Ubuntu environment. Initial development environment limitations are recorded in `docs/VALIDATION.md`.

## Test Cases

| ID | Scenario / preconditions | Steps or input | Expected result | Automated coverage / manual verification |
| --- | --- | --- | --- | --- |
| TC-01 | Local TCP port is listening. | Create a listening socket and check its port. | PASS / connected. | `test_real_tcp_open_and_closed_ports` |
| TC-02 | Local port is bound but not listening. | Check that port. | FAIL / connection_refused. | `test_real_tcp_open_and_closed_ports` |
| TC-03 | Linux has ping installed and permits ICMP. | Run the loopback-ping check in local.json. | PASS / reply_received. | Invocation and classification tested with mocks; real ping success also manually verified on personal Ubuntu. |
| TC-04 | Ping reports no reply. | Mock ping exit code 1. | FAIL / no_reply. | `test_ping_no_reply_and_tool_error` |
| TC-05 | Ping cannot execute normally. | Mock ping exit code 2. | ERROR / ping_error. | `test_ping_no_reply_and_tool_error` |
| TC-06 | Ping is unavailable. | Clear subprocess PATH and run a ping configuration. | ERROR / missing_ping; report saved; CLI exit code 2. | `test_cli_missing_ping_writes_error_report` |
| TC-07 | Ping or TCP exceeds its timeout. | Mock TimeoutExpired. | FAIL / timeout. | `test_overall_deadline_for_ping_and_tcp` |
| TC-08 | DNS resolution blocks. | Block subprocess DNS for 5 seconds; configure a 0.2-second timeout. | FAIL / timeout; elapsed time below the 1.5-second tolerance limit. | `test_real_process_timeout_including_blocked_dns` |
| TC-09 | TCP DNS resolution fails. | Mock socket.gaierror. | FAIL / dns_error. | `test_tcp_failure_classification` |
| TC-10 | Route is unreachable or another network error occurs. | Mock ENETUNREACH and EIO. | FAIL / unreachable or network_error. | `test_tcp_failure_classification` |
| TC-11 | Valid configuration with default timeout. | Use IPv4, IPv6, or hostnames; omit timeout. | Configuration accepted; timeout defaults to 2 seconds. | `test_valid_hosts_and_default_timeout` |
| TC-12 | Invalid target string. | Supply URLs, whitespace, options, invalid IP addresses, or `x..`. | Configuration rejected. | `test_invalid_targets` |
| TC-13 | Invalid timeout values and types. | Supply 0, negative numbers, bool, NaN, Infinity, or an excessive value. | Configuration rejected. | `test_invalid_timeouts` |
| TC-14 | Port boundaries and invalid values. | Supply 1 / 65535; then 0 / 65536 / bool / string. | Valid boundaries accepted; other values rejected. | `test_port_boundaries_and_invalid_ports` |
| TC-15 | Invalid configuration structure. | Missing or extra fields, duplicate names, empty list, or more than 100 checks. | Configuration rejected. | `test_invalid_structure_and_duplicate_names` |
| TC-16 | Malformed JSON. | Use a file containing only an opening brace. | Error on stderr; exit code 2; no report generated. | `test_bad_config_cli_returns_two_without_reports` |
| TC-17 | Report integrity. | Run a suite containing a failed target. | Correct JSON summary; CSV text preserved; start/end events in log. | `test_report_files_and_unique_run_folders` |
| TC-18 | Repeated runs. | Run twice using the same output root. | Different run folders; earlier results retained. | `test_report_files_and_unique_run_folders` |
| TC-19 | Exit code precedence. | PASS; PASS+FAIL; FAIL+ERROR. | Exit codes 0, 1, and 2, respectively. | `test_exit_code_precedence` |
| TC-20 | Full CLI execution. | Use a temporary configuration with real listening and non-listening local ports. | Two results saved; CLI exit code 1. | `test_cli_real_local_checks` |
| TC-21 | Output directory is not writable. | Mock PermissionError. | Error on stderr; CLI exit code 2. | `test_unwritable_output_returns_two` |
| TC-22 | Subprocess execution or output is invalid. | Mock startup permission failure or invalid JSON output. | ERROR; never incorrectly reported as PASS. | `test_subprocess_permission_error` / `test_invalid_child_output_is_error` |
| TC-23 | Bound captured command output. | Mock ping output exceeding 5000 characters. | detail contains at most 2000 characters. | `test_ping_detail_is_bounded` |
| TC-24 | Suspicious CSV text prefixes. | Supply details beginning with =, +, -, @, or related leading whitespace. | Values are prefixed for text handling in spreadsheet programs. | `test_csv_formula_prefixes` |

## Manual Verification: Service Start and Stop

1. In terminal A, run `python3 -m http.server 8000 --bind 127.0.0.1`.
2. In terminal B, run `python3 -m netcheck --config configs/local.json` from the project root.
3. Confirm that `local-web-port` is PASS.
4. Stop the service in terminal A, then rerun the same check configuration.
5. Confirm that `local-web-port` is FAIL, normally with reason `connection_refused`.
6. Compare `results.json` and `run.log` from the two runs. Evaluate ICMP status independently.

These service start/stop steps were performed in the personal Ubuntu environment with the expected results; see `docs/my_validation.txt`. Bundled historical TCP evidence comes from `demo.py` and automated local socket tests.
