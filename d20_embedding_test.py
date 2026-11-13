from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

print("正在加载 Embedding 模型 (BAAI/bge-small-zh-v1.5)...")
# 第一次运行会自动从 HuggingFace 下载模型，大概 100MB 左右
model = SentenceTransformer("BAAI/bge-small-zh-v1.5")

# 准备三句话：一句问句，两句候选文档
query = "屏幕不显示怎么办？"
docs = [
    "打印机卡纸时，请先断电，再打开后盖取出纸张。",
    "电子餐牌黑屏不亮，请检查 HDMI 线是否松动，或者电源是否插紧。",
    "员工申请年假，请直接登录 OA 系统提交审批。"
]

print("正在把文本转换成向量...")
# 把问句和文档全部转成 512 维的向量
query_vec = model.encode(query)
docs_vecs = model.encode(docs)

# 计算问句和每个文档的余弦相似度
# query_vec 需要转成二维数组才能算相似度
similarities = cosine_similarity([query_vec], docs_vecs)[0]

print("\n=== 检索结果 ===")
for i, doc in enumerate(docs):
    print(f"相似度得分: {similarities[i]:.4f} | 文档内容: {doc}")