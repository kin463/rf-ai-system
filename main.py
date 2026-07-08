import os
import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class ChatRequest(BaseModel):
    message: str

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

@app.post("/api/chat")
async def chat(request: ChatRequest):
    # 1. rules.txt を全読み込み
    try:
        with open("rules.txt", "r", encoding="utf-8") as f:
            full_context = f.read()
    except Exception:
        return {"response": "資料が読み込めません。"}
    
    # 2. AI へのプロンプト（「推論」を強化）
    # AIに「この人がどの部署のメンバーか」を資料から探させる
    prompt = f"""あなたはR&F株式会社のAIアシスタントです。
    提供された【資料】を読み込み、質問に回答してください。
    
    【ルール】
    - 質問された社員名がどの部署（課）のメンバーリストに含まれているかを探してください。
    - 該当する部署の「帰社日」を見つけて回答してください。
    - もし資料内に該当する名前がない場合は「その社員の情報は見つかりません」と答えてください。

    【資料】
    {full_context}

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
            data = res.json()
            return {"response": data["choices"][0]["message"]["content"]}
        except Exception:
            return {"response": "回答生成中にエラーが発生しました。"}

@app.get("/")
async def get_index():
    return FileResponse("index.html")
