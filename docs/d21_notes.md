🚀 D21 总结：RAG TriageGPT-V1.0 诞生，从“检索片段”到“带引用的专家级问答”
﻿
## 🎯 一、 今日战果（产出清单）
今天，我们把昨天切分好的 164 个文本块（Chunks），变成了一个真正能对话、会拒绝、能溯源的 AI 运维专家 `RAG TriageGPT-V1.0`。
﻿
1. **知识库大扩充**：将 `dirty_test.md` 扩充到了 150+ 条涵盖 DMB电子餐牌、华硕电脑、海康监控、Linux/网络等 5 大类真实排障场景，极大地丰富了知识厚度。
2. **生产级 Prompt 约束**：写出了带有“只基于上下文、带引用编号、不知道就说不知道”的“紧箍咒” Prompt。
3. **跑通 CLI 问答闭环**：编写 `d21_cli_rag.py`，实现本地 Chroma 检索 + DeepSeek 生成的完整闭环，并带有大模型 API 的超时和指数退避重试。
4. **20问极限测试**：成功复现了“机子死机了咋整”等模糊问题下的精准拒答，同时也敏锐地发现了长文本（如 80 页 PDF）抢占 Top-3 导致新知识无法召回的 Bad Case。
﻿
## 🧠 二、 知识图谱（核心认知升级）
1. **大模型的“无状态”与“上下文依赖”**：大模型自己是什么都不知道的，它就是个“阅读理解机”。我们的 `ask()` 函数就是把检索到的片段像喂饭一样塞给它，所以**参考资料的质量，直接决定了回答的上限**。
2. **防幻觉的底线**：在 RAG 中，宁可输出“无法确定”，也绝不能让大模型用预训练知识胡编乱造。今天在 Prompt 中设下的拒答机制，是大厂落地 AI 应用中非常重要的一环。
3. **引用溯源（Citation）**：今天在代码里把 `metadatas` 和文本块拼成 `〖材料N〗`，让大模型学会引用。这样业务人员看到答案，能直接追溯到 PDF 的哪一页、第几块，彻底解决了 AI 答错没人敢用的问题。
﻿
## 💣 三、 踩坑与排雷
1. **“假数据”导致向量污染的惊醒**：上午测试时，问“屏幕的 Fn 键失灵”，AI 却没答出我新写的【ASUS-017】。排查发现，原因是旧数据里有一堆无用的 `note_x.md` 测试文件霸占相似度榜单。**破案**：果断 `rm` 删除垃圾文件，重新跑 `ingest` 和 `chunking`，AI 立刻恢复聪明。
2. **终端调试的杂乱无章**：一开始代码里用 print 疯狂打印，后来意识到这是个项目。重写了 `ingest.py`，引入了大厂风的“处理总览、文件格式分布、质量评分分布”，让终端输出赏心悦目。
﻿
## 🔴 四、 重点交付：核心 Bad Case 记录
* **现象**：问“笔记本 Fn 键失灵了”，Top-3 全部被 80 页的华硕官方 PDF（页73、页80）霸占。而真正包含答案的 `it_ops_manual.md` 块没有被召回。
* **根因**：纯向量检索（Vector Search）中，PDF 长文档由于内容多，很容易在相似度计算时“容错率”过高，挤占了精悍的短块。
* **改进方向**：这正是 D26 优化要做的。计划引入 **Rerank（重排）模型**，先把 Top-10 捞出来，再让重排模型把最精确的短块提上来；同时引入 **BM25 混合检索**，加强关键词命中。

今天我们只用新建一个文件：d21_cli_rag.py。整个上午的 3 个小时，我们只干三件事：写 Prompt、写调大模型的逻辑、写终端交互循环。
任务 1（60 分钟）：写生产级 RAG Prompt
你现在要构建的是一个“运维知识库助手”，它的核心是只能回答知识库里有的内容，不能瞎编。
第一步：定义 System Prompt（系统指令）
你需要在代码里定义一段文本，这段文本会作为“最高指令”发给大模型。
请在你的草稿里写下这段话（一会儿复制进代码）：
text
你是一个严谨的运维知识库助手。请遵守以下规则：
1. 只根据下面提供的〖参考资料〗回答用户问题。
2. 不要使用参考资料之外的事实性信息，不要补充你自己知道但资料中没有的内容。
3. 如果参考资料中没有足够信息来回答问题，请直接输出：“根据当前知识库资料，我无法确定这个问题的答案。”
4. 每个关键结论必须标注引用的材料编号，格式如 〖材料1〗。
为什么要这么写？ 规则1和2是防止它用预训练知识瞎编；规则3是拒答机制（找不答案就说不知道，这比答错强）；规则4是为了后续能溯源，它能证明这个答案是来自于哪份文档。
第二步：思考上下文怎么拼接
你从 D20 的 Chroma 数据库里检索出来的结果，不能直接一股脑丢给大模型，必须带上“身份证”。格式必须是：
text
〖材料1〗来源：d19_docs/dirty_test.md | 页：1 | 块：2
（这里放检索到的文本内容）
﻿
〖材料2〗来源：d19_docs/note_1.md | 页：1 | 块：0
（这里放检索到的文本内容）
这样大模型回答时，才能准确说出 〖材料1〗。
任务 2（90 分钟）：实现 ask(query)，跑通 CLI 闭环
这里包含了几个核心代码块。不要直接复制，跟着我一步步在 d21_cli_rag.py 里敲。
步骤 2.1：准备好环境和依赖（5 分钟）
你现在在 WSL 的终端里，确保你的虚拟环境激活了（就是前面有 (venv) 字样）。我们需要安装一个官方库来调用大模型，在终端输入：
bash
pip install openai
安装完成后，你需要去 DeepSeek 官网申请一个 API Key（如果你之前没用过的话）。然后，在代码的开头加上你的 Key（或者像我后面代码里那样用环境变量，但为了最简单，直接写在代码里也行）。
步骤 2.2：封装调用 DeepSeek 的函数（30 分钟）
为什么要封装？ 因为网络会断、接口会超时，大厂工程师绝不会写裸的请求。我们要加上超时和重试（对应你 D5.2 学过的 requests 重试机制）。
在代码里写下这个函数：
python
import time
import random
from openai import OpenAI, APITimeoutError, RateLimitError
﻿
# 初始化 DeepSeek 客户端（它兼容 OpenAI 的接口标准）
client_llm = OpenAI(
    api_key="sk-你的真实Key写这里", # 记得换成你自己的
    base_url="https://api.deepseek.com"
)
﻿
def call_deepseek(messages):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            # 发起请求，一定要设置 timeout=30 秒
            response = client_llm.chat.completions.create(
                model="deepseek-chat",
                messages=messages,
                temperature=0.1, # 温度调低，代表让模型严谨一点，不要发散
                timeout=30
            )
            return response.choices[0].message.content
        except (APITimeoutError, RateLimitError) as e:
            # 如果是超时或限流，且还有重试次数，就等一会儿再试
            if attempt < max_retries - 1:
                wait = (2 ** attempt) + random.uniform(0, 0.5)
                print(f"请求超时，{wait:.1f} 秒后重试...")
                time.sleep(wait)
            else:
                raise # 3次都失败了，直接报错
步骤 2.3：实现核心 ask() 逻辑（30 分钟）
这个函数就是把 D20 的检索 + 刚才写的 Prompt + 刚才写的 LLM 调用 串起来。
python
def ask(query, top_k=3):
    # 1. 把问题转成向量（用你 D20 的 model）
    query_emb = model.encode([query]).tolist()
    
    # 2. 检索（用你 D20 的 collection）
    results = collection.query(
        query_embeddings=query_emb,
        n_results=top_k,
        include=["documents", "metadatas"]
    )
    chunks = results["documents"][0]
    metadatas = results["metadatas"][0]
    
    # 3. 拼接带元数据的上下文（对应今天任务1的第二步）
    context_blocks = []
    for i in range(len(chunks)):
        # 提取元数据
        source = metadatas[i].get("source", "未知文档")
        page = metadatas[i].get("page", 1)
        chunk_idx = metadatas[i].get("chunk_index", i)
        text = chunks[i]
        
        # 组装成 〖材料N〗格式
        block = f"〖材料{i+1}〗来源：{source} | 页：{page} | 块：{chunk_idx}\n{text}"
        context_blocks.append(block)
        
    context = "\n\n".join(context_blocks)
    
    # 4. 组装发送给大模型的 Prompt 格式
    system_prompt = "你是一个严谨的运维知识库助手...（把任务1写的规则复制到这里）"
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"〖参考资料〗\n{context}\n\n〖用户问题〗\n{query}"}
    ]
    
    # 5. 调用大模型
    answer = call_deepseek(messages)
    
    return answer, metadatas
步骤 2.4：写 CLI 交互循环（25 分钟）
这是你在终端里问答的界面。不能运行一次就结束，要能一直问。
python
def main():
    print("🤖 CLI RAG v1 启动（输入 q 退出）")
    while True:
        query = input("\n👤 你：")
        if query.lower() in ['q', 'quit', 'exit']:
            break
        if not query.strip():
            continue
            
        print("🤖 助手思考中...")
        try:
            answer, metadatas = ask(query)
            print(f"\n🤖 助手：{answer}")
            
            # 打印引用了哪些来源
            print("\n📎 引用来源清单：")
            for i, meta in enumerate(metadatas):
                print(f"  材料{i+1}: {meta['source']} (页{meta['page']})")
                
        except Exception as e:
            print(f"❌ 发生错误：{e}")
﻿
if __name__ == "__main__":
    main()
任务 3（30 分钟）：3个问题烟雾测试
代码写完了，你需要把它跑起来。
在终端输入：python d21_cli_rag.py
如果终端出现了 👤 你：，说明成功了！现在输入这三个测试问题，看看它是不是按你的要求在工作：
1. 输入：电子餐牌屏幕不亮，应该检查什么？
预期：它会输出检查电源或 HDMI，并且结尾带有 〖材料1〗 这样的引用标识，下面会列出引用的文件。
1. 
	* 
2. 输入：机子死机了咋整？
预期：由于你的知识库是几份文档，如果里面没有“死机”的确切内容，大模型应该触发你设定的“拒答”规则，输出：“根据当前知识库资料，我无法确定这个问题的答案。”如果它瞎编了，我们要把这句话截下来，作为“拒答失效”的 Bad Case。
1. 
	* 
2. 输入：授权失败咋办？
预期：这就回到了 D20 的 Bad Case，系统可能会检索到“账号锁定”，看看模型是顺着错误资料胡编，还是说“没有相关信息”。
1. 
	* 
完整文件：d21_cli_rag.py
上面解释完后，这就是你今天上午完成的最终文件。我逐行加上了详细注释，标明了这几天的知识是如何串联的。
python
# d21_cli_rag.py
# 对应 D21 学习任务：实现带引用和拒答的 CLI RAG 问答
﻿
import os
import time
import random
﻿
# [复习 D20] 设置 HuggingFace 镜像，防止下载模型超时
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
﻿
# [复习 D20] 导入相关的库
import chromadb
from sentence_transformers import SentenceTransformer
# [新增今天] 导入 OpenAI SDK 来调用 DeepSeek
from openai import OpenAI, APITimeoutError, RateLimitError
﻿
# ==========================================
# 1. 初始化组件
# ==========================================
print("正在加载本地向量数据库和模型...")
# [复习 D20] 加载向量模型和 Chroma 数据库
model = SentenceTransformer("BAAI/bge-small-zh-v1.5")
client_db = chromadb.PersistentClient(path="./chroma_db")
collection = client_db.get_collection(name="sop_knowledge_base")
﻿
# [新增今天] 初始化 LLM 客户端（切记把 API Key 换成你自己的）
client_llm = OpenAI(
    api_key="sk-你的DeepSeekAPI密钥", 
    base_url="https://api.deepseek.com"
)
﻿
# ==========================================
# 2. 定义生产级 Prompt（任务1产出）
# ==========================================
# 这里集中管理 System Prompt，相当于给大模型戴上“紧箍咒”
SYSTEM_PROMPT = """你是一个严谨的运维知识库助手。请遵守以下规则：
1. 只根据下面提供的〖参考资料〗回答用户问题。
2. 不要使用参考资料之外的事实性信息。
3. 如果参考资料中没有足够信息，请直接输出：“根据当前知识库资料，我无法确定这个问题的答案。”
4. 每个关键结论必须标注引用的材料编号，格式如 〖材料1〗。"""
﻿
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
﻿
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
﻿
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
﻿
if __name__ == "__main__":
    main()
现在，你可以先把它敲进 VS Code，跑通这三个测试问题。
🌤️ 下午（4h）：20 问测试 + Bad Case 分类 + 录音
任务 4（90 分钟）：跑 20 问，按“检索层 / 生成层”分类记录
从你 D19 的文档里构造 20 个问题，覆盖故障处理、SOP、账号、网络四类。每个问题记录三件事：是否命中期望来源（检索层）、回答是否忠实于上下文（生成层）、引用是否指向正确段落。
不要用“对/错”二分。大厂评测已经明确：answer-level 的整体打分是“vibe check”，真正能定位问题的是 claim-level 分解——把回答拆成原子断言，逐条检查是否有上下文支撑。你不需要今天就写代码实现 claim-level 评测，但记录 bad case 时要用这个思路：不要写“回答不好”，要写“回答中的第 2 个断言（‘重启即可解决’）在上下文中找不到依据”。﻿
d21_20q_record.md 的每条记录至少包含：
﻿
﻿
字段 示例 
问题 电子餐牌黑屏，第一步查什么？ 
期望来源 dirty_test.md 
实际 Top-3 来源 dirty_test.md, note_1.md, note_2.md 
回答摘要 检查 HDMI 线是否松动，并确认电源插紧。 
引用是否准确 ✅ 指向 dirty_test.md 块2 
问题归属 检索层 / 生成层 / 引用层 
根因 （如果没命中）chunk 边界把“第二步”切断了；或（如果命中但回答编造）Prompt 中引用约束不够强 
任务 5（60 分钟）：提炼 3 条“面试级”bad case
从 20 问里挑 3 条最有讲解价值的，按四段式写进 d21_bad_cases.md。其中至少 1 条必须归因到 Prompt/生成层，而不是全部甩给检索。示例方向：
Bad Case A（生成层 — 拒答未触发）：问题“年假有几天？”检索到了正确的 chunk，但模型在上下文只说了“满 1 年 5 天”的情况下，自行补了“满 3 年 10 天”（来自预训练知识）。根因：Prompt 的“不要使用参考资料之外的事实性信息”约束不够硬，或 temperature 偏高。改进：加一句“如果某个数字/条件在参考资料中没有明确写出，不要补充”。
Bad Case B（引用层 — 引用不指向具体块）：模型输出了 〖材料1〗，但 〖材料1〗 对应的 chunk 并不是回答的实际依据（模型引用了最相似的块，但答案来自第二个块）。根因：Prompt 只要求“标注材料编号”，但没有要求“引用必须逐字来自该材料的原文”。改进：要求“引用时附上该材料中的原句片段”。
Bad Case C（检索层 — 已在 D20 记录，今天复现）：“授权失败”召回了“账号锁定”。今天在 CLI 里实际跑一次，看模型是拒答还是硬答——如果拒答，说明 Prompt 的“资料不足就说无法确定”生效了，这是正面证据；如果硬答，就是生成层需要加固的 bad case。


