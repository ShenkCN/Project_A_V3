
现在你的 Project_A_V3 就像一个精密的工厂，里面有几个文件夹是绝对核心，决定了 RAG TriageGPT 能不能正常运转。我把你需要“认清”的核心文件和目录整理成了四个层级，方便你以后自己去改：
🌟 第一梯队：数据层（知识库的源头）
这个目录决定了 AI 的“脑子”里装了什么。
* 📂 d19_docs/
it_ops_manual.md：（最核心） 这就是你手写的 150+ 条运维排障圣经。如果你想让 AI 变得更聪明，回答更多问题，就是在这里面继续加内容（比如继续加海康、三星电视的故障处理）。
test_manual.pdf / test_sop.docx：你早期用来测试解析功能的格式文件，放着就行。
* 📂 chroma_db/
这是向量数据库。里面存着把你的文档切碎后变成的“数字特征”。每次代码启动，都会来这里查资料。千万不要手动去改这个文件夹里的东西。
🌟 第二梯队：后端层（负责干脏活累活）
这是你今天上午写的 FastAPI，相当于后厨。
* 📂 d22_api/
main.py：（大门） FastAPI 的路由入口。定义了 /health、/upload、/ask 三个接口。如果以后你想加新的接口（比如 /delete 删除知识），就在这儿加。
rag_service.py：（大脑） 核心逻辑！这里面有 ask() 函数，它负责去数据库捞资料、拼装 Prompt，并调用 DeepSeek 生成回答。你想优化机器人的回答（比如改 Prompt、改温度），就改这个文件。
ingest_service.py：（传送带） 负责处理前端上传的新文件，切块并存入数据库。你想优化切分逻辑（比如 chunk_size 的大小），就改这个文件。
📂 d22_uploads/：网页上上传的文件都会存在这里。
🌟 第三梯队：前端层（给客户看的脸面）
这是你下午写的 Streamlit，相当于餐厅大堂。
* 📂 d22_streamlit/
app.py：网页的所有代码。你想改网页的标题、UI 布局、增加按钮，就改这个文件。
chat_history.json：代码自动生成的，存着你的网页聊天记录。不用管它。
🌟 第四梯队：基建层（早期的心血，用来证明基本功）
这些文件虽然现在 RAG 用不上，但它们是你面试大厂“Python工程化”和“运维底子”的硬核证据，绝对不能删。
* ingest.py 和 d20_chunking.py：早期用来“全量初始化知识库”的脚本。如果你以后把 it_ops_manual.md 大改了，想彻底重来一遍，就依次运行这两个脚本。
* d21_cli_rag.py：昨晚写的终端版 AI，现在留着当个备胎，万一网页崩了，终端还能用来演示。
* 📂 d14_task/ ~ d16_sql/：里面有你手敲的 Linux、Dockerfile、SQL。面试官如果问“你懂不懂 Linux/Docker”，你直接把这个文件夹打开给他看。
* requirements.txt：依赖清单。如果你今天安装了 streamlit，记得在终端运行 pip freeze > requirements.txt 更新一下它，否则明天 Docker 部署会报错。


☀️ 上午（3h）：FastAPI 服务化——把 ask() 变成生产级 API
任务 1（60 分钟）：定义 Pydantic 模型 + /health + /upload
为什么先做这个： 面试官看一个 RAG 项目，第一眼会看你的接口是否“像生产系统”。生产级 RAG API 至少要有健康检查、上传、普通问答、流式问答四个端点。今天上午先把前三个静态/半静态端点搭好，流式留到下一个任务。
步骤 1：新建 d22_api/ 目录，初始化 FastAPI 应用
python
# d22_api/main.py
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional
﻿
app = FastAPI(title="RAG TriageGPT API", version="1.0")
﻿
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 本地联调先放开，面试时讲“生产会收紧”
    allow_methods=["*"],
    allow_headers=["*"],
)
﻿
# ---------- Pydantic 模型：这是接口的“契约” ----------
class AskRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000, description="用户问题")
    top_k: int = Field(default=3, ge=1, le=10, description="检索返回的文本块数量")
﻿
class SourceItem(BaseModel):
    source: str
    page: int
    chunk_index: int
﻿
class AskResponse(BaseModel):
    answer: str
    sources: list[SourceItem]
关键点（面试会问）： AskRequest 里 query 的 min_length=1 不是装饰——FastAPI 会在进入你的 ask() 逻辑之前就拦截空问题，直接返回 422，避免把空字符串扔进向量检索。这就是“参数校验前置”，和 D15 学过的 422 逻辑完全一致。
步骤 2：/health 端点
python
@app.get("/health")
def health():
    return {"status": "ok", "service": "RAG TriageGPT-V1.0"}
面试话术：/health 是服务健康检查端点，生产环境会扩展为检查向量库连接、LLM API 可达性、磁盘空间等。今天先返回静态 ok，但你要知道它未来会变“重”。﻿
步骤 3：/upload 端点——上传后增量入库
D21 的 ingest.py 和 d20_chunking.py 是“全量重建”。今天 /upload 要做到“上传一个文件，只把这个文件解析、切分、嵌入、写入 Chroma”，不碰已有数据。
python
# d22_api/ingest_service.py（新建）
import os
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
from pathlib import Path
from pypdf import PdfReader
from docx import Document
from sentence_transformers import SentenceTransformer
import chromadb
import json, re, uuid
﻿
model = SentenceTransformer("BAAI/bge-small-zh-v1.5")
client = chromadb.PersistentClient(path="../chroma_db")
collection = client.get_collection("sop_knowledge_base")
﻿
def parse_and_index(file_path: Path):
    # 复用 D19/D20 的解析与清洗逻辑（略，直接 import 或复制函数）
    # 切分、嵌入、写入 collection
    # 返回写入的 chunk 数量
    ...
在 main.py 里：
python
@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    allowed = {".md", ".pdf", ".docx"}
    suffix = Path(file.filename).suffix.lower()
    if suffix not in allowed:
        raise HTTPException(status_code=400, detail=f"不支持的文件格式: {suffix}")
﻿
    save_path = Path("d22_uploads") / file.filename
    save_path.parent.mkdir(exist_ok=True)
    content = await file.read()
    save_path.write_bytes(content)
﻿
    from d22_api.ingest_service import parse_and_index
    chunk_count = parse_and_index(save_path)
    return {"filename": file.filename, "chunks_added": chunk_count}
面试考点： 为什么 upload 要限制后缀？因为如果直接放任意文件，pypdf 遇到非 PDF 会抛异常，python-docx 遇到损坏 ZIP 会抛 PackageNotFoundError。在 API 层做白名单，是把 D19 的“解析兜底”前移到“入口拦截”，两层防护。
任务 2（90 分钟）：实现 /ask（同步）和 /ask/stream（SSE 流式）
这是今天上午最核心的部分。 面试官几乎必问“你怎么实现流式输出，为什么不用 WebSocket”。﻿
步骤 1：把 D21 的 ask() 函数迁移过来
D21 的 d21_cli_rag.py 里已经有了完整的检索→拼上下文→调 DeepSeek→返回答案的逻辑。新建 d22_api/rag_service.py，把 ask(query) 原样搬过来，但去掉 print 和 CLI 循环，只保留纯函数。返回 (answer, metadatas)。
步骤 2：同步 /ask
python
@app.post("/ask", response_model=AskResponse)
def ask_endpoint(req: AskRequest):
    from d22_api.rag_service import ask
    answer, metadatas = ask(req.query, top_k=req.top_k)
    sources = [
        SourceItem(source=m["source"], page=m["page"], chunk_index=m["chunk_index"])
        for m in metadatas
    ]
    return AskResponse(answer=answer, sources=sources)
同步版本的好处：前端 fetch 直接拿完整 JSON，方便 Streamlit 先跑通。但它有一个致命问题——大模型生成 500 字可能要 10 秒，前端就白屏 10 秒。所以必须有流式。
步骤 3：SSE 流式 /ask/stream——生产级的写法
为什么用 SSE 而不是 WebSocket： 大模型生成是“服务端单向往客户端推文字”，不需要全双工。SSE 基于 HTTP，浏览器和网关支持好，实现成本低；WebSocket 适合语音/视频/客户端持续推帧的场景，对纯文本 RAG 是过度设计。﻿
生产级 SSE 的四个细节（面试会追问）：
1. 事件要有类型，不要只推裸文本：每个 chunk 带上 type（如 token、done、error），前端才能区分“文字增量”和“结束信号”。﻿
2. 防止代理缓冲：设置 Cache-Control: no-cache、X-Accel-Buffering: no，否则 Nginx 会攒一批才发，流式失效。﻿
3. 处理客户端断连：用 await request.is_disconnected() 检测，客户端关掉页面后及时停止 LLM 调用，省钱。﻿
4. 不要用 yield json.dumps(...) 直接当 SSE：SSE 的格式是 data: ...\n\n，必须按规范拼。
python
from fastapi import Request
from fastapi.responses import StreamingResponse
import json, asyncio
﻿
@app.post("/ask/stream")
async def ask_stream(req: AskRequest, request: Request):
    from d22_api.rag_service import stream_ask  # 下面写
﻿
    async def event_generator():
        try:
            async for event in stream_ask(req.query, req.top_k):
                if await request.is_disconnected():
                    break
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"
﻿
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
stream_ask 的实现思路（伪代码，你今天要自己写完整）：
python
async def stream_ask(query, top_k):
    # 1. 先检索（同步，可以放到线程池，但今天先接受阻塞）
    answer, metadatas = await asyncio.to_thread(ask, query, top_k)
    # 2. 先推 sources 事件
    yield {"type": "sources", "sources": [...]}
    # 3. 逐字/逐句推 token（DeepSeek 支持 stream=True）
    #    把 OpenAI SDK 的同步流改成异步生成器，或者用 to_thread 包装
    async for token in stream_deepseek(messages):
        yield {"type": "token", "content": token}
    yield {"type": "done"}
今天不要求做到完美异步（DeepSeek 的流式 SDK 是同步的，真正全异步需要 httpx 手动发请求）。你可以先做“先检索、再一次性返回完整答案、但用 SSE 格式推 sources + token 模拟”的版本，面试时说“当前版本是流式封装，下一步会把 LLM 调用也换成真正的 token 级流”。诚实比硬编加分。
任务 3（30 分钟）：启动服务，验证 Swagger
bash
cd d22_api
uvicorn main:app --reload --port 8002
打开 http://127.0.0.1:8002/docs，确认四个端点都在。用 Swagger 先测 /health 和 /ask，/ask/stream 用 curl -N 测：
bash
curl -N -X POST http://127.0.0.1:8002/ask/stream \
  -H "Content-Type: application/json" \
  -d '{"query": "电子餐牌屏幕不亮，应该检查什么？", "top_k": 3}'
截图保存 Swagger 页面和 curl 流式输出，这是今天的证据包。
🌤️ 下午（4h）：Streamlit 前端——让引用“看得见”
任务 4（120 分钟）：Streamlit 聊天界面 + 引用展示 + 上传
大厂前端对 RAG 的核心要求是“引用可溯源”：每个答案下面必须有可展开的“来源”，能点到具体文档和页码。你的 D21 CLI 已经打印了引用清单，今天把它搬到网页上。
步骤 1：安装并初始化
bash
pip install streamlit
新建 d22_streamlit/app.py：
python
import streamlit as st
import requests
﻿
API_BASE = "http://127.0.0.1:8002"
﻿
st.set_page_config(page_title="RAG TriageGPT", page_icon="🤖", layout="wide")
st.title("🤖 RAG TriageGPT-V1.0 · 智能运维知识库")
﻿
# 侧边栏：上传文档
with st.sidebar:
    st.header("知识库管理")
    uploaded = st.file_uploader("上传 SOP / 手册 / 笔记", type=["md", "pdf", "docx"])
    if uploaded and st.button("上传并入库"):
        files = {"file": (uploaded.name, uploaded.getvalue())}
        r = requests.post(f"{API_BASE}/upload", files=files)
        if r.status_code == 200:
            st.success(f"入库成功，新增 {r.json()['chunks_added']} 个文本块")
        else:
            st.error(r.text)
    if st.button("清空对话"):
        st.session_state.messages = []
        st.rerun()
步骤 2：对话状态与引用展示
python
if "messages" not in st.session_state:
    st.session_state.messages = []
﻿
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("sources"):
            with st.expander("📎 引用来源"):
                for s in msg["sources"]:
                    st.caption(f"{s['source']} · 页 {s['page']} · 块 {s['chunk_index']}")
﻿
if query := st.chat_input("输入运维问题…"):
    st.session_state.messages.append({"role": "user", "content": query})
    with st.chat_message("user"):
        st.markdown(query)
﻿
    with st.chat_message("assistant"):
        with st.spinner("检索并生成中…"):
            r = requests.post(f"{API_BASE}/ask", json={"query": query, "top_k": 3})
        data = r.json()
        st.markdown(data["answer"])
        sources = data.get("sources", [])
        with st.expander("📎 引用来源"):
            for s in sources:
                st.caption(f"{s['source']} · 页 {s['page']} · 块 {s['chunk_index']}")
    st.session_state.messages.append(
        {"role": "assistant", "content": data["answer"], "sources": sources}
    )
步骤 3：先用同步 /ask 跑通，再考虑流式
Streamlit 对 SSE 的原生支持不如 Web 前端方便。今天下午优先保证“同步问答 + 引用展示 + 上传”完整可用，这是可演示的最小闭环。流式可以留到 D24 部署之后再优化——面试时你有一个可访问的链接，比一个“流式但打不开”的半成品强十倍。
任务 5（60 分钟）：本地联调 + 截图证据
终端 A：cd d22_api
uvicorn main:app --port 8002
终端 B：streamlit run d22_streamlit/app.py
保存三张截图： ① Swagger /docs 四端点齐全；② curl -N 流式输出；③ Streamlit 聊天界面带展开的引用来源。
任务 6（60 分钟）：面试话术整理 + Git 提交
2 分钟讲解稿（对着截图讲）：
“今天我把 D21 的 CLI RAG 升级成了 API + 前端。后端是 FastAPI，四个端点：/health 做健康检查，/upload 支持增量入库，/ask 同步问答，/ask/stream 用 SSE 流式输出。流式选 SSE 而不是 WebSocket，因为 RAG 是服务端单向推文字，SSE 基于 HTTP、网关友好、实现成本低。SSE 这里我做了三件事：事件带 type 让前端区分 token 和结束信号、设置 X-Accel-Buffering: no 防止代理缓冲、用 is_disconnected 检测断连。前端是 Streamlit，每个回答下面有可展开的引用来源，点到具体文档和页码。下一步是 Docker 化部署到云服务器，拿公网链接。”
Git 提交：
bash
git add d22_api/ d22_streamlit/
git commit -m "D22: FastAPI RAG service (/health /upload /ask /ask/stream) + Streamlit frontend with citation display"
git push origin main




整理：
第一步：建文件夹和空文件
在 VS Code 左侧的 Project_A_V3 目录上右键，选择“新建文件夹”，命名为 d22_api。
然后在这个 d22_api 文件夹里，新建三个文件：
1. rag_service.py （负责大模型的检索和回答）
2. ingest_service.py （负责解析上传的新文件并入库）
3. main.py （负责提供 API 接口）
第二步：写 rag_service.py（把 D21 的知识搬过来）
打开 rag_service.py，把下面的代码全部复制进去。这就是你在 D21 写的核心逻辑，我把它封装成了一个独立的函数。
python
# 文件路径：d22_api/rag_service.py
import os
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
import chromadb
from sentence_transformers import SentenceTransformer
from openai import OpenAI
﻿
# 1. 初始化模型和数据库（路径注意用 ../ 退到上一级）
print("正在加载本地模型和向量库...")
model = SentenceTransformer("BAAI/bge-small-zh-v1.5")
client_db = chromadb.PersistentClient(path="../chroma_db")
collection = client_db.get_collection(name="sop_knowledge_base")
﻿
# 2. 初始化 DeepSeek（把你 D21 的 API Key 粘贴到这里）
client_llm = OpenAI(
    api_key="sk-你的DeepSeekKey", 
    base_url="https://api.deepseek.com"
)
﻿
SYSTEM_PROMPT = """你是一个严谨的运维知识库助手。请遵守以下规则：
1. 只根据下面提供的〖参考资料〗回答用户问题。
2. 不要使用参考资料之外的事实性信息。
3. 如果参考资料中没有足够信息，请直接输出：“根据当前知识库资料，我无法确定这个问题的答案。”
4. 每个关键结论必须标注引用的材料编号，格式如 〖材料1〗。"""
﻿
def ask(query, top_k=3):
    """核心问答函数"""
    # 检索
    query_emb = model.encode([query]).tolist()
    results = collection.query(query_embeddings=query_emb, n_results=top_k, include=["documents", "metadatas"])
    
    chunks = results["documents"][0]
    metadatas = results["metadatas"][0]
    
    # 拼上下文
    context_blocks = []
    for i in range(len(chunks)):
        block = f"〖材料{i+1}〗来源：{metadatas[i].get('source')} | 页：{metadatas[i].get('page')}\n{chunks[i]}"
        context_blocks.append(block)
    
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"〖参考资料〗\n{chr(10).join(context_blocks)}\n\n〖用户问题〗\n{query}"}
    ]
    
    # 调大模型
    response = client_llm.chat.completions.create(
        model="deepseek-chat", messages=messages, temperature=0.1, timeout=30
    )
    answer = response.choices[0].message.content
    
    return answer, metadatas
第三步：写 ingest_service.py（处理上传的新文件）
打开 ingest_service.py，把代码复制进去。这个文件负责把你以后上传的文档，切块后塞进 Chroma 数据库。
python
# 文件路径：d22_api/ingest_service.py
import os
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
from pathlib import Path
from pypdf import PdfReader
from docx import Document
from sentence_transformers import SentenceTransformer
import chromadb
import uuid
﻿
model = SentenceTransformer("BAAI/bge-small-zh-v1.5")
client = chromadb.PersistentClient(path="../chroma_db")
collection = client.get_collection("sop_knowledge_base")
﻿
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
﻿
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
﻿
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
第四步：写 main.py（搭建 FastAPI 的大门）
打开 main.py，复制以下代码。这是把上面两个文件包装成 Web API 接口的代码。
python
# 文件路径：d22_api/main.py
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from pathlib import Path
import shutil
﻿
# 导入刚才写好的两个业务模块
from rag_service import ask
from ingest_service import parse_and_index
﻿
app = FastAPI(title="RAG TriageGPT API", version="1.0")
﻿
# 允许跨域（方便以后 Streamlit 前端调用）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)
﻿
# --- 定义接口的请求和响应格式 ---
class AskRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    top_k: int = Field(default=3, ge=1, le=10)
﻿
class SourceItem(BaseModel):
    source: str
    page: int
    chunk_index: int
﻿
class AskResponse(BaseModel):
    answer: str
    sources: list[SourceItem]
﻿
# --- 1. 健康检查 ---
@app.get("/health")
def health():
    return {"status": "ok", "service": "RAG TriageGPT-V1.0"}
﻿
# --- 2. 文件上传并增量入库 ---
@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    allowed = {".md", ".pdf", ".docx"}
    suffix = Path(file.filename).suffix.lower()
    if suffix not in allowed:
        raise HTTPException(status_code=400, detail=f"不支持的文件格式: {suffix}")
﻿
    # 保存文件
    save_dir = Path("d22_uploads")
    save_dir.mkdir(exist_ok=True)
    save_path = save_dir / file.filename
    
    with save_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
﻿
    # 调用入库逻辑
    chunk_count = parse_and_index(save_path)
    return {"filename": file.filename, "chunks_added": chunk_count}
﻿
# --- 3. 问答接口 ---
@app.post("/ask", response_model=AskResponse)
def ask_endpoint(req: AskRequest):
    answer, metadatas = ask(req.query, top_k=req.top_k)
    sources = [SourceItem(source=m["source"], page=m["page"], chunk_index=m["chunk_index"]) for m in metadatas]
    return AskResponse(answer=answer, sources=sources)
第五步：跑起来看看！
现在所有文件都写好了，我们让它跑起来。
1. 在 VS Code 的终端里，确保你进入了 d22_api 文件夹：
bash
cd d22_api
1. 输入以下命令启动服务：
bash
uvicorn main:app --reload --port 8002
1. 当你看到终端显示 Application startup complete. 时，在浏览器中打开：👉 http://127.0.0.1:8002/docs
2. 你会看到一个非常高级的 Swagger 接口文档界面。里面有三个接口：
/health：点击 Try it out -> Execute，会返回 {"status": "ok"}。
/upload：你可以随便上传一下你本地的 it_ops_manual.md，看看会不会返回 {"chunks_added": xx}。
/ask：点击 Try it out，在 Request body 里输入 {"query": "电子餐牌屏幕不亮怎么办", "top_k": 3}，点击 Execute。你会看到它返回了答案和引用清单！

太棒了！既然上午的 FastAPI 接口已经跑通了，下午我们就给这个“大脑”装上一个好看且实用的“脸面”——Streamlit 前端。
这一块的目标非常明确：让任何人（面试官、前同事、你自己）打开一个网页，就能像用 ChatGPT 一样，上传文档、问问题，并且能看到回答是出自哪份文档的哪一页。
跟着下面的步骤一步一步来，我会告诉你每个文件建在哪里、终端敲什么。
任务 4（120 分钟）：搭建 Streamlit 聊天界面
第一步：建文件夹和安装依赖（5 分钟）
1. 在 VS Code 左侧 Project_A_V3 目录下，右键新建一个文件夹，叫 d22_streamlit。
2. 在里面新建一个文件，叫 app.py。
3. 打开 VS Code 的终端，确保你退回到了 Project_A_V3 的根目录（如果还在 d22_api 里，敲 cd .. 退出来）。
4. 在终端运行安装命令：
bash
pip install streamlit requests
第二步：编写前端代码（30 分钟）
把下面的代码完整复制进你刚建好的 d22_streamlit/app.py 里。
这份代码不仅实现了聊天，还实现了你 D22 计划里要求的“引用展示”、“上传文档”和“清空对话”。 我在关键地方加了注释，帮你复习。
python
# 文件路径：d22_streamlit/app.py
import streamlit as st
import requests
﻿
# 这就是你上午跑通的 FastAPI 服务地址
API_BASE = "http://127.0.0.1:8002"
﻿
# 1. 页面基本设置
st.set_page_config(page_title="RAG TriageGPT", page_icon="🤖", layout="wide")
st.title("🤖 RAG TriageGPT-V1.0 · 智能运维知识库")
st.caption("基于 FastAPI + Chroma + DeepSeek 构建的交付级 RAG 演示系统")
﻿
# 2. 侧边栏：知识库管理（上传文档、清空对话）
with st.sidebar:
    st.header("📁 知识库管理")
    
    # 文件上传器
    uploaded_file = st.file_uploader("上传 SOP / 手册 / 笔记 (支持 .md, .pdf, .docx)", type=["md", "pdf", "docx"])
    
    # 如果有文件上传，触发 FastAPI 的 /upload 接口
    if uploaded_file and st.button("开始解析并入库"):
        with st.spinner("正在解析并向量化..."):
            # 构造请求发送给 FastAPI
            files = {"file": (uploaded_file.name, uploaded_file.getvalue())}
            try:
                r = requests.post(f"{API_BASE}/upload", files=files)
                if r.status_code == 200:
                    st.success(f"入库成功！新增 {r.json()['chunks_added']} 个文本块。")
                else:
                    st.error(f"上传失败：{r.text}")
            except Exception as e:
                st.error(f"连接后端失败，请确保 FastAPI 正在运行。错误：{e}")
                
    st.divider()
    
    # 清空对话按钮
    if st.button("🗑️ 清空当前对话"):
        st.session_state.messages = []
        st.rerun()
﻿
# 3. 主界面：聊天记录展示
# 使用 st.session_state 来保存聊天记录，防止刷新页面时丢失
if "messages" not in st.session_state:
    st.session_state.messages = []
﻿
# 遍历并渲染历史记录
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        # 如果这条消息是助手回答，且有引用来源，就显示折叠面板
        if msg["role"] == "assistant" and msg.get("sources"):
            with st.expander("📎 查看引用来源"):
                for s in msg["sources"]:
                    st.caption(f"**{s['source']}** · 页 {s['page']} · 块 {s['chunk_index']}")
﻿
# 4. 底部输入框与问答逻辑
# st.chat_input 会在页面底部生成一个聊天输入框
if query := st.chat_input("请输入你的运维问题（如：电子餐牌屏幕不亮）..."):
    
    # 1. 立即把用户的问题显示在屏幕上
    st.session_state.messages.append({"role": "user", "content": query})
    with st.chat_message("user"):
        st.markdown(query)
﻿
    # 2. 调用 FastAPI 的 /ask 接口获取回答
    with st.chat_message("assistant"):
        with st.spinner("RAG TriageGPT 正在检索并生成回答..."):
            try:
                # 发送同步请求
                payload = {"query": query, "top_k": 3}
                r = requests.post(f"{API_BASE}/ask", json=payload)
                
                if r.status_code == 200:
                    data = r.json()
                    answer = data["answer"]
                    sources = data.get("sources", [])
                    
                    # 渲染大模型的回答
                    st.markdown(answer)
                    
                    # 渲染引用来源
                    if sources:
                        with st.expander("📎 查看引用来源"):
                            for s in sources:
                                st.caption(f"**{s['source']}** · 页 {s['page']} · 块 {s['chunk_index']}")
                    
                    # 保存到历史记录
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": answer,
                        "sources": sources
                    })
                else:
                    st.error(f"接口报错：{r.text}")
            except Exception as e:
                st.error(f"连接失败：{e}")
任务 5（60 分钟）：本地联调与截图
现在，我们要把“大脑”（FastAPI）和“脸面”（Streamlit）同时启动起来。
第一步：双终端启动
1. 打开 VS Code 的终端（终端 A），进入 API 目录并启动：
bash
cd d22_api
uvicorn main:app --port 8002
（看到 Application startup complete. 说明启动成功）
1. 点击 VS Code 终端面板右上角的 + 号，新建一个终端 B，进入前端目录并启动：
bash
cd d22_streamlit
streamlit run app.py
（终端会弹出一个本地网络地址，通常是 http://localhost:8501，浏览器会自动打开）
第二步：浏览器实测（极度关键）
在打开的网页里，测试以下三个场景，这是你今天下午的验收标准：
1. 正常问答与引用：
在输入框输入：“电子餐牌屏幕不亮，应该检查什么？”
验收点：回答正常输出，回答下方出现一个折叠框“📎 查看引用来源”，点开能看到文件名为 it_ops_manual.md，页码和块号。
1. 上传功能：
在左侧边栏点击“Browse files”，选一个你本地的小 .md 文件（比如随便写一个 测试上传.md，里面写一句“如果电脑死机，请拔掉电源”）。
点击“开始解析并入库”。
验收点：提示“入库成功！新增 1 个文本块。”。然后你回到对话框问“电脑死机怎么办”，看它能不能回答出来。
1. 拒答机制：
在输入框问：“公司停车场怎么收费？”
验收点：模型输出类似“根据当前知识库资料，我无法确定这个问题的答案。”，且拒绝瞎编。
第三步：截图存档（为面试准备）
将以下三张图保存到一个新建的 docs 文件夹里（或者直接保存在你桌面上）：
1. Swagger 截图：打开 http://127.0.0.1:8002/docs，截全屏，证明你有 3 个 API。
2. Streamlit 问答截图：截出网页聊天界面，一定要把“📎 查看引用来源”点开截图。
3. 终端截图：展示 FastAPI 和 Streamlit 同时在运行。




﻿
