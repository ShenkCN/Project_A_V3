# d21_cli_rag.py
# 对应 D21 学习任务：实现带引用和拒答的 CLI RAG 问答

import os
import time
import random

# [复习 D20] 设置 HuggingFace 镜像，防止下载模型超时
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

# [复习 D20] 导入相关的库
import chromadb
from sentence_transformers import SentenceTransformer
# [新增今天] 导入 OpenAI SDK 来调用 DeepSeek
from openai import OpenAI, APITimeoutError, RateLimitError

# ==========================================
# 1. 初始化组件
# ==========================================
print("正在加载本地向量数据库和模型...")
# [复习 D20] 加载向量模型和 Chroma 数据库
model = SentenceTransformer("BAAI/bge-small-zh-v1.5")
client_db = chromadb.PersistentClient(path="./chroma_db")
collection = client_db.get_collection(name="sop_knowledge_base")

# [新增今天] 初始化 LLM 客户端（切记把 API Key 换成你自己的）
client_llm = OpenAI(
    api_key="sk-082c06b461c540d8a2cfff42fcfb2a71", 
    base_url="https://api.deepseek.com"
)

# ==========================================
# 2. 定义生产级 Prompt（任务1产出）
# ==========================================
# 这里集中管理 System Prompt，相当于给大模型戴上“紧箍咒”
SYSTEM_PROMPT = """你是一个严谨的运维知识库助手。请遵守以下规则：
1. 只根据下面提供的〖参考资料〗回答用户问题。
2. 不要使用参考资料之外的事实性信息。
3. 如果参考资料中没有足够信息，请直接输出：“根据当前知识库资料，我无法确定这个问题的答案。”
4. 每个关键结论必须标注引用的材料编号，格式如 〖材料1〗。"""

# ==========================================
# 3. 封装 LLM 调用（任务2：超时与重试）
# ==========================================
def call_llm(messages):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            # 发送请求，temperature=0.1 让模型更保守，timeout=30 防止无限卡住
            response = client_llm.chat.completions.create(
                model="deepseek-chat",
                messages=messages,
                temperature=0.1,
                timeout=30
            )
            return response.choices[0].message.content
        except (APITimeoutError, RateLimitError) as e:
            # [复习 D5.2] 类似你封装的 HTTP Client 的重试逻辑
            if attempt < max_retries - 1:
                wait = (2 ** attempt) + random.uniform(0, 0.5)
                print(f"网络波动或限流，{wait:.1f}秒后第{attempt+1}次重试...")
                time.sleep(wait)
            else:
                raise Exception(f"大模型接口调用失败: {e}")

# ==========================================
# 4. 核心问答函数（任务2：串联检索+Prompt）
# ==========================================
def ask(query):
    # 1. 向量化检索（[复习 D20]）
    query_emb = model.encode([query]).tolist()
    results = collection.query(
        query_embeddings=query_emb,
        n_results=3, # 取 Top-3
        include=["documents", "metadatas"]
    )
    
    chunks = results["documents"][0]
    metadatas = results["metadatas"][0]
    
    # 2. 拼接上下文，给每段文字打上 〖材料N〗 标签
    context_blocks = []
    for i in range(len(chunks)):
        source = metadatas[i].get("source", "未知文档")
        page = metadatas[i].get("page", 1)
        chunk_idx = metadatas[i].get("chunk_index", i)
        # 格式必须对齐，这样大模型才能学会引用
        block = f"〖材料{i+1}〗来源：{source} | 页：{page} | 块：{chunk_idx}\n{chunks[i]}"
        context_blocks.append(block)
    
    # 将三段材料合并成一个大字符串
    context = "\n\n".join(context_blocks)
    
    # 3. 构造符合 OpenAI 协议的消息列表
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"〖参考资料〗\n{context}\n\n〖用户问题〗\n{query}"}
    ]
    
    # 4. 调用大模型
    answer = call_llm(messages)
    
    # 返回答案和检索到的元数据（元数据用于在终端展示引用）
    return answer, metadatas

# ==========================================
# 5. CLI 主循环（任务2：命令行交互）
# ==========================================
def main():
    print("\n" + "="*40)
    print("🤖 运维知识库 CLI RAG v1")
    print("输入问题开始对话，输入 q 退出")
    print("="*40 + "\n")
    
    while True:
        query = input("👤 你：").strip()
        if query.lower() in ['q', 'quit', 'exit']:
            print("👋 会话结束")
            break
        if not query:
            continue
            
        print("🤖 助手检索生成中...")
        try:
            answer, metadatas = ask(query)
            print(f"\n🤖 助手：{answer}\n")
            
            # 打印引用清单，证明是可溯源的
            print("📎 引用来源清单：")
            for i, meta in enumerate(metadatas):
                print(f"  〖材料{i+1}〗: {meta['source']} (页{meta['page']}, 块{meta['chunk_index']})")
            print("-" * 40)
            
        except Exception as e:
            print(f"\n❌ 发生错误：{e}\n")

if __name__ == "__main__":
    main()