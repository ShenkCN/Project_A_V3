# D19 文档解析与清洗异常记录 (Parsing Issues Log)
## 🎯 背景说明
在构建 RAG 知识库时，文档解析是第一道防线。真实的业务文档往往存在各种格式问题、编码问题和脏数据。本文档记录在 D19 阶段，针对 PDF、Word、Markdown 进行自动化解析时遇到的异常现象、根因排查以及降级处理策略。核心原则：**任何一个坏文件都不能拖垮整个解析流水线。**
---
## 🚨 异常 1：伪造/损坏的 PDF 文件导致解析崩溃
- **现象**：程序运行到 `fake_pdf.pdf` 时，终端打印 `❌ 解析崩溃跳过: fake_pdf.pdf | 原因: EOF marker not found`。如果不加拦截，整个解析进程会直接抛出 `PdfReadError` 并终止。
- **排查**：使用 `file fake_pdf.pdf` 命令检查，或者用文本编辑器打开，发现文件内容实际是纯文本，根本不是真正的 PDF 二进制文件。
- **根因**：PDF 文件必须包含 `%PDF` 文件头和 `%%EOF` 结尾标记。`pypdf` 库在读取时会严格校验文件结构，找不到标记直接报错。
- **修复/降级**：在 `parse_all` 遍历文件的循环中，加入 `try-except` 兜底。捕获异常后，为该文件生成一条 `quality="error"` 的记录，附带 `error_msg`，然后 `continue` 继续解析下一个文件。
---
## 🚨 异常 2：损坏的 Word 文件导致解压失败
- **现象**：程序运行到 `broken_word.docx` 时，终端打印 `❌ 解析崩溃跳过: broken_word.docx | 原因: PackageNotFoundError`。
- **排查**：`.docx` 本质是一个 ZIP 压缩包（里面包含 XML）。`python-docx` 底层会去解压它。
- **根因**：由于文件被恶意篡改或下载中断，ZIP 文件头损坏，导致解压失败抛出 `PackageNotFoundError`。
- **修复/降级**：同异常 1，通过 `try-except` 拦截，将此文件标记为 `quality="error"` 并跳过，保证其他正常的 Word 文档能被继续解析。
---
## 🚨 异常 3：编码不匹配导致乱码或读取崩溃
- **现象**：程序运行到 `gbk_test.md` 时，终端打印 `❌ 解析崩溃跳过: gbk_test.md | 原因: 'utf-8' codec can't decode byte...`。
- **排查**：代码中使用了 `open(file_path, encoding="utf-8")`。由于该文件是 Windows 下默认保存的 GBK 编码，包含中文字符，强行用 UTF-8 读取直接报错。
- **根因**：不同操作系统或编辑器保存的文件编码不一致。
- **修复/降级**：
  - **当前策略**：捕获 `UnicodeDecodeError`，将该文件记录为 `quality="error"`，跳过解析。
  - **未来优化**：引入 `chardet` 库动态探测文件编码后再读取；或者在读取时加上 `errors="ignore"`（不推荐，容易丢失关键信息，目前选择宁可报错也不产生半截乱码）。
---
## 🚨 异常 4：Markdown 页眉/水印等脏数据混入正文
- **现象**：测试文件 `dirty_test.md` 中包含 `【内部资料，严禁外传】第 1 页 共 3 页` 和 `Copyright © 2026 汉堡王 IT 部` 等页眉页脚。解析成纯文本后，这些无意义字符完美混入正文，且占据了大量字符空间。
- **排查**：Markdown 解析器（如 `markdown-it`）只负责剥离语法标记（如 `#`、`**`），不懂业务语义。
- **根因**：RAG 检索极其依赖文本纯净度。如果这些水印进入向量库，会导致：
  1. 浪费 Token 成本。
  2. 干扰向量相似度计算（用户问“怎么修屏幕”，召回结果里全是“严禁外传”，导致检索精度下降）。
- **修复/降级**：在 `clean_text(text)` 函数中引入正则替换和行级过滤：
  1. 通过 `if "内部资料，严禁外传" in line: continue` 过滤特指水印。
  2. 通过 `re.search(r'第\s*\d+\s*页\s*共\s*\d+\s*页', line)` 过滤通用页码。
---
## 💡 面试话术准备（基于本记录）
> “面试官您好，在开发 RAG 系统的数据解析模块时，我发现真实的企业文档非常‘脏’。比如 PDF 是扫描件或伪造的，Word 文件损坏无法解压，或者代码因编码不一致（GBK/UTF-8）直接报错。
> 
> 所以我做了一个**高可用解析流水线**。核心逻辑是：**每个文件的解析必须被 `try-except` 包裹**，失败的文件我会记录一个 `quality=error` 的状态并降级跳过，绝不让单个坏文件阻塞其他 20 个文件。
> 
> 同时，对于成功解析的文件，我会做一层**正则清洗**。因为像页眉、版权声明这种水印，如果不洗掉，一旦进入向量库，就会严重干扰检索的召回率和答案准确性。我的原则是：**宁可让问题暴露在质量分上，也不让脏数据进向量库。**”


📁 输入层 (Raw Documents)
 ├── 📄 PDF 文档 (SOP手册/排障报告)
 ├── 📝 Word 文档 (规范/流程)
 └── 📋 Markdown 文档 (技术笔记/速查表)
       │
       ▼
🔧 解析层 (Parsing Engines)
 ├── pypdf (提取 PDF 文本，按页切割)
 ├── python-docx (提取 Word 段落 + 表格)
 └── markdown-it (将 MD 转为纯文本 Token)
       │
       ▼
🧹 清洗层 (Text Cleaning)
 ├── 移除特定噪声 (如: "内部资料"、"Copyright")
 ├── 正则过滤页眉页脚 (如: "第 X 页 共 Y 页")
 ├── 合并连续空行 (压缩多余换行符)
 └── 保留 Markdown 标题边界 (为了后续按结构切分)
       │
       ▼
⭐ 质量评估 (Quality Check)
 ├── 长度 < 20 字符  --> 标记 [quality: low]
 ├── 乱码字符 > 10%  --> 标记 [quality: low]
 └── 解析抛出异常    --> 标记 [quality: error]
       │
       ▼
📦 输出层 (Structured Data)
 └── 生成 d19_parsed.jsonl (每行一条 JSON 记录)
      ├── text: "清洗后的干净文本"
      ├── source: "d19_docs/xxx.pdf"
      ├── page: 1
      ├── title: "xxx"
      ├── format: "pdf/md/docx"
└── quality: "ok/low/error"

一、大厂 AI 应用交付/开发岗在 D19 看什么
AI 应用开发岗的 JD 里，RAG 流程的第一环写得很明确：文档解析 → 切片 → 向量化 → 检索 → Prompt 注入。交付/实施岗更关注“落地最后一公里”：文档质量检测优先，不能用同一种方式处理所有企业文档。﻿﻿
面试官在 D19 对应的考核点很集中：
1. 你用过哪些解析库？ pypdf、python-docx、markdown-it-py 是基础，能说出选型理由（pypdf 纯 Python 无系统依赖、python-docx 能抽段落和表格、markdown-it-py 能剥离标记保留纯文本）会加分。
2. 你怎么处理页眉页脚、水印、空行、乱码？ 这些噪声如果进了向量库，会严重干扰检索质量。﻿
3. 你的文档解析失败了怎么办？ 是跳过、记录、还是降级？有没有质量评分机制？
4. 元数据保留了什么？ source、page、title 是最低要求，没有这些，后面引用溯源就是空的。
D19 不要求你做到生产级完美，但必须留下“我踩过解析的坑、我知道噪声怎么清理”的证据。
二、上午（3h）：RAG 总览 + 文档解析
任务 1（约 60 分钟）：RAG 总览与架构图
为什么要做：如果面试官让你“说说 RAG 的完整流程”，你不能只背“检索+生成”。完整的落地链路是：解析 → 切分 → 嵌入 → 入库 → 检索 → 重排 → 生成 → 引用。今天先把前半段（解析）打透，后半段在 D20—D21 展开。
这是你在面试时，可以在白板上画出来的图。你可以把下面的代码复制到一个支持 Mermaid 的笔记软件（比如 Typora、Notion 或语雀）里，它会自动渲染成图，然后截图保存为 docs/rag_d19_architecture.png。

graph TD
    subgraph 输入层
        A1[PDF 手册]
        A2[Word SOP]
        A3[Markdown 笔记]
    end
﻿
    subgraph 解析层 (Parsing)
        B1[pypdf 提取文本]
        B2[python-docx 提取段落/表格]
        B3[markdown-it-py 剥离标记]
    end
﻿
    subgraph 清洗层 (Cleaning)
        C1[去除页眉页脚 / 水印]
        C2[合并连续空行 / 去除乱码]
        C3[保留 Markdown 标题结构]
    end
﻿
    subgraph 输出层 (Structured Data)
        D1[JSONL 结构: text]
        D2[元数据: source, page, title, format]
        D3[质量评分: quality = ok / low / error]
    end
﻿
    A1 --> B1
    A2 --> B2
    A3 --> B3
    
    B1 --> C1
    B2 --> C1
    B3 --> C3
    
    C1 --> C2
    C2 --> D1
    C3 --> D1
    
    D1 --> D2
    D2 --> D3
📂 第二块：准备“案发现场”（20 份测试文档）
千万不要在这个环节花几个小时去到处找真实的 SOP 文件。我们先造一批“有代表性的脏数据”来练手。
打开你的 WSL 终端，回到 Project_A_V3 根目录，依次执行：
1. 创建目录：
bash
mkdir -p ~/Project_A_V3/d19_docs
cd ~/Project_A_V3/d19_docs
2. 快速生成 10 份 Markdown 笔记（直接用你之前的）：
把你的 day9_linux_cheatsheet.md 等笔记复制 10 份进来，改个名。或者直接敲下面这行命令，循环生成 10 份：
bash
for i in {1..10}; do echo -e "# 模拟SOP笔记 $i\n\n## 1. 检查电源\n请检查设备是否插电。\n\n## 2. 检查网络\n请 ping 127.0.0.1。" > note_$i.md; done
3. 生成一份带干扰项的测试用 Markdown（故意制造坑）：
bash
cat << 'EOF' > dirty_test.md
【内部资料，严禁外传】第 1 页 共 3 页
# 电子餐牌故障排查
﻿
## 第一步：检查电源
确保电源线插紧。
﻿
Copyright © 2026 汉堡王 IT 部。保留所有权利。
﻿
## 第二步：检查 HDMI
如果屏幕不亮，重新插拔 HDMI 线。
﻿
﻿
【内部资料，严禁外传】第 2 页 共 3 页
EOF
4. 准备 Word 和 PDF 文件（手动准备）：
* 随便写一个 Word 文档，里面放一段话加一个 2x2 的表格，命名为 test_sop.docx，拖进这个文件夹。
* 去网上随便找一个公开的 PDF 技术文档（比如某路由器的配置手册），下载下来改名为 test_manual.pdf，拖进这个文件夹。
💻 第三块：手写解析代码 ingest.py
现在，在你的项目根目录下（~/Project_A_V3），新建 ingest.py，把下面的代码完整复制进去。我加了详细注释，不要只看，要弄懂它在干嘛。
python
import re
import json
from pathlib import Path
from pypdf import PdfReader
from docx import Document
from markdown_it import MarkdownIt
﻿
# ================= 1. 定义解析器 =================
﻿
def parse_pdf(file_path: Path) -> list[dict]:
    """解析 PDF，按页返回"""
    records = []
    try:
        reader = PdfReader(file_path)
        for i, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            records.append({
                "text": text,
                "page": i + 1,
                "source": str(file_path),
                "format": "pdf"
            })
    except Exception as e:
        print(f"[报错] PDF解析失败 {file_path}: {e}")
    return records
﻿
def parse_docx(file_path: Path) -> list[dict]:
    """解析 Word，提取段落和表格"""
    records = []
    try:
        doc = Document(file_path)
        text_parts = []
        # 提取段落
        for p in doc.paragraphs:
            if p.text.strip():
                text_parts.append(p.text)
        # 提取表格（转换为文本）
        for table in doc.tables:
            for row in table.rows:
                row_text = " | ".join([cell.text.strip() for cell in row.cells])
                text_parts.append(row_text)
        
        records.append({
            "text": "\n".join(text_parts),
            "page": 1,
            "source": str(file_path),
            "format": "docx"
        })
    except Exception as e:
        print(f"[报错] Word解析失败 {file_path}: {e}")
    return records
﻿
def parse_md(file_path: Path) -> list[dict]:
    """解析 Markdown，保留纯文本"""
    records = []
    try:
        md = MarkdownIt()
        text = file_path.read_text(encoding="utf-8")
        tokens = md.parse(text)
        # 把 token 拼起来
        text_parts = [t.content for t in tokens if t.type in ("inline", "text", "fence")]
        records.append({
            "text": "\n".join(text_parts),
            "page": 1,
            "source": str(file_path),
            "format": "md"
        })
    except Exception as e:
        print(f"[报错] Markdown解析失败 {file_path}: {e}")
    return records
﻿
# ================= 2. 核心清洗逻辑 =================
﻿
def clean_text(text: str) -> str:
    """清洗脏数据"""
    if not text:
        return ""
    # 1. 替换不可见字符/乱码
    text = text.replace('\u3000', ' ') # 全角空格
    # 2. 去除连续的空行（把3个以上的换行符替换为2个）
    text = re.sub(r'\n{3,}', '\n\n', text)
    # 3. 去除首尾空白
    text = text.strip()
    return text
﻿
def check_quality(text: str) -> str:
    """简单的质量打分"""
    if len(text) < 20:
        return "low"
    return "ok"
﻿
# ================= 3. 调度器 =================
﻿
def parse_all(docs_dir: str) -> list[dict]:
    results = []
    docs_path = Path(docs_dir)
    
    for path in docs_path.rglob("*"):
        if path.suffix == ".pdf":
            file_records = parse_pdf(path)
        elif path.suffix == ".docx":
            file_records = parse_docx(path)
        elif path.suffix == ".md":
            file_records = parse_md(path)
        else:
            continue
            
        # 对解析出来的每条记录进行清洗和元数据增强
        for r in file_records:
            r["text"] = clean_text(r["text"])
            r["quality"] = check_quality(r["text"])
            r["title"] = path.stem # 文件名作为 title
            results.append(r)
            
    return results
﻿
if __name__ == "__main__":
    print("开始解析 d19_docs 目录下的文档...")
    all_data = parse_all("d19_docs")
    
    print(f"共解析出 {len(all_data)} 条记录。")
    
    # 打印前 3 条看看效果
    for i, item in enumerate(all_data[:3]):
        print(f"\n--- 记录 {i+1} ---")
        print(f"来源: {item['source']}")
        print(f"格式: {item['format']} | 质量: {item['quality']}")
        print(f"内容摘要: {item['text'][:100]}...") # 只打印前100个字符
🚀 第四块：运行并“抓虫”（约 30 分钟）
在终端里，确保你在 Project_A_V3 目录下，激活虚拟环境，然后运行：
安装解析依赖：
bash
pip install pypdf python-docx markdown-it-py
#pypdf 用于 PDF，python-docx 用于 Word，markdown-it-py 用于把 Markdown 剥离成纯文本。
python ingest.py
仔细看终端里的输出，这就是你发现“脏数据”的案发现场：
1. 看 PDF 的输出：extract_text() 提取出来的文字顺序有没有乱？有没有混入页眉、页脚、或者乱码的符号？
2. 看 Word 的输出：你的表格内容被成功提取出来了吗？（在我的代码里，表格是用 | 拼接的）。
3. 看 Markdown 的输出：看看前面我们造的那个 dirty_test.md。它的 # 和 ** 等符号被剥离了，但“【内部资料，严禁外传】第 1 页 共 3 页”这种垃圾信息是不是依然完美地混在了文本里？
﻿
三、下午（4h）：文档清洗 + 结构化输出

🧹 第一步：升级清洗逻辑，修复 Markdown 丢标题的问题（约 40 分钟）
上午的遗留问题：上午我们用了 markdown-it-py 去解析 Markdown，结果把 # 给剥掉了。但在 RAG 里，标题是天然的语义边界，明天（D20）切分时，我们需要靠标题来切。所以这里我们要改一下：直接把文件读成字符串，不要用 token 剥离，直接在原文本上做正则清洗。
打开你的 ingest.py，把 parse_md 和 clean_text 函数替换成下面这段：
python
# 1. 修改 parse_md：直接读文本，保留原始结构
def parse_md(file_path: Path) -> list[dict]:
    records = []
    try:
        # 直接读取原始文本，保留 # 等结构
        text = file_path.read_text(encoding="utf-8")
        records.append({
            "text": text,
            "page": 1,
            "source": str(file_path),
            "format": "md"
        })
    except Exception as e:
        print(f"[报错] Markdown解析失败 {file_path}: {e}")
    return records

# 2. 升级 clean_text：用正则干掉页眉页脚
def clean_text(text: str) -> str:
    if not text:
        return ""
        
    # 去掉全角空格
    text = text.replace('\u3000', ' ')
    
    lines = text.split('\n')
    clean_lines = []
    for line in lines:
        # 过滤我们上午伪造的垃圾数据
        if "内部资料，严禁外传" in line: continue
        if "Copyright" in line and "汉堡王" in line: continue
        
        # 过滤通用的页眉页脚格式（比如：第 1 页 共 3 页）
        if re.search(r'第\s*\d+\s*页\s*共\s*\d+\s*页', line): continue
        
        clean_lines.append(line)
    
    text = '\n'.join(clean_lines)
    
    # 合并连续空行（3个及以上的换行变2个）
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()
🎯 第二步：给文档“打分”，处理坏数据（约 30 分钟）
大厂面试题：“如果一份文档解析出来全是乱码，或者只有两个字，你会直接丢进向量库吗？”
绝对不会。 我们会给它打个低分（quality="low"），交给后续流程去判断怎么处理。
在 ingest.py 中加入打分函数，并稍微修改一下 parse_all：
python
# 打分函数
def check_quality(text: str) -> str:
    if not text or len(text.strip()) < 20:
        return "low"  # 太短了，可能是空页
    # 简单的乱码率检查（比如替换字符 \ufffd）
    bad_chars = text.count('\ufffd')
    if bad_chars / len(text) > 0.1:
        return "low"
    return "ok"

# 修改 parse_all，加入质量评分
def parse_all(docs_dir: str) -> list[dict]:
    results = []
    docs_path = Path(docs_dir)
    
    for path in docs_path.rglob("*"):
        file_records = []
        
        # 【核心】异常兜底：任何文件解析失败，不能拖垮整个流程！
        try:
            if path.suffix == ".pdf":
                file_records = parse_pdf(path)
            elif path.suffix == ".docx":
                file_records = parse_docx(path)
            elif path.suffix == ".md":
                file_records = parse_md(path)
            else:
                continue
        except Exception as e:
            print(f"❌ 解析崩溃跳过: {path.name} | 原因: {e}")
            # 记录错误，打个 error 标签
            file_records = [{
                "text": "", "source": str(path), "format": path.suffix[1:],
                "quality": "error", "error_msg": str(e)
            }]
            
        for r in file_records:
            r["text"] = clean_text(r["text"])
            # 如果没有 error 标签，才去算质量分
            if r.get("quality") != "error":
                r["quality"] = check_quality(r["text"])
            r["title"] = path.stem
            results.append(r)
            
    return results
💣 第三步：制造 3 个“事故”，测试你的兜底逻辑（约 30 分钟）
为了让你在 d19_parsing_issues.md 里有真实的素材写，我们现在在 d19_docs/ 目录下制造三个坏文件：
打开终端，运行以下命令：
bash
cd ~/Project_A_V3/d19_docs

# 1. 造一个空 PDF（或者把非 PDF 文件改成后缀）
echo "I am not a pdf" > fake_pdf.pdf

# 2. 造一个损坏的 Word
echo "fake docx" > broken_word.docx

# 3. 造一个 GBK 编码的 Markdown（你的代码用 utf-8 读肯定报错）
echo "这是中文GBK编码" | iconv -f utf-8 -t gbk > gbk_test.md
现在，回到根目录 ~/Project_A_V3，再次运行：
bash
python ingest.py
注意看终端输出！ 你会发现程序打印了 3 个 ❌（或者被捕捉的报错），但没有崩溃，依然把好文件解析完了！这就是“高可用”。
📦 第四步：结构化输出，写出 d19_parsed.jsonl（约 20 分钟）
现在我们要把内存里的 all_data 真正落到硬盘上，变成明天能直接喂给切分模型的数据集。
在 ingest.py 的 if __name__ == "__main__": 块的最后，加上写出 JSONL 的代码：
python
if __name__ == "__main__":
    print("🚀 开始解析...")
    all_data = parse_all("d19_docs")
    
    # --- 新增：写出 JSONL ---
    output_file = "d19_parsed.jsonl"
    with open(output_file, "w", encoding="utf-8") as f:
        for item in all_data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
            
    print(f"✅ 解析完成！成功生成 {len(all_data)} 条记录。")
    print(f"📁 结果已保存到: {output_file}")
运行 python ingest.py。然后你可以用 head -n 5 d19_parsed.jsonl 看一眼你的数据结构（每一行都是一条包含 text, source, quality 的 JSON）。
任务 5（约 60 分钟）：Git 提交 + 面试话术准备
操作步骤：
1. 提交代码和交付物：
bash
git add d19_docs/ ingest.py d19_parsed.jsonl d19_parsing_issues.md docs/rag_d19_architecture.png
git commit -m "D19: RAG overview + multi-format document parsing/cleaning (PDF/DOCX/MD) + parsing issues log"
