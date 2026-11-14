# 🚀 Project A V3: 智能运维与 RAG TriageGPT-V1.0

## 📖 1. 项目简介
本项目是一个基于 Python 开发的自动化运维与 AI 知识库系统，由两部分核心组成：
1. **Python 工程化底座（D1-D17）**：一个高并发、跨平台的系统日志巡检工具，实现了多线程并发告警与 Linux 底层系统审计。
2. **RAG TriageGPT-V1.0（D19-D21）**：一套面向企业 IT 运维场景的 RAG 检索增强生成系统。它支持将 PDF/Word/Markdown 等复杂排障手册进行高可用解析，并通过本地向量库结合大模型（DeepSeek），输出**带精确引用**与**防幻觉拒答**的专家级排障建议。

## ✨ 2. 核心特性
### ⚙️ 基础运维底座
- **大厂级工程目录**：`src/config/tests` 结构，配置与源码解耦。
- **系统级审计**：跨平台调用 Linux 命令（如 `df -h`、`kill -9`），预警磁盘与清理僵尸进程。
- **高并发限流告警**：基于 `ThreadPoolExecutor` 实现多渠道路由告警。

### 🧠 RAG TriageGPT 智能问答
- **高可用数据流水线（ETL）**：支持多格式解析，内置异常兜底（坏文件不阻塞整个流水线）、正则清洗与元数据（来源、页码）保留。
- **递归切分与向量化**：实现 `recursive_split` 递归切分策略，基于 `bge-small-zh-v1.5` 模型将文本转化为 512 维向量，持久化至 Chroma 向量数据库。
- **生产级 Prompt 约束**：强约束 LLM “只基于上下文回答”，支持资料不足时**主动拒答**，且强制标注 `〖材料N〗`，杜绝幻觉。
- **LLM 调用防弹衣**：封装 DeepSeek API 调用，带有超时控制与指数退避重试机制（防网络抖动）。

## 🛠️ 3. 技术栈
- **语言**：Python 3.10
- **系统环境**：Linux (WSL2 / Ubuntu 22.04)
- **AI 框架**：ChromaDB (向量库), SentenceTransformers (Embedding), OpenAI SDK (调用 DeepSeek)
- **核心基础库**：`pypdf` / `python-docx` / `markdown-it-py` (解析), `concurrent.futures` (并发), `logging` (日志)
- **测试**：`pytest`, `unittest.mock`

## 📂 4. 目录结构
```text
Project_A_V3/
├── chroma_db/             # Chroma 向量数据库持久化目录
├── d19_docs/              # 企业 IT 运维知识库原始文档 (md, pdf, docx)
├── d19_parsed.jsonl       # D19 解析并清洗后的结构化 JSON 数据
├── d20_chunking.py        # D20 脚本: 递归切分 + 向量化入库
├── d20_retrieval.py       # D20 脚本: 检索测试与 Hit@3/MRR 评估
├── d21_cli_rag.py         # D21 交付: 带引用与拒答的 CLI RAG 助手
├── ingest.py              # ETL 核心脚本: 包含健壮性兜底与数据清洗
├── d14_task/ ~ d16_sql/   # 前序阶段的 Linux/FastAPI/SQL 练习代码
├── README.md              # 项目说明文档
└── requirements.txt       # 依赖清单

##🚀 5. Quick Start (快速启动)
安装依赖：pip install -r requirements.txt

构建知识库：python ingest.py -> python d20_chunking.py

启动问答：python d21_cli_rag.py

##📁 6.目录与文件解析（方便复习）
chroma_db/：（核心） 存放向量化后的知识库数据。明天写 FastAPI 时直接读取它。

d14_task/, d14_refactor/, d15_http/：D14-D15 练习文件夹，用于巩固 Linux 和早期 FastAPI 基础，面试时作为“工程基本功”提及即可。

d15_api/, d16_sql/：FastAPI 初体验与 SQL 练习。

d19_docs/：（核心语料库） 里面现在存放了 it_ops_manual.md（150条排障圣经）、test_manual.pdf（干扰项）、test_sop.docx。

d19_parsed.jsonl：解析后的结构化数据源。

d20_*.py：向量切分、检索测试代码。

d21_cli_rag.py：（核心） 今天的 CLI 问答主程序。

ingest.py：数据接入 ETL 脚本（带有质量评分与清洗）。

docker-compose.yml：早期练习的 MySQL 编排（可作为了解 Docker 的基础，暂不用改）。

.gitignore：忽略 venv/ 和 __pycache__/ 以及 logs/。