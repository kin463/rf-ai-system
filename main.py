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
    # ファイルの読み込み
    base_dir = os.path.dirname(os.path.abspath(__file__))
    full_text = ""
    for filename in ["rules.txt", "rules.txt2"]:
        file_path = os.path.join(base_dir, filename)
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                full_text += f.read() + "\n"

    # 質問に基づくコンテキスト抽出（RAG）
    question = payload.question
    lines = full_text.splitlines()
    
    # 検索ロジックの強化
    if any(k in question for k in ["帰社日", "大関", "山田", "石井", "中山"]):
        # 人名や帰社日に関するキーワードがあればその周辺を抽出
        relevant_lines = [l for i, l in enumerate(lines) if any(n in l for n in ["帰社", "大関", "山田", "石井", "中山"])]
    elif any(k in question for k in ["勉強会", "講師", "評価"]):
        relevant_lines = [l for i, l in enumerate(lines) if any(k in l for k in ["勉強会", "講師", "評価"])]
    elif any(k in question for k in ["議事録", "MTG", "テンプレート"]):
        relevant_lines = [l for i, l in enumerate(lines) if any(k in l for k in ["議事録", "概要", "決定事項"])]
    else:
        relevant_lines = lines # それ以外は全体から（文字数制限のため注意）
    
    context = "\n".join(relevant_lines)[-3000:]

    api_key = os.environ.get("GROQ_API_KEY")
    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": "llama-3.1-8b-instant",
                "messages": [
                    {"role": "system", "content": (
                        "あなたはR&F株式会社の優秀な社内AIアシスタントです。\n"
                        "緊急時(寝坊等)は「現場連絡」→「LINE WORKSで営業担当とリーダーへ報告」を最優先で案内してください。\n"
                        "提供されたデータを元に、正確かつ簡潔に回答してください。\n"
                        f"【データソース】\n{context}"
                    )},
                    {"role": "user", "content": question}
                ],
                "temperature": 0.0
            }
        )
        return {"answer": response.json()["choices"][0]["message"]["content"]}
    except Exception as e:
        return {"answer": f"エラー: {str(e)}"}
