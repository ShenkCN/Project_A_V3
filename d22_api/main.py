# 文件路径：d22_api/main.py
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from pathlib import Path
import shutil

# 导入刚才写好的两个业务模块
from rag_service import ask
from ingest_service import parse_and_index

app = FastAPI(title="RAG TriageGPT API", version="1.0")

# 允许跨域（方便以后 Streamlit 前端调用）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)

# --- 定义接口的请求和响应格式 ---
class AskRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    top_k: int = Field(default=7, ge=1, le=10)

class SourceItem(BaseModel):
    source: str
    page: int
    chunk_index: int

class AskResponse(BaseModel):
    answer: str
    sources: list[SourceItem]

# --- 1. 健康检查 ---
@app.get("/health")
def health():
    return {"status": "ok", "service": "RAG TriageGPT-V1.0"}

# --- 2. 文件上传并增量入库 ---
@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    allowed = {".md", ".pdf", ".docx"}
    suffix = Path(file.filename).suffix.lower()
    if suffix not in allowed:
        raise HTTPException(status_code=400, detail=f"不支持的文件格式: {suffix}")

    # 保存文件
    save_dir = Path("d22_uploads")
    save_dir.mkdir(exist_ok=True)
    save_path = save_dir / file.filename
    
    with save_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # 调用入库逻辑
    chunk_count = parse_and_index(save_path)
    return {"filename": file.filename, "chunks_added": chunk_count}

# --- 3. 问答接口 ---
@app.post("/ask", response_model=AskResponse)
def ask_endpoint(req: AskRequest):
    answer, metadatas = ask(req.query, top_k=req.top_k)
    sources = [SourceItem(source=m["source"], page=m["page"], chunk_index=m["chunk_index"]) for m in metadatas]
    return AskResponse(answer=answer, sources=sources)