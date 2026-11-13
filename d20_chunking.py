import os
# 防止下载模型卡住（如果你上午没加，这里一定要加）
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

import json
import re
import chromadb
from sentence_transformers import SentenceTransformer

# ================= 1. 定义我们的递归切分算法 =================
def recursive_split(text: str, chunk_size: int = 500, overlap: int = 80) -> list[str]:
    """
    大厂标准的递归切分：优先按段落切，切不开再按句号，再切不开按逗号
    """
    seps = ["\n\n", "\n", "。", "！", "？", "，", " "]
    chunks = []
    start = 0
    
    while start < len(text):
        end = min(start + chunk_size, len(text))
        
        # 如果还没到文件末尾，尽量找一个自然边界切开
        if end < len(text):
            for sep in seps:
                # rfind 从右往左找，尽量把边界包进来
                pos = text.rfind(sep, start, end)
                if pos != -1 and pos > start:
                    end = pos + len(sep)
                    break
                    
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
            
        # 核心逻辑：滑动窗口。下一次从 (当前结束位置 - overlap) 开始
        # 如果 end 已经到末尾了，就没必要再切了，直接跳出循环
        start = end - overlap if end < len(text) else end
        
    return chunks

# ================= 2. 准备环境 =================
print("🚀 正在加载 Embedding 模型...")
model = SentenceTransformer("BAAI/bge-small-zh-v1.5")

# 创建本地的向量数据库文件夹
# 创建/连接本地的向量数据库
print("📦 正在连接/创建 Chroma 向量数据库...")
client = chromadb.PersistentClient(path="./chroma_db")

# 每次跑之前先清空，防止重复添加（增加容错：如果不存在就跳过）
try:
    client.delete_collection(name="sop_knowledge_base") 
except Exception:
    pass

# 重新创建集合
collection = client.create_collection(
    name="sop_knowledge_base", 
    metadata={"hnsw:space": "cosine"} # 声明我们用余弦相似度
)

# ================= 3. 读取 D19 数据，切分并组装 =================
print("✂️ 正在读取并切分 D19 数据...")
records = []
with open("d19_parsed.jsonl", "r", encoding="utf-8") as f:
    for line in f:
        data = json.loads(line)
        # 只处理质量为 ok 的文档
        if data.get("quality") == "ok":
            chunks = recursive_split(data["text"])
            for i, chunk in enumerate(chunks):
                records.append({
                    "text": chunk,
                    "source": data["source"],
                    "page": data.get("page", 1),
                    "title": data.get("title", ""),
                    "chunk_index": i,
                })

print(f"✅ 切分完成！共生成 {len(records)} 个文本块 (Chunks)")

# ================= 4. 转换为向量并写入 Chroma =================
texts = [r["text"] for r in records]
metadatas = [{"source": r["source"], "page": r["page"], "chunk_index": r["chunk_index"]} for r in records]
# 方案：把 page 加进 ID 里，这样每一页的 chunk 就不冲突了
ids = [f"{r['source']}_p{r['page']}_{r['chunk_index']}" for r in records]

print("🧠 正在将文本转换为 512 维向量（这可能需要几秒钟）...")
embeddings = model.encode(texts).tolist()

print("💾 正在写入向量数据库...")
collection.add(
    documents=texts,
    embeddings=embeddings,
    metadatas=metadatas,
    ids=ids
)

print(f"🎉 入库成功！当前数据库中总共有 {collection.count()} 条数据。")