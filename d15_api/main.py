from fastapi import FastAPI, UploadFile, File
from pydantic import BaseModel

app = FastAPI()

# 1. /health — 无参数，返回固定状态
@app.get("/health")
def health():
    return {"status": "ok"}

# 2. /echo — Query 参数
@app.get("/echo")
def echo(message: str = "hello"):
    return {"echo": message}

# 3. /upload — Body（文件上传）
@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    content = await file.read()
    return {"filename": file.filename, "size": len(content)}