import os
import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

app = FastAPI()

# CORS設定：フロントエンドとの通信を許可
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str

# RAG用の補助関数：手動（rules.txt）を段落ごとに読み込む
def get_relevant_manual_context(query: str) -> str:
    if not os.path.exists("rules.txt"):
        return "規定ファイルが見つかりません。"
    
    with open("rules.txt", "r", encoding="utf-8") as f:
        # 改行で段落を分割
        paragraphs = [p.strip() for p in f.read().split("\n\n") if p.strip()]
    
    # 質問に関連する段落だけを抽出（単純なキーワードマッチング）
    relevant = [p for p in paragraphs if any(k in p for k in query.split())]
    return "\n".join(relevant) if relevant else "規定に記載がありません。"

@app.post("/api/chat")
async def chat(request: ChatRequest):
    groq_api_key = os.environ.get("GROQ_API_KEY", "")
    if not groq_api_key:
        return {"response": "システムエラー：APIキーが設定されていません。"}
    
    # 関連情報の取得
    context = get_relevant_manual_context(request.message)

    # プロンプトの組み立て
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {groq_api_key}", "Content-Type": "application/json"}
    
    prompt = f"""あなたはR&F株式会社のAIアシスタントです。
以下の【社内規定】のみを根拠にして、質問に日本語で回答してください。
規定に該当する情報がない場合は「規定に記載がないため、正確な回答ができません」と答えてください。

【社内規定】
{context}

【質問】
{request.message}
"""
    
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            return {"response": data["choices"][0]["message"]["content"]}
    except Exception as e:
        return {"response": f"AI通信エラーが発生しました: {str(e)}"}

@app.get("/")
async def get_index():
    return FileResponse("index.html")
