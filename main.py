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
    # ファイルパス設定
    base_dir = os.path.dirname(os.path.abspath(__file__))
    file_list = ["rules.txt", "rules.txt2"]
    
    # 1. 全ファイルを読み込み
    full_text = ""
    for filename in file_list:
        file_path = os.path.join(base_dir, filename)
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                full_text += f.read() + "\n"
    
    if not full_text:
        return {"answer": "システムエラー: マニュアルファイルが空です。"}

    # 2. 質問に関連する行だけを抽出（413エラー回避のためのRAG）
    lines = full_text.splitlines()
    query_words = payload.question.split()
    relevant_lines = [line for line in lines if any(word in line for word in query_words if len(word) > 1)]
    
    # 関連行が少ない場合は先頭部分を補填し、合計文字数を3000文字以内に調整
    if len(relevant_lines) < 5:
        context = full_text[:3000]
    else:
        context = "\n".join(relevant_lines)[:3000]

    # 3. APIリクエスト
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
                            "【重要】寝坊や体調不良などの緊急時は、必ず「現場連絡」→「LINE WORKSで営業担当とリーダーへ報告」を最優先として案内してください。\n"
                            "以下の社内規定に基づき、簡潔に回答せよ：\n"
                            f"{context}"
                        )
                    },
                    {"role": "user", "content": payload.question}
                ],
                "temperature": 0.0
            }
        )
        
        # エラーハンドリング
        if response.status_code == 413:
            return {"answer": "エラー：データ量が多すぎます。マニュアルを整理してください。"}
        if response.status_code == 429:
            return {"answer": "AIが非常に混雑しています。1分ほど待ってから再送してください。"}
            
        response.raise_for_status()
        return {"answer": response.json()["choices"][0]["message"]["content"]}
        
    except Exception as e:
        return {"answer": f"通信エラー: {str(e)}"}
