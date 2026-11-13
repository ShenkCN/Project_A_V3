import os
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

import chromadb
from sentence_transformers import SentenceTransformer

# 1. 加载模型和数据库
model = SentenceTransformer("BAAI/bge-small-zh-v1.5")
client = chromadb.PersistentClient(path="./chroma_db")
collection = client.get_collection(name="sop_knowledge_base")

# 2. 准备我们的“考题”和“标准答案（Expected Source）”
# 这些题目是根据你 D19 造的假数据生成的
queries = [
    {"question": "电子餐牌屏幕不亮，应该检查什么？", "expected_source": "d19_docs/dirty_test.md"},
    {"question": "设备不亮，怎么检查电源？", "expected_source": "d19_docs/note_1.md"},
    {"question": "网络不通，怎么测试？", "expected_source": "d19_docs/note_1.md"},
    # 你可以继续加题目，凑够 20 题。这里先用 3 题演示逻辑。
]

# 3. 计算 Hit@K 和 MRR 的函数
def evaluate(queries: list[dict], top_k=3):
    hit = 0
    reciprocal_ranks = []
    
    print("\n=== 开始测试检索效果 ===")
    for q in queries:
        # 把问题变成向量
        query_emb = model.encode([q["question"]]).tolist()
        
        # 去数据库检索
        results = collection.query(
            query_embeddings=query_emb,
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )
        
        # 提取来源列表
        sources = [m["source"] for m in results["metadatas"][0]]
        
        # 计算 Hit@k (Top-3 里有正确来源吗？)
        is_hit = q["expected_source"] in sources
        if is_hit:
            hit += 1
            
        # 计算 MRR (正确来源排在第几？)
        rr = 0.0
        for rank, src in enumerate(sources, start=1):
            if src == q["expected_source"]:
                rr = 1.0 / rank
                break
        reciprocal_ranks.append(rr)
        
        # 打印这题的详细结果
        status = "✅ 命中" if is_hit else "❌ 未命中"
        print(f"问题: {q['question']}")
        print(f"  {status} | 期望来源: {q['expected_source']}")
        print(f"  实际召回: {sources}")
        print(f"  MRR得分: {rr:.2f}\n")

    # 计算平均值
    hit_at_k = hit / len(queries)
    mrr = sum(reciprocal_ranks) / len(queries)
    print(f"================ 评估总结 ================")
    print(f"最终 Hit@{top_k}: {hit_at_k:.2%}")
    print(f"最终 MRR: {mrr:.3f}")

# 执行测试
evaluate(queries, top_k=3)