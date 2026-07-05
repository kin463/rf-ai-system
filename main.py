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
    file_list = ["rules.txt", "rules.txt2"]
    
    # 1. ファイル内容を統合
    full_text = ""
    for filename in file_list:
        file_path = os.path.join(base_dir, filename)
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                full_text += f.read() + "\n"
    
    # 2. RAG (関連情報の抽出): 質問の単語が含まれる行を優先抽出
    lines = full_text.splitlines()
    query_words = [w for w in payload.question.split() if len(w) > 0]
    relevant_lines = [line for line in lines if any(word in line for word in query_words)]
    
    # 抽出結果が少なければ先頭から補填し、サイズ制限内でコンテキストを作成
    context = "\n".join(relevant_lines)
    if len(context) < 500:
        context = full_text[:3000]
    else:
        context = context[:3000]

    # 3. AIへのリクエスト
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
                            "あなたはR&Fの社内AIアシスタントです。\n"
                            "【重要】寝坊・体調不良等の緊急時は「現場連絡」→「LINE WORKSで営業担当とリーダーへ報告」を最優先で案内すること。\n"
                            "以下の社内規定に基づき、簡潔かつ正確に回答してください。\n"
                            f"【参照データ】\n{context}"
                        )
                    },
                    {"role": "user", "content": payload.question}
                ],
                "temperature": 0.0
            }
        )
        
        if response.status_code == 429:
            return {"answer": "AIが混雑しています。1分ほど待ってから再送してください。"}
        if response.status_code == 413:
            return {"answer": "データサイズ制限エラー。管理者へ確認してください。"}
            
        response.raise_for_status()
        return {"answer": response.json()["choices"][0]["message"]["content"]}
        
    except Exception as e:
        return {"answer": f"通信エラー: {str(e)}"}
