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

def get_all_manual_content():
    combined_text = ""
    for file_path in glob.glob("*.txt"):
        with open(file_path, "r", encoding="utf-8") as f:
            combined_text += f.read() + "\n\n"
    return combined_text

def get_relevant_sections(user_query: str, all_text: str) -> str:
    # 帰社日や人名検索に強いロジック
    sections = re.split(r'(\[RandF .*?\])', all_text)
    
    scored_sections = []
    # 質問に関連する名前やキーワードを抽出
    for i in range(1, len(sections), 2):
        header = sections[i]
        content = sections[i+1]
        score = 0
        
        if any(kw in user_query for kw in header + content):
            score += 1000
        if "帰社日" in user_query and "帰社日" in content:
            score += 500
            
        if score > 0:
            scored_sections.append(header + content)
            
    return "\n".join(scored_sections) if scored_sections else all_text[:2000]

@app.post("/api/chat")
async def chat(request: ChatRequest):
    if not GROQ_API_KEY:
        return {"response": "システムエラー：APIキーが設定されていません。"}
    
    context = get_relevant_sections(request.message, get_all_manual_content())
    
    prompt = f"""あなたはR&F株式会社のAIアシスタントです。以下の【社内資料】に基づいて正確に回答してください。
    
【社内資料】
{context}

【質問】
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
