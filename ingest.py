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
    print("🚀 开始解析...")
    all_data = parse_all("d19_docs")
    
    # --- 新增：写出 JSONL ---
    output_file = "d19_parsed.jsonl"
    with open(output_file, "w", encoding="utf-8") as f:
        for item in all_data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
            
    print(f"✅ 解析完成！成功生成 {len(all_data)} 条记录。")
    print(f"📁 结果已保存到: {output_file}")
    
    # 打印前 3 条看看效果
    for i, item in enumerate(all_data[:3]):
        print(f"\n--- 记录 {i+1} ---")
        print(f"来源: {item['source']}")
        print(f"格式: {item['format']} | 质量: {item['quality']}")
        print(f"内容摘要: {item['text'][:100]}...") # 只打印前100个字符