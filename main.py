import os
import glob
import httpx
import re
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

def get_all_manuals():
    """全.txtを読み込み結合してセクション(段落)ごとに返す"""
    combined = ""
    for f_path in glob.glob("*.txt"):
        with open(f_path, "r", encoding="utf-8") as f:
            combined += f.read() + "\n\n"
    return [s.strip() for s in re.split(r'\n\s*\r?\n', combined) if s.strip()]

@app.post("/api/chat")
async def chat(request: ChatRequest):
    if not GROQ_API_KEY:
        return {"response": "システムエラー：APIキーが設定されていません。"}
    
    # 全セクションから質問に関連するものだけを抽出
    sections = get_all_manuals()
    relevant = [s for s in sections if any(kw in s for kw in request.message if len(kw) > 1)]
    context = "\n\n".join(relevant[:5]) if relevant else "\n\n".join(sections[:10])

    prompt = f"""あなたはR&F株式会社のAIアシスタントです。提供された資料に基づいて正確に回答してください。
    
【社内資料】
{context}

【ユーザーの質問】
{request.message}
"""
    
    url = "https://api.groq.com/openai/v1/chat/completions"
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.0
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        res = await client.post(url, json=payload, headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"})
        return {"response": res.json()["choices"][0]["message"]["content"]}

@app.get("/")
async def get_index():
    return FileResponse("index.html")
