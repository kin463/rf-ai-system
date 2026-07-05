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
    # ファイル読み込み
    base_dir = os.path.dirname(os.path.abspath(__file__))
    full_text = ""
    for filename in ["rules.txt", "rules.txt2"]:
        if os.path.exists(os.path.join(base_dir, filename)):
            with open(os.path.join(base_dir, filename), "r", encoding="utf-8") as f:
                full_text += f.read() + "\n"

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
                            "あなたはR&F株式会社の社内AI秘書です。\n"
                            "【重要ルール】\n"
                            "1. 提出先等の回答は必ず提供されたマニュアルの記述に従うこと（勝手に推測しない）。\n"
                            "2. 回答は簡潔にすること。同じ内容を繰り返さないこと（ループ禁止）。\n"
                            "3. 関連情報が見つからない場合は「規定に記載がありません」とだけ答えること。\n"
                            f"【マニュアル全文】\n{full_text}"
                        )
                    },
                    {"role": "user", "content": payload.question}
                ],
                "temperature": 0.0 # 創造的な回答を抑える
            }
        )
        return {"answer": response.json()["choices"][0]["message"]["content"]}
    except Exception as e:
        return {"answer": f"エラー: {str(e)}"}
