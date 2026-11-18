# Linux 网络自动化测试项目

使用 Python 执行 ICMP ping 和 TCP 端口检查，设置超时与失败判定，保存日志、JSON 和 CSV 结果，并配套自动化测试、测试用例及缺陷报告。项目使用 Python 标准库，无第三方 Python 依赖，适合学习 Linux 网络测试和作为 QA 项目练习。

## 功能与项目规划

| 模块 | 第一版功能 | 代码 |
| --- | --- | --- |
| 配置 | JSON、主机/端口/超时校验、拒绝重复用例名 | `netcheck/config.py` |
| 连通性 | 调用 Linux `ping`，每次发送一个 ICMP 请求 | `netcheck/checks.py` |
| TCP 端口 | 建立并关闭 TCP 连接，支持 IP 或域名 | `netcheck/_tcp_probe.py` |
| 超时与判定 | 区分超时、拒绝连接、DNS 错误和工具错误 | `netcheck/checks.py` |
| 执行与报告 | 顺序执行，逐项日志，独立的运行目录，JSON/CSV 汇总 | `netcheck/runner.py` |
| 命令行 | 读取配置、打印结果、返回自动化可用的退出码 | `netcheck/__main__.py` |
| 验证 | 24 项自动化测试，真实本机 TCP 与受控故障 | `tests/` |
| QA 文档 | 用例、真实已修复缺陷、模拟服务异常报告 | `docs/` |

第一版先完成配置 → 执行 → 判定 → 保存证据的流程。后续按需要增加 HTTP 状态码检查、重试、并发执行和定时运行；目前不依赖数据库或任务调度框架。

## 环境

- 目标系统：Linux，Python 3.10+；个人验证环境：Ubuntu，Python 3.12.3。
- TCP 和测试套件只需要 Python。
- ICMP 检查需要系统提供兼容 iputils 参数的 `ping`。可用 `command -v ping` 检查；Debian/Ubuntu 的软件包通常为 `iputils-ping`。
- 运行时无需修改防火墙或使用 root。若环境限制 ICMP 权限，结果将记录为 `ERROR/ping_error`。

## 最快运行：无需外网、无需 ping

解压后进入目录：

```bash
cd linux-network-tests
python3 -m unittest discover -s tests -v
python3 demo.py
```

`demo.py` 自动创建两个动态的本机 TCP 端口：一个监听，一个只绑定而不监听。预期输出为一个 `PASS/connected` 和一个 `FAIL/connection_refused`，因此**演示的退出码 1 是预期结果**。它用于展示失败证据，不表示测试程序有缺陷。

报告默认保存到 `artifacts/<运行ID>/`：

| 文件 | 内容 |
| --- | --- |
| `run.log` | UTC 时间、用例名、目标、超时、状态、耗时 |
| `results.json` | 环境、汇总和每项检查的结构化结果 |
| `results.csv` | 便于筛选、比较和导入表格的结果 |
| `demo-config.json` | 仅演示生成，用于记录当次动态端口 |

每次生成独立目录，不覆盖历史结果。动态端口在演示结束后释放；再次演示请重新运行 `demo.py`，不要复用旧端口号。

## 运行 ping 和端口检查

终端 A 启动一个本机 HTTP 服务，仅监听回环地址：

```bash
python3 -m http.server 8000 --bind 127.0.0.1
```

终端 B 执行配置中的两项检查：

```bash
python3 -m netcheck --config configs/local.json --output artifacts
```

如果系统可正常 ping 回环地址且 HTTP 服务已启动，预期两项 `PASS`、退出码 0。停止终端 A 的 HTTP 服务后重新执行，端口检查通常变为 `FAIL/connection_refused`。ping 可能仍成功，因为 IP 连通与应用端口监听是不同条件。

个人验证已在 Ubuntu 上完成：本机回环地址 ping 成功；HTTP 服务启动时 TCP 端口检查通过，停止时返回 connection_refused；修改目标端口和无效超时配置的测试也符合预期。另已运行完整自动化测试套件，24 项通过。

docs/VALIDATION.md 保留了项目最初验证时的环境与限制；个人后续操作记录见 docs/my_validation.txt。

## 自定义配置

```json
{
  "checks": [
    {"name": "gateway-ping", "type": "ping", "host": "192.168.1.1", "timeout": 2},
    {"name": "app-port", "type": "tcp", "host": "localhost", "port": 8000, "timeout": 3}
  ]
}
```

上述网关地址仅是配置格式示例，按你的测试环境替换。

- `name`：唯一用例名，1–80 字符，字母或数字开头，允许字母、数字、点、下划线和连字符。
- `type`：`ping` 或 `tcp`。
- `host`：IP 或域名，不包含 URL、端口、空白或命令参数。支持 IPv4、IPv6 和常规 ASCII 域名；不支持带 zone ID 的 IPv6 或 Unicode 域名。
- `timeout`：每项检查的总体秒数，默认 2，范围 0.05–60，必须为有限数字。
- `port`：仅 TCP 必填，整数 1–65535。
- 配置一次包含 1–100 项检查，顺序执行；第一版不自动重试，避免掩盖首次失败。

## 判定与退出码

| 状态 | 条件或原因 | 含义 |
| --- | --- | --- |
| PASS | `reply_received` | ping 返回成功 |
| PASS | `connected` | TCP 三次握手成功 |
| FAIL | `no_reply` | ping 返回 1，未收到成功响应 |
| FAIL | `timeout` | 超出检查时限 |
| FAIL | `connection_refused` | TCP 连接被明确拒绝 |
| FAIL | `dns_error` | TCP 的域名解析失败 |
| FAIL | `unreachable` / `network_error` | TCP 网络错误 |
| ERROR | `missing_ping` / `ping_error` | 命令缺失、参数/权限或其他 ping 执行错误 |
| ERROR | `execution_error` / `probe_error` | 无法启动子进程、子进程异常或返回格式异常 |

退出码：`0` 全部通过；`1` 存在 FAIL 且无 ERROR；`2` 存在 ERROR、配置无效或输出失败。ERROR 优先于 FAIL。有效配置的检查完成后保存报告；配置无效只在 stderr 提示并返回 2，不创建运行报告。输出目录不可写时无法保证报告生成。

## 超时与检查范围

TCP 连接放在独立 Python 子进程中，父进程设置总体超时，覆盖子进程启动、DNS 解析和多个地址连接的累计等待。超时后终止并回收子进程；不会因单独的 DNS 线程继续阻塞程序。ping 同样由父进程限时。实际耗时可能略超过配置值，因为进程创建、系统调度、终止和清理存在开销；这不是实时系统的严格时钟保证。

TCP PASS 仅表示连接成功，不验证 HTTP 响应、TLS、认证或业务功能。ping 失败不能单独证明设备宕机，也可能是 ICMP 被过滤。无回复、拒绝连接或超时可以提供故障线索，但不足以直接断定根因。第一版检查“期望主机可达 / 期望端口开放”，未实现“期望端口关闭”的策略。

## 测试与缺陷材料

- `docs/TEST_CASES.md`：测试计划、前置条件、步骤、预期和覆盖映射。
- `docs/DEFECT_REPORTS.md`：真实已修复的 NET-001，以及明确标注的模拟环境报告 LAB-001。
- `docs/DEFECT_TEMPLATE.md`：以后记录缺陷可直接填写的模板。
- `docs/VALIDATION.md`：本次已验证内容、环境限制和结果说明。
- `docs/evidence/`：修复前的失败输出、最终自动化测试输出。
- `sample-results/`：真实执行本机 TCP 演示所生成的日志、JSON 和 CSV。


## 个人贡献与项目来源

本项目在 AI 辅助下搭建，代码和自动化测试套件由 AI 提供并指导使用。本人完成了 Ubuntu 环境配置、SSH 操作、测试执行、配置修改、日志和报告分析，以及验证记录整理。

在 Ubuntu 上运行了 24 项自动化测试，并手工验证了服务启动与停止、目标端口修改、无效超时配置等场景。

NET-001 是项目附带的已修复历史缺陷，本人阅读了历史证据并执行修复后复测与正常输入回归验证。LAB-001 是模拟环境异常练习。

英文项目描述：

> Validated a Python network testing tool on Ubuntu, executed 24 automated tests, and reviewed logs and JSON/CSV reports. Verified configuration handling and service availability, and performed regression checks for a documented historical defect.