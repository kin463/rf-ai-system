from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import requests
import os

app = FastAPI(title="R&F株式会社 社内AIアシスタント Backend")

# CORSの設定（フロントエンド HTML からの通信を許可）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🔑 Groq APIキー
GROK_API_KEY = os.environ.get("GROQ_API_KEY") 

class QueryRequest(BaseModel):
    question: str

# 1. ルートアクセス時に index.html を返す
@app.get("/")
async def get_index():
    return FileResponse("index.html")

# 2. AIとの通信用 API
@app.post("/api/ask")
async def ask_grok(payload: QueryRequest):
    rules_content = ""
    rules_file_path = "rules.txt"
    if os.path.exists(rules_file_path):
        with open(rules_file_path, "r", encoding="utf-8") as f:
            rules_content = f.read()
    else:
        raise HTTPException(status_code=500, detail="rules.txt が見つかりません。")

    system_instruction = (
        "# あなたの役割\n"
        "あなたはＲ＆Ｆ株式会社の極めて厳格で優秀な社内AIアシスタントです。\n"
        "以下の【社内マニュアル】に記載されている事実・データのみに基づいて回答してください。\n\n"
        f"# 【Ｒ＆Ｆ株式会社 社内規定・組織情報総合マニュアル】\n{rules_content}"
    )

    groq_url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROK_API_KEY}",
        "Content-Type": "application/json"
    }
    
    groq_payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": payload.question}
        ],
        "temperature": 0.0,
        "stream": False
    }

    try:
        response = requests.post(groq_url, json=groq_payload, headers=headers)
        response.raise_for_status()
        result = response.json()
        
        choices = result.get("choices", [])
        if choices:
            answer = choices[0].get("message", {}).get("content", "")
            return {"answer": answer}
        return {"answer": "回答を生成できませんでした。"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Render環境での起動用
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000)
