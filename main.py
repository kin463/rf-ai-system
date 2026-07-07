from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import httpx
import os
import re

app = FastAPI()

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class ChatRequest(BaseModel):
    message: str

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

def get_best_section(user_query: str, filepath: str) -> str:
    """最も関連性の高いセクションを1つだけ抽出し、トークン消費を抑える"""
    if not os.path.exists(filepath): return "規定資料が見つかりません。"
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except: return "資料読み込みエラー"
    
    sections = re.split(r'\n(?=\[)', content)
    best_section = sections[0]  # デフォルト
    max_score = 0
    
    # 質問に関連するセクションを特定
    for section in sections:
        score = sum(1 for kw in user_query if kw in section)
        if score > max_score:
            max_score = score
            best_section = section
    return best_section

@app.post("/api/chat")
async def chat(request: ChatRequest):
    relevant_section = get_best_section(request.message, "rules.txt")
    
    prompt = f"""あなたはR&F株式会社のAIアシスタントです。以下の資料に基づき簡潔に回答してください。
    【資料】
    {relevant_section}
    【質問】
    {request.message}
    """

    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.0
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            res = await client.post("https://api.groq.com/openai/v1/chat/completions", 
                                    json=payload, 
                                    headers={"Authorization": f"Bearer {GROQ_API_KEY}"})
            
            if res.status_code == 429:
                return {"response": "現在アクセスが集中しています。1分ほど待ってから再度お試しください。"}
            
            data = res.json()
            return {"response": data["choices"][0]["message"]["content"]}
        except Exception as e:
            return {"response": "通信エラーが発生しました。"}

@app.get("/")
async def get_index():
    return FileResponse("index.html")
