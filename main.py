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

    # 検索ロジック：質問内容に合わせて抽出箇所を切り替える
    question = payload.question
    lines = full_text.splitlines()
    
    if any(k in question for k in ["帰社日", "大関", "山田", "田中"]):
        relevant_lines = [l for l in lines if any(n in l for n in ["帰社", "大関", "山田", "田中"])]
    elif any(k in question for k in ["勉強会", "講師", "テーマ"]):
        relevant_lines = [l for l in lines if any(k in l for k in ["勉強会", "講師", "日時"])]
    elif any(k in question for k in ["議事録", "MTG", "テンプレート"]):
        relevant_lines = [l for l in lines if any(k in l for k in ["議事録", "概要", "決定事項", "進捗", "記入担当"])]
    else:
        relevant_lines = lines # 通常は全体を参照
    
    # AI送信サイズ制限（3000文字）
    context = "\n".join(relevant_lines)[-3000:]

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
                            "あなたはR&F株式会社のAI秘書です。\n"
                            "【重要】寝坊・体調不良等の緊急時は「現場連絡」→「LINE WORKSで営業担当とリーダーへ報告」を最優先で案内すること。\n"
                            "議事録の依頼には、提供されたテンプレートを用いて正確に回答してください。\n"
                            f"【参照データ】\n{context}"
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
