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
    # ファイル読み込みチェック
    if not os.path.exists("rules.txt"):
        raise HTTPException(status_code=500, detail="rules.txt が見つかりません")
    
    with open("rules.txt", "r", encoding="utf-8") as f:
        rules_content = f.read()

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="APIキーが設定されていません")

    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [
                    {"role": "system", "content": f"以下のマニュアルに基づき回答してください：\n{rules_content}"},
                    {"role": "user", "content": payload.question}
                ],
                "temperature": 0.0
            }
        )
        response.raise_for_status()
        return {"answer": response.json()["choices"][0]["message"]["content"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
