# 缺陷与故障报告

## NET-001：连续结尾点的非法主机名被配置校验接受

| 字段 | 内容 |
| --- | --- |
| 类型 / 来源 | 项目附带的已修复历史实现缺陷；初始开发阶段由自动化测试发现 |
| 状态 | Closed，已修复并通过回归 |
| 环境 | Linux，Python 3.12.14，本项目初始开发版本 |
| 严重程度 | Minor：配置校验遗漏，可导致无效目标进入网络检查 |
| 优先级 | P2：交付前修复 |
| 触发条件 | host 为 `x..`，具有连续的结尾点 |
| 发生频率 | 修复前稳定复现 |

前置条件：运行修复前 `valid_host()` 实现。

复现步骤：

1. 将 `host` 设为 `x..`。
2. 调用 `valid_host('x..')`，或运行 `python3 -m unittest discover -s tests -p test_config.py -v`。
3. 查看 `test_invalid_targets` 的 `host='x..'` 子用例。

预期：返回 False，拒绝该配置。实际：返回 True，断言 `AssertionError: True is not false`。

根因：`host.rstrip('.')` 删除了所有结尾点，把 `x..` 错误地规范化为 `x`。修复：使用 `host.removesuffix('.')` 只移除一个合法的 DNS 绝对名称结尾点，保留第二个点供空 label 校验拒绝。`app.example.test.` 仍然允许。

回归：`test_invalid_targets` 验证 `x..` 被拒绝；`test_valid_hosts_and_default_timeout` 验证正常带结尾点的名称仍被接受。最终24项测试通过。

证据：

- `docs/evidence/NET-001-before-fix.txt`：修复前真实失败输出。
- `docs/evidence/automated-tests.txt`：修复后完整测试输出。

个人验证：本人阅读了该历史缺陷报告及修复前失败证据，并在 Ubuntu / Python 3.12.3 环境执行了修复后的无效主机名复测与正常主机名回归验证，均通过。本人并非该缺陷的首次发现者。

## LAB-001：期望服务端口开放，但端口未监听

这是**模拟测试环境报告**：demo.py 有意创建一个只绑定、不监听的本机端口，用来练习记录故障。它不是本测试工具的缺陷，也不是某个真实业务系统的已发现缺陷。这里的 TCP 失败日志来自真实本机连接。

| 字段 | 内容 |
| --- | --- |
| 类型 / 来源 | 模拟服务环境问题；受控故障 |
| 状态 | Reproduced；未修改外部服务 |
| 严重程度 | 假设这是必需的应用端口，则服务连接受阻；练习中无业务影响 |
| 目标 | 127.0.0.1:45685（仅该次演示有效） |
| 用例 | local-closed |
| 运行ID | 20261112T181925-4b78f416 |

复现步骤：

1. 在项目根目录执行 `python3 demo.py`。
2. 查看终端和该次运行目录中的 `results.json`。
3. `local-open` 为 PASS，`local-closed` 为 FAIL。

假设需求下的预期：应用端口应该接受 TCP 连接。实际：`FAIL / connection_refused`，演示 suite 退出码1。JSON记录耗时 20.493 ms。

已确认原因：该演示端口只执行 bind()，没有执行 listen()。对于真实外部系统，仅根据 connection_refused 不能直接确定“服务未启动”，还应结合进程、监听地址和网络策略检查。

建议处理与复测：在真实环境中确认服务启动并监听正确地址/端口，再用相同业务配置执行。演示重新运行会分配新端口；旧动态端口不能用于稳定复测。本报告不声称已经修复一个实际业务服务。

证据：`sample-results/20261112T181925-4b78f416/results.json`、`results.csv`、`run.log`、`demo-config.json`。
