🚀 D20 总结：从“物理切分”到“向量检索”，赋予机器语义理解力（P3 阶段：RAG v1）
🎯 一、今日战果（产出清单）
今天我们把昨天解析好的纯文本，彻底变成了机器能看懂的“向量知识库”，并第一次用数据量化了检索效果：
策略验证与代码落地：放弃了粗暴的固定长度切分，手写了 recursive_split 递归切分算法（优先按段落，其次按句号，最后按逗号），设定 chunk_size=500，overlap=80。
向量库搭建：成功引入 bge-small-zh-v1.5 模型（并配置了国内镜像源防超时），将切分好的 90+ 个 chunks 转换为 512 维向量，落盘写入本地 Chroma 向量数据库。
检索与评测脚本：编写 d20_retrieval.py，输入测试问题，成功返回相似度最高的 Top-3 文档块。手写了评估函数，跑通了 Hit@3（前3命中率） 和 MRR（平均倒数排名） 的计算逻辑。
价值验证：亲眼见证了“屏幕不亮”精准召回“电子餐牌黑屏”（得分 0.75），明白了向量检索跨越字面意思、直达语义的本质。
🧠 二、知识图谱（核心认知升级）
递归切分（Recursive Split）的性价比：固定切分会把一句话从中间砍断，语义切分（比如用模型理解）又太贵。递归切分就像“顺着骨头缝切肉”，先按大段落切，超长了再按句号切，尽最大努力保住语义完整性。
为什么必须有 Overlap（重叠）？：如果不重叠，关键的上下文刚好断在两块的交界处，检索时两边都召回不到。设了 80 字的重叠，相当于给上下文留了“接口”。
指标意识：以前写脚本只要能跑就行，今天知道了必须要算 Hit@3（Top3里有没有正确答案）和 MRR（正确答案排得越靠前，得分越高）。以后面试官问“你的 RAG 效果怎么样”，我拿数据说话。
💣 三、踩坑与排雷（程序员的日常）
模型下载卡死：第一次运行 SentenceTransformer 时，因为没有科学上网，直接从 HuggingFace 拉取模型超时卡住。破案：在代码开头加了一句 os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"，用国内镜像秒下。
Chroma 的“记忆残留”：反复运行脚本测试时，发现数据库里的数据翻倍了。破案：每次入库前必须执行 client.delete_collection("sop_knowledge_base") 先清空再重建，保证幂等性。
🔴 四、重点交付：5 个检索 Bad Case 记录（四段式）
为了明天（D21）给大模型写 Prompt 做准备，今天必须拿 20 个问题“拷打”我的检索系统。以下是我记录的 5 个典型翻车案例：
Bad Case 1：Chunking 边界切断表格（参数问题）
现象：用户问“HDMI 检查的下一步是什么？”，期望召回 dirty_test.md 的第二步，但实际召回了些不相干的话。Top-3 没命中。
排查：去看了切分后的 chunk 文本，发现 dirty_test.md 里的电源和 HDMI 步骤字数刚好卡在 480 字左右，被 chunk_size=500 的硬边界切成了两半，导致 HDMI 那一段失去了“第二步”的上下文标题。
根因：Markdown 结构没有被完全尊重，按标点切分时把列表切断了。
改进方向：明天试试调整切分策略，或者在切分前，把 Markdown 的 ## 标题作为严格的分割线（结构感知切分）。
Bad Case 2：口语化描述与专业术语的鸿沟（Embedding 语义理解问题）
现象：问题问“机子死机了咋整”，期望召回 note_1.md 里的“设备卡滞无响应”，但实际 Top-3 召回的是“网络不通”和“电源插紧”。
排查：算了一下相似度，发现“死机”和“卡滞无响应”的余弦相似度只有 0.42，而“机子”和“设备”的相似度还行，但整体被“咋整”这种口语词拉低了。
根因：BGE 模型虽然懂中文，但对极度口语化、带方言色彩的词，还是不如专业术语敏感。
改进方向：这属于模型能力边界，后续（D26）可以引入 Query Rewrite（查询改写），先用大模型把用户的口语问题改写为“设备无响应怎么处理”，再去向量库检索。
Bad Case 3：长文档霸榜，信息单一（召回多样性问题）
现象：问“网络怎么排查”，Top-3 全部命中了 day10_linux_cheatsheet.md 中的不同段落。但其实 note_1.md 里也有网络排查的步骤。
排查：长文档切出来的块多，只要其中包含网络字眼，就很容易占据榜单。而短文档因为特征不够密集，被挤下去了。
根因：只用了纯向量检索，没有做多样性处理，导致上下文冗余，大模型看到的信息面太窄。
改进方向：后续必须引入 MMR（最大边际相关性） 算法，或者 元数据过滤（Metadata Filter），强制让 Top-3 来自不同的 source。
Bad Case 4：短块缺乏上下文，变成“废话块”（切分策略问题）
现象：问“怎么 ping 127.0.0.1”，召回了一个只有 10 个字的 chunk：“请 ping 127.0.0.1。”，但是没命中同段落的“检查本机网络协议”。
排查：长度小于 20 的短文本块，在向量化时特征稀疏，虽然字面匹配了，但根本没提供解答问题的完整上下文。
根因：D19 清洗时，一些孤立的短行被当成独立 chunk 入库了。
改进方向：需要加一个合并逻辑（Parent Document Retriever 思想），检索时把邻近的上下块一并带出来；或者在 D19/D20 阶段直接丢弃质量分极低的短块（quality="low"）。
Bad Case 5：同义词陷阱（Embedding 语义理解问题）
现象：问题问“授权失败咋办”，期望召回 “Token 过期处理”，结果召回的是“账号被锁定”。
排查：在向量空间里，“授权”和“账号”高度相关，但“授权失败”通常指鉴权 Token 问题，而“账号锁定”是另一条业务线。
根因：遇到特定领域的黑话/行话，纯向量检索容易混淆“相关”和“精确”。
改进方向：这正是混合检索（BM25 + 向量） 的用武之地。引入关键词精确匹配（BM25），就能把包含“Token”这个词的文档权重拉高。D26 开搞！


二、上午（3h）：Chunking 策略与 Embedding 选型
﻿
🧠 第一块：Chunking 策略（理论认知）
为什么不能把一整篇文档直接丢给 AI？
因为大模型有“上下文窗口限制”，而且你如果把 5000 字的排障手册全塞进去，Token 费用极高，并且大模型会被无关信息干扰，找不到重点。
为什么选择“递归切分”？
想象一下切排骨：
* 固定切分：不管有没有骨头，每 5 厘米砍一刀。结果可能把一块完整的肉切得稀碎。
* 语义切分：用高精度扫描仪看看肉和骨头在哪，顺着缝隙切。极其精准，但要花很多钱和时间去扫描。
* 递归切分：先顺着大骨缝砍一刀（段落 \n\n），如果这块肉还是太大，再顺着小骨缝砍（句子 。），如果还大，再切（词）。这是性价比最高、最智能的默认方案。
两个关键参数怎么定？
* chunk_size（块大小）：对于中文，通常设为 500 字左右。太小了（比如 50 字）会缺乏上下文，太长了（比如 2000 字）会包含太多噪音。
* overlap（重叠度）：设为 50-80 字。就像你读一段话，最后一句和下一段的第一句要有重合，这样语义才不会断掉。
💻 第二块：实操——Embedding 向量化（动手验证）
第一步：安装依赖
打开终端，确保你在 Project_A_V3 目录下，激活了虚拟环境 (venv)，运行：
bash
pip install sentence-transformers chromadb scikit-learn
(注意：sentence-transformers 这个包比较大，里面包含了 PyTorch，下载可能需要几分钟，请耐心等待。)
第二步：写代码测试向量化
在 VS Code 里，新建一个文件叫 d20_embedding_test.py，把下面这段代码复制进去：
python
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
﻿
print("正在加载 Embedding 模型 (BAAI/bge-small-zh-v1.5)...")
# 第一次运行会自动从 HuggingFace 下载模型，大概 100MB 左右
model = SentenceTransformer("BAAI/bge-small-zh-v1.5")
﻿
# 准备三句话：一句问句，两句候选文档
query = "屏幕不显示怎么办？"
docs = [
    "打印机卡纸时，请先断电，再打开后盖取出纸张。",
    "电子餐牌黑屏不亮，请检查 HDMI 线是否松动，或者电源是否插紧。",
    "员工申请年假，请直接登录 OA 系统提交审批。"
]
﻿
print("正在把文本转换成向量...")
# 把问句和文档全部转成 512 维的向量
query_vec = model.encode(query)
docs_vecs = model.encode(docs)
﻿
# 计算问句和每个文档的余弦相似度
# query_vec 需要转成二维数组才能算相似度
similarities = cosine_similarity([query_vec], docs_vecs)[0]
﻿
print("\n=== 检索结果 ===")
for i, doc in enumerate(docs):
    print(f"相似度得分: {similarities[i]:.4f} | 文档内容: {doc}")
第三步：运行并观察
在终端运行 python d20_embedding_test.py。
⚠️ 避坑提示：如果你在国内，可能会卡在“下载模型”这一步报错或超时。如果卡住超过 2 分钟，请在终端按 Ctrl+C 中断，然后在运行命令前加上镜像环境变量，像这样：
bash
HF_ENDPOINT=https://hf-mirror.com python d20_embedding_test.py
第四步：验收结果
你应该能看到类似这样的输出：
text
=== 检索结果 ===
相似度得分: 0.1823 | 文档内容: 打印机卡纸时，请先断电，再打开后盖取出纸张。
相似度得分: 0.7541 | 文档内容: 电子餐牌黑屏不亮，请检查 HDMI 线是否松动，或者电源是否插紧。
相似度得分: 0.1055 | 文档内容: 员工申请年假，请直接登录 OA 系统提交审批。
你能看到什么魔法？
* 你的问句里有“屏幕”，候选文档里有“电子餐牌”。
* 这俩词字面上完全不一样，传统的 grep 或 like 根本搜不到。
* 但是向量检索算出了 0.7541 的高分！因为模型在训练时，早就知道“屏幕”和“餐牌”在语义空间里靠得很近。
三、下午（4h）：Chunk 入库 Chroma + 检索验证
🌲 任务一：切块（Chunking）与入库（写入 Chroma）
为什么不能把整篇文档直接入库？
因为你 D19 解析出来的 dirty_test.md 有几百字，如果整篇喂给大模型，它不仅浪费 Token，而且重点会被稀释。我们要把它切成 500 字左右的“小知识块”。
在 VS Code 里新建 d20_chunking.py，把下面的代码全部复制进去：
python
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
print("📦 正在连接/创建 Chroma 向量数据库...")
client = chromadb.PersistentClient(path="./chroma_db")
# 每次跑之前先清空，防止重复添加
client.delete_collection(name="sop_knowledge_base") 
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
# 生成唯一ID，防止冲突
ids = [f"{r['source']}_chunk_{r['chunk_index']}" for r in records]

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
操作验证：
在终端运行 python d20_chunking.py。
运行完后，你看左侧资源管理器，是不是多了一个 chroma_db 文件夹？终端是不是打印出了 “当前数据库中总共有 XX 条数据”（大概是 90 多条，根据你 D19 的文本长度而定）。
🔍 任务二：检索验证与指标计算（Hit@3 / MRR）
数据进去了，现在我们要当“考官”了。我们要用几个测试问题，去看看刚才入库的数据能不能被准确搜出来。
在 VS Code 里新建 d20_retrieval.py，复制以下代码：
python
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
操作验证：
运行 python d20_retrieval.py。你会看到终端打印出类似这样的结果：
问题: 电子餐牌屏幕不亮，应该检查什么？
✅ 命中 | 期望来源: d19_docs/dirty_test.md
实际召回: ['d19_docs/dirty_test.md', 'd19_docs/note_1.md', 'd19_docs/note_2.md']
MRR得分: 1.00
这就是你亲手跑通的 Hit@3 和 MRR 计算！如果在面试时，面试官问你怎么评估检索效果，你就可以直接把这段代码的逻辑讲出来。
任务 5（约 60 分钟）：Git 提交 + 5 个 Bad Case 记录
操作步骤：
1. 新建 d20_bad_cases.md，记录 5 个检索效果不好的例子。每个 Bad Case 按四段式写：
现象：用户问什么，期望来源是什么，实际 Top-3 返回了什么。
排查：是切分把关键句切断了？还是 Embedding 模型没理解语义？还是元数据过滤没生效？
根因：具体是哪一步的问题。
改进方向：调整 chunk_size、换 overlap、加结构感知切分、还是后续加 Rerank。
1. 提交代码和交付物：
bash
git add d20_chunking.py d20_retrieval.py d20_bad_cases.md chroma_db/
git commit -m "D20: recursive chunking + bge-small-zh embedding + Chroma indexing + Hit@3/MRR evaluation"
验收标准：5 个 Bad Case 里至少有一个能归因到“Chunking 参数”，一个能归因到“Embedding 语义理解”，而不是全部写成“模型不行”。
