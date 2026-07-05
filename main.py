import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import requests

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class QueryRequest(BaseModel):
    question: str

@app.get("/")
async def get_index():
    return FileResponse("index.html")

@app.post("/api/ask")
async def ask_grok(payload: QueryRequest):
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return {"answer": "システム設定エラー: APIキーが設定されていません。"}

    # ファイル読み込み（デバッグ用）
    base_dir = os.path.dirname(os.path.abspath(__file__))
    full_text = ""
    for filename in ["rules.txt", "rules.txt2"]:
        path = os.path.join(base_dir, filename)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                full_text += f.read() + "\n"

    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": "llama-3.1-8b-instant",
                "messages": [
                    {"role": "system", "content": "あなたはR&F社のAIアシスタントです。マニュアルの内容に基づき回答してください。"},
                    {"role": "user", "content": f"マニュアル内容: {full_text[:2000]}\n\n質問: {payload.question}"}
                ],
                "temperature": 0.0
            }
        )
        
        # エラー詳細を確認するための処理
        res_data = response.json()
        if "choices" in res_data:
            return {"answer": res_data["choices"][0]["message"]["content"]}
        else:
            return {"answer": f"APIレスポンスエラー: {res_data}"}
            
    except Exception as e:
        return {"answer": f"通信例外エラー: {str(e)}"}
