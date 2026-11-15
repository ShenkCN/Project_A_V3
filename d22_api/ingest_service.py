# 文件路径：d22_api/ingest_service.py
import os
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
from pathlib import Path
from pypdf import PdfReader
from docx import Document
from sentence_transformers import SentenceTransformer
import chromadb
import uuid

model = SentenceTransformer("BAAI/bge-small-zh-v1.5")
client = chromadb.PersistentClient(path="../chroma_db")
collection = client.get_collection("sop_knowledge_base")

def recursive_split(text: str, chunk_size: int = 500, overlap: int = 80) -> list[str]:
    seps = ["\n\n", "\n", "。", "！", "？", "，", " "]
    chunks, start = [], 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        if end < len(text):
            for sep in seps:
                pos = text.rfind(sep, start, end)
                if pos != -1 and pos > start:
                    end = pos + len(sep)
                    break
        chunk = text[start:end].strip()
        if chunk: chunks.append(chunk)
        start = end - overlap if end < len(text) else end
    return chunks

def extract_text(file_path: Path) -> str:
    """根据后缀提取文本"""
    suffix = file_path.suffix.lower()
    if suffix == ".md":
        return file_path.read_text(encoding="utf-8")
    elif suffix == ".pdf":
        reader = PdfReader(file_path)
        return "\n".join([page.extract_text() or "" for page in reader.pages])
    elif suffix == ".docx":
        doc = Document(file_path)
        return "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
    return ""

def parse_and_index(file_path: Path) -> int:
    """解析、切分、向量化并写入数据库"""
    text = extract_text(file_path)
    if not text: return 0
    
    chunks = recursive_split(text)
    if not chunks: return 0
    
    embeddings = model.encode(chunks).tolist()
    ids = [f"{file_path.name}_{uuid.uuid4().hex[:8]}_{i}" for i in range(len(chunks))]
    metadatas = [{"source": str(file_path.name), "page": 1, "chunk_index": i} for i in range(len(chunks))]
    
    collection.add(documents=chunks, embeddings=embeddings, metadatas=metadatas, ids=ids)
    return len(chunks)