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
    """全テキストファイルを統合"""
    combined_text = ""
    for file_path in glob.glob("*.txt"):
        with open(file_path, "r", encoding="utf-8") as f:
            combined_text += f.read() + "\n\n"
    return combined_text

def get_relevant_sections(user_query: str, all_text: str) -> str:
    """検索ロジック：人名、課名、規定内容を動的に抽出"""
    # 帰社日スケジュールと規定本文を個別に扱う
    sections = re.split(r'\n(?=\[RandF|\n\()', all_text)
    
    scored_sections = []
    for section in sections:
        score = 0
        # 質問文中のキーワードをスコアリング
        if any(kw in user_query for kw in section):
            score += 100
        # 帰社日や人名が含まれる場合は加点
        if any(name in user_query for name in ["大関", "中山", "石井", "渡", "山田", "山崎"]):
            if any(name in section for name in ["大関", "中山", "石井", "渡", "山田", "山崎"]):
                score += 500
        
        if score > 0:
            scored_sections.append((score, section))
            
    scored_sections.sort(key=lambda x: x[0], reverse=True)
    # 上位3セクションをコンテキストとして返す
    return "\n\n".join([s[1] for s in scored_sections[:3]]) if scored_sections else all_text[:2000]

@app.post("/api/chat")
async def chat(request: ChatRequest):
    context = get_relevant_sections(request.message, get_all_manual_content())
    
    prompt = f"""あなたはR&F株式会社のAIアシスタントです。以下の資料に基づき正確に回答してください。
    社員情報の検索や帰社日の案内、有給や見舞金の規定など、全ての質問に対応します。
    
    【資料】
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
