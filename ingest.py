import re
import json
from pathlib import Path
from pypdf import PdfReader
from docx import Document
from markdown_it import MarkdownIt

# ================= 1. 定义解析器 =================

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

if __name__ == "__main__":
    import time
    from collections import Counter
    
    print("="*50)
    print("🚀 启动 RAG 知识库 ETL 数据流水线...")
    start_time = time.time()
    
    # 1. 执行解析
    all_data = parse_all("d19_docs")
    
    # 2. 写出 JSONL
    output_file = "d19_parsed.jsonl"
    with open(output_file, "w", encoding="utf-8") as f:
        for item in all_data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
            
    # 3. 统计报表 (这才是大厂高级感)
    process_time = time.time() - start_time
    formats = Counter([item["format"] for item in all_data])
    qualities = Counter([item["quality"] for item in all_data])
    
    print("-" * 50)
    print(f"✅ 数据解析完毕！总耗时: {process_time:.2f} 秒")
    print(f"📊 数据处理总览:")
    print(f"   - 总提取文本块: {len(all_data)} 条")
    print(f"   - 文件格式分布: {dict(formats)}")
    print(f"   - 质量评分分布: {dict(qualities)}")
    
    if qualities.get("error", 0) > 0 or qualities.get("low", 0) > 0:
        print(f"⚠️ 警告: 发现 {qualities.get('error', 0) + qualities.get('low', 0)} 条低质量或异常数据 (详情见 d19_parsing_issues.md)")
    
    print("-" * 50)
    print(f"📁 结构化数据已保存至: {output_file}")
    print("="*50)