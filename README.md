# 🚀 Project A V3: 智能日志巡检与系统审计工具

## 📖 1. 项目简介
本项目是一个基于 Python 开发的高并发、跨平台的自动化运维工具（V3 重构版）。针对企业级 IT 运维场景，本工具不仅实现了应用日志的规则匹配与多线程并发告警，还深度集成了 Linux 底层系统命令（如 `df -h`, `kill -9`），实现了“系统资源监控 + 僵尸进程清理”的系统级巡检能力。本项目已在 WSL (Ubuntu) 环境下完成验证。

## ✨ 2. 核心特性
- **大厂级工程目录**：采用 `src/config/tests` 结构，实现配置、源码与测试的完全解耦。
- **系统级审计**：利用 `subprocess` 模块，跨平台调用 Linux 核心命令，实现磁盘使用率预警与卡死进程的自动击杀。
- **日志按天切割**：集成 `TimedRotatingFileHandler`，自动将运行日志按天切分并保留 7 天，防止磁盘撑爆。
- **高并发限流告警**：基于 `concurrent.futures.ThreadPoolExecutor` 实现多渠道（钉钉/飞书/企微）告警的并发分发。
- **TDD 测试驱动**：基于 `pytest` 与 `unittest.mock` 编写单元测试，彻底隔离网络请求与系统调用。

## 🛠️ 3. 技术栈
- **语言**: Python 3.10
- **系统环境**: Linux (WSL2 / Ubuntu 22.04)
- **核心库**: `subprocess`, `argparse`, `logging`, `concurrent.futures`
- **测试框架**: `pytest`, `pytest-cov`, `unittest.mock`

## 📂 4. 目录结构
```text
Project_A_V3/
├── config/
│   └── config.json      # 规则与告警渠道配置
├── logs/                # 运行日志存放目录（自动切割）
├── src/                 # 核心源码
│   ├── __init__.py
│   ├── logger.py        # 日志封装组件
│   ├── notifier.py      # 告警发送组件
│   ├── main.py          # 应用日志巡检入口
│   └── system_audit.py  # 系统底层审计入口
├── tests/               # 单元测试
│   ├── __init__.py
│   └── test_main.py
├── requirements.txt     # 依赖清单
└── README.md