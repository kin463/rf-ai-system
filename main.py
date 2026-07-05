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
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # マニュアル全文の読み込み
    full_text = ""
    for filename in ["rules.txt", "rules.txt2"]:
        file_path = os.path.join(base_dir, filename)
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                full_text += f.read() + "\n"

    # 【検索ロジック】質問内容に応じて重要度を付与
    question = payload.question
    lines = full_text.splitlines()
    
    # キーワードマッチングによる抽出
    if any(k in question for k in ["帰社日", "大関", "山田"]):
        relevant_lines = [l for l in lines if any(n in l for n in ["帰社", "大関", "山田", "田中"])]
    elif any(k in question for k in ["勉強会", "講師", "テーマ"]):
        relevant_lines = [l for l in lines if any(k in l for k in ["勉強会", "講師", "日時"])]
    elif any(k in question for k in ["議事録", "MTG", "テンプレート"]):
        relevant_lines = [l for l in lines if any(k in l for k in ["議事録", "概要", "決定事項", "進捗"])]
    else:
        # 通常時はマニュアルの重要規定を優先
        relevant_lines = lines[:200] 

    context = "\n".join(relevant_lines)[-3000:] # サイズ制限を厳守

    # AIへのリクエスト
    api_key = os.environ.get("GROQ_API_KEY")
    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": "llama-3.1-8b-instant",
                "messages": [
                    {
                        "role": "system", 
                        "content": (
                            "あなたはR&Fの社内AI秘書です。\n"
                            "【ルール】緊急時は現場連絡→LINE WORKS報告を最優先すること。\n"
                            "【知識源】以下のマニュアル内容に基づき回答してください。\n"
                            f"{context}"
                        )
                    },
                    {"role": "user", "content": question}
                ],
                "temperature": 0.0
            }
        )
        return {"answer": response.json()["choices"][0]["message"]["content"]}
    except Exception as e:
        return {"answer": f"システムエラー: {str(e)}"}
