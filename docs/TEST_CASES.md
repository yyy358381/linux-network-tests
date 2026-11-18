# 测试计划与用例

## 范围和通过标准

验证配置校验、ping 调用、TCP 连接、超时、失败分类、结果保存和命令行退出码。项目自身的自动化测试应全部通过；测试目标的 FAIL 是业务检查结果，不等同于自动化测试代码失败。

正常、故障、边界和环境异常分别覆盖。自动化测试使用 unittest 和 unittest.mock；可控的本机 socket 用于真实 TCP，阻塞 DNS 的子进程用于真实超时。无需公网。真实 ping 成功路径已在个人 Ubuntu 环境手工验证；初始开发环境的限制见 docs/VALIDATION.md。

## 用例

| ID | 场景 / 前置条件 | 步骤或输入 | 预期结果 | 自动化覆盖 |
| --- | --- | --- | --- | --- |
| TC-01 | 本机 TCP 已监听 | 创建监听 socket，检查其端口 | PASS / connected | `test_real_tcp_open_and_closed_ports` |
| TC-02 | 本机端口只绑定不监听 | 检查对应端口 | FAIL / connection_refused | 同上 |
| TC-03 | Linux 已安装 ping 且允许 ICMP | 执行 local.json 的 loopback-ping | PASS / reply_received | 调用与判定用 mock；另已在个人 Ubuntu 环境完成真实 ping 成功验证 |
| TC-04 | ping 返回无响应 | 模拟 ping 退出码 1 | FAIL / no_reply | `test_ping_no_reply_and_tool_error` |
| TC-05 | ping 不能正常执行 | 模拟退出码 2 | ERROR / ping_error | 同上 |
| TC-06 | ping 不存在 | 清空子进程 PATH 后执行 ping 配置 | ERROR / missing_ping；生成报告；CLI 退出 2 | `test_cli_missing_ping_writes_error_report` |
| TC-07 | ping 或 TCP 超时 | 模拟 TimeoutExpired | FAIL / timeout | `test_overall_deadline_for_ping_and_tcp` |
| TC-08 | DNS 长时间阻塞 | 子进程 DNS 替身阻塞 5 秒，配置超时 0.2 秒 | FAIL / timeout；耗时小于宽容测试上限 1.5 秒 | `test_real_process_timeout_including_blocked_dns` |
| TC-09 | TCP DNS 解析失败 | 模拟 socket.gaierror | FAIL / dns_error | `test_tcp_failure_classification` |
| TC-10 | 路由不可达及其他错误 | 模拟 ENETUNREACH/EIO | FAIL / unreachable 或 network_error | 同上 |
| TC-11 | 配置正常及默认值 | IPv4 / IPv6 / 域名，省略 timeout | 接受配置；timeout=2 | `test_valid_hosts_and_default_timeout` |
| TC-12 | 非法主机字符串 | URL、空白、选项、无效 IP、x.. | 拒绝，配置错误 | `test_invalid_targets` |
| TC-13 | 超时边界与类型 | 0、负数、bool、NaN、Infinity、过大值 | 拒绝 | `test_invalid_timeouts` |
| TC-14 | 端口边界 | 1 / 65535；0 / 65536 / bool / 字符串 | 合法边界接受，其他拒绝 | `test_port_boundaries_and_invalid_ports` |
| TC-15 | 配置结构异常 | 缺字段、多余字段、重复名、空列表、超过100项 | 拒绝 | `test_invalid_structure_and_duplicate_names` |
| TC-16 | JSON 损坏 | 文件仅包含左大括号 | stderr 提示；退出2；不生成报告 | `test_bad_config_cli_returns_two_without_reports` |
| TC-17 | 报告完整性 | 执行包含失败目标的 suite | JSON 汇总正确；CSV 特殊字符完整；日志有开始/结束事件 | `test_report_files_and_unique_run_folders` |
| TC-18 | 多次执行 | 同一个输出根目录运行两次 | 生成不同目录，旧结果保留 | 同上 |
| TC-19 | 退出码优先级 | PASS；PASS+FAIL；FAIL+ERROR | 依次0、1、2 | `test_exit_code_precedence` |
| TC-20 | 完整 CLI | 临时配置中包含真实开放/关闭端口 | 保存两个结果；CLI退出1 | `test_cli_real_local_checks` |
| TC-21 | 输出目录不可写 | 模拟 PermissionError | stderr 提示；CLI退出2 | `test_unwritable_output_returns_two` |
| TC-22 | 子进程异常 | 模拟启动权限失败或无效 JSON | ERROR；不误判为通过 | `test_subprocess_permission_error` / `test_invalid_child_output_is_error` |
| TC-23 | 控制命令输出长度 | 模拟超过5000字符 ping 输出 | detail最多2000字符 | `test_ping_detail_is_bounded` |
| TC-24 | CSV 可疑文本前缀 | 详情以=、+、-、@等开头 | CSV 作为文本保存 | `test_csv_formula_prefixes` |

## 手工验证步骤：服务停止

1. 在终端 A 运行 `python3 -m http.server 8000 --bind 127.0.0.1`。
2. 在终端 B 执行 `python3 -m netcheck --config configs/local.json`。
3. 确认 `local-web-port` 为 PASS。
4. 停止终端 A 服务，再执行相同配置。
5. 确认 `local-web-port` 为 FAIL，原因通常为 connection_refused。
6. 比较两个运行目录中的 results.json 和 run.log；ICMP 状态独立判断。

这组服务启动与停止的手工步骤已在个人 Ubuntu 环境执行，结果符合预期，见 docs/my_validation.txt。项目附带的历史 TCP 示例证据来自 demo.py 和自动化本机 socket 测试。