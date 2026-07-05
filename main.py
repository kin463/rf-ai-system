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
    
    # 全データを結合して保持
    full_text = ""
    for filename in ["rules.txt", "rules.txt2"]:
        file_path = os.path.join(base_dir, filename)
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                full_text += f.read() + "\n"

    # 【重要】キーワード検索で関連箇所だけを抽出（簡易RAG）
    # 質問に関連する行（文）だけを抽出して送信サイズを抑える
    lines = full_text.splitlines()
    # 質問に含まれる単語に関連しそうな行だけを抽出（例：寝坊 -> 連絡, 勤怠, 遅刻 など）
    relevant_lines = [line for line in lines if any(keyword in line for keyword in payload.question.split() if len(keyword) > 1)]
    
    # 関連行が見つからない場合は全ファイルの先頭3000文字で妥協する
    if not relevant_lines:
        context = full_text[:3000]
    else:
        context = "\n".join(relevant_lines)[:3000]

    api_key = os.environ.get("GROQ_API_KEY")
    
    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": "llama-3.1-8b-instant",
                "messages": [
                    {"role": "system", "content": f"社内規定マニュアルに基づき回答してください。関連情報:\n{context}"},
                    {"role": "user", "content": payload.question}
                ],
                "temperature": 0.0
            }
        )
        return {"answer": response.json()["choices"][0]["message"]["content"]}
    except Exception as e:
        return {"answer": f"通信エラー: {str(e)}"}
