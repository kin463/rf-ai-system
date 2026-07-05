from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import requests
import os

app = FastAPI()

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class QueryRequest(BaseModel):
    question: str

@app.get("/")
async def get_index():
    return FileResponse("index.html")

@app.post("/api/ask")
async def ask_grok(payload: QueryRequest):
    if not os.path.exists("rules.txt"):
        return {"answer": "システムエラー: マニュアルが見つかりません。"}
    
    with open("rules.txt", "r", encoding="utf-8") as f:
        rules_content = f.read()

    api_key = os.environ.get("GROQ_API_KEY")
    
    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [
                    {"role": "system", "content": f"社内規定マニュアルに基づき、簡潔に回答せよ：\n{rules_content}"},
                    {"role": "user", "content": payload.question}
                ],
                "temperature": 0.0
            }
        )
        
        # 429エラー(制限)時の処理
        if response.status_code == 429:
            return {"answer": "現在、AIの利用が集中しています。数分待ってからもう一度送信してください。"}
        
        response.raise_for_status()
        return {"answer": response.json()["choices"][0]["message"]["content"]}
    except Exception as e:
        return {"answer": f"通信エラーが発生しました: {str(e)}"}
