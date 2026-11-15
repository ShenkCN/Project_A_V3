# 文件路径：d22_api/rag_service.py
import os
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
import chromadb
from sentence_transformers import SentenceTransformer
from openai import OpenAI

# 1. 初始化模型和数据库（路径注意用 ../ 退到上一级）
print("正在加载本地模型和向量库...")
model = SentenceTransformer("BAAI/bge-small-zh-v1.5")
client_db = chromadb.PersistentClient(path="../chroma_db")
collection = client_db.get_collection(name="sop_knowledge_base")

# 2. 初始化 DeepSeek（把你 D21 的 API Key 粘贴到这里）
client_llm = OpenAI(
    api_key="sk-082c06b461c540d8a2cfff42fcfb2a71", 
    base_url="https://api.deepseek.com"
)

SYSTEM_PROMPT = """你是一个经验丰富的企业 IT 运维专家。请严格根据下面提供的〖参考资料〗回答用户问题。
请遵守以下规则：
1. 用户的提问可能包含情绪化词汇（如脏话）或错别字，请务必忽略这些干扰词，提取核心故障现象进行匹配。
2. 如果用户提问的具体型号（如 iPhone13）在参考资料中没有完全对应的条目，但参考资料中包含同品牌（如 iPhone）的通用排障逻辑，请基于该逻辑给出排查建议。
3. 不要使用参考资料之外的事实性信息（如凭空捏造排查步骤）。
4. 如果参考资料中完全没有相关的故障排查逻辑（比如问怎么修汽车），请直接输出：“根据当前知识库资料，我无法确定这个问题的答案。”
5. 每个关键结论必须标注引用的材料编号，格式如 〖材料1〗。"""

def rewrite_query(original_query):
    """使用大模型提取用户的核心故障关键词，过滤情绪词"""
    rewrite_prompt = f"""你是一个IT运维助手。请从用户的输入中提取出核心的故障现象和设备名称。
去掉所有的情绪词、脏话、抱怨和多余的废话。只输出最精简的搜索关键词，不要任何解释。
用户输入："{original_query}"
提取结果（例如：iPhone13 相机 打不开）："""

    try:
        response = client_llm.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": rewrite_prompt}],
            temperature=0.1,
            timeout=15
        )
        cleaned = response.choices[0].message.content.strip()
        print(f"🔄 查询改写：'{original_query}' -> '{cleaned}'")
        return cleaned
    except Exception as e:
        print(f"❌ 改写失败: {e}")
        return original_query # 失败了就用原句查

def ask(query, top_k=7):
    """核心问答函数"""
    # 1. 【新增】先改写查询词
    search_query = rewrite_query(query)
    
    # 2. 检索（用改写后的词去查向量库，而不是原句）
    query_emb = model.encode([search_query]).tolist()
    results = collection.query(
        query_embeddings=query_emb, 
        n_results=top_k, 
        include=["documents", "metadatas"]
    )
    
    chunks = results["documents"][0]
    metadatas = results["metadatas"][0]
    
    # 3. 拼上下文（下面保持不变）
    context_blocks = []
    for i in range(len(chunks)):
        block = f"〖材料{i+1}〗来源：{metadatas[i].get('source')} | 页：{metadatas[i].get('page')}\n{chunks[i]}"
        context_blocks.append(block)
    
    # 4. 组装 Prompt（注意：传给大模型回答时，依然可以用原句，也可以用改写后的）
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"〖参考资料〗\n{chr(10).join(context_blocks)}\n\n〖用户问题〗\n{query}"}
    ]
    
    # 5. 调大模型
    response = client_llm.chat.completions.create(
        model="deepseek-chat", messages=messages, temperature=0.1, timeout=30
    )
    answer = response.choices[0].message.content
    
    return answer, metadatas