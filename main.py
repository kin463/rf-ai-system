import os
import httpx
import random
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

app = FastAPI()

# フロントエンド設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str

def load_and_split_manual():
    """rules.txtを読み込み、段落ごとに分割する"""
    if not os.path.exists("rules.txt"):
        return []
    with open("rules.txt", "r", encoding="utf-8") as f:
        # 空行で段落を分割
        return [para for para in f.read().split("\n\n") if para.strip()]

@app.post("/api/chat")
async def chat(request: ChatRequest):
    # APIキーの取得（環境変数から読み込む）
    # 複数設定がある場合はカンマ区切りで読み込み、ランダムに選択（制限回避策）
    api_keys = os.environ.get("GROQ_API_KEYS", "").split(",")
    groq_key = random.choice(api_keys).strip()
    
    if not groq_key:
        return {"response": "システムエラー：APIキーが設定されていません。"}
    
    # RAG: 関連する段落を抽出
    manual_paragraphs = load_and_split_manual()
    keywords = request.message.split()
    relevant_context = [p for p in manual_paragraphs if any(k in p for k in keywords)]
    
    context_text = "\n".join(relevant_context) if relevant_context else "（社内規定に該当する記述が見当たりませんでした。）"
    
    # プロンプト作成
    prompt = f"""あなたはR&F株式会社のAIアシスタントです。以下の【社内規定】のみを根拠に回答してください。
規定に回答がない場合は「申し訳ありませんが、規定に記載がないため回答できません」と正直に答えてください。

【社内規定】
{context_text}

【質問】
{request.message}
"""
    
    # Groq API 呼び出し
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3 # 回答の精度を重視
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            data = response.json()
            return {"response": data["choices"][0]["message"]["content"]}
    except Exception as e:
        return {"response": f"通信エラーが発生しました: {str(e)}"}

@app.get("/")
async def get_index():
    return FileResponse("index.html")
