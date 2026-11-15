# 文件路径：d22_streamlit/app.py
import streamlit as st
import requests
import json
import os

# 后端 FastAPI 服务地址
API_BASE = "http://127.0.0.1:8002"
# 本地持久化存储聊天记录的文件
HISTORY_FILE = "chat_history.json"

# ==========================================
# 1. 数据持久化工具函数
# ==========================================
def load_chat_history() -> list:
    """从本地 JSON 文件加载历史记录，如果文件不存在则返回空列表"""
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_chat_history(messages: list):
    """将当前的聊天记录保存到本地 JSON 文件"""
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(messages, f, ensure_ascii=False, indent=2)

# ==========================================
# 2. 页面基本设置与 Session 初始化
# ==========================================
st.set_page_config(page_title="RAG TriageGPT", page_icon="🛠️", layout="wide")
st.title("🛠️ RAG TriageGPT · 企业智能运维知识库")
st.caption("基于 FastAPI + Chroma + DeepSeek 构建的交付级 RAG 演示系统。内置 300+ 条覆盖终端/服务器/网络/移动端的多维排障案例。")

# 如果内存中没有 messages，则从本地文件加载
if "messages" not in st.session_state:
    st.session_state.messages = load_chat_history()

# ==========================================
# 3. 侧边栏：知识库管理（上传文档、清空对话）
# ==========================================
with st.sidebar:
    st.header("📁 知识库管理")
    
    # 增加知识库介绍，彰显专业度
    st.info("""
    **当前内置知识库覆盖领域：**
    - 💻 电脑终端：华硕 / ROG / 联想
    - 📱 移动设备：华为 / vivo / OPPO / iPhone
    - 📺 显示与监控：三星电视 / 创维 / 海康威视
    - 🌐 底层架构：桌面运维 / 网络工程 / Linux / Python
    """)
    
    st.divider()
    
    # 文件上传器
    uploaded_file = st.file_uploader("上传新的 SOP / 排障手册 (支持 .md, .pdf, .docx)", type=["md", "pdf", "docx"])
    
    if uploaded_file and st.button("开始解析并入库"):
        with st.spinner("正在解析并向量化..."):
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
    if st.button("🗑️ 清空当前对话缓存"):
        st.session_state.messages = []
        save_chat_history([])  # 同时清空本地文件
        st.rerun()

# ==========================================
# 4. 主界面：渲染历史聊天记录
# ==========================================
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        # 渲染助手回答的引用来源
        if msg["role"] == "assistant" and msg.get("sources"):
            with st.expander("📎 查看引用来源"):
                for s in msg["sources"]:
                    st.caption(f"**{s['source']}** · 页 {s['page']} · 块 {s['chunk_index']}")

# ==========================================
# 5. 底部输入框与问答交互逻辑
# ==========================================
# 修改了输入框的提示词，引导用户提问真实运维问题
if query := st.chat_input("请输入故障现象（如：ROG开机黑屏、Linux磁盘满了、海康监控掉线）..."):
    
    # 5.1 渲染并保存用户提问
    st.session_state.messages.append({"role": "user", "content": query})
    save_chat_history(st.session_state.messages) # 写入本地
    with st.chat_message("user"):
        st.markdown(query)

    # 5.2 请求大模型并渲染回答
    with st.chat_message("assistant"):
        with st.spinner("RAG TriageGPT 正在检索并生成回答..."):
            try:
                payload = {"query": query, "top_k": 3}
                r = requests.post(f"{API_BASE}/ask", json=payload)
                
                if r.status_code == 200:
                    data = r.json()
                    answer = data["answer"]
                    sources = data.get("sources", [])
                    
                    # 渲染文本
                    st.markdown(answer)
                    
                    # 渲染引用
                    if sources:
                        with st.expander("📎 查看引用来源"):
                            for s in sources:
                                st.caption(f"**{s['source']}** · 页 {s['page']} · 块 {s['chunk_index']}")
                    
                    # 保存 AI 回答至内存与本地
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": answer,
                        "sources": sources
                    })
                    save_chat_history(st.session_state.messages) # 写入本地
                else:
                    st.error(f"接口报错：{r.text}")
            except Exception as e:
                st.error(f"连接失败：{e}")