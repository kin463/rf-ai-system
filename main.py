from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import httpx
import os

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class ChatRequest(BaseModel):
    message: str

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

def get_full_manual(filepath: str) -> str:
    """検索せず、資料全体をそのまま返す（精度重視）"""
    if not os.path.exists(filepath): return "規定資料が見つかりません。"
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    except: return "資料読み込みエラー"

@app.post("/api/chat")
async def chat(request: ChatRequest):
    # 資料全体を読み込む
    manual_content = get_full_manual("rules.txt")
    
    prompt = f"""あなたはR&F株式会社のAIアシスタントです。
    提供された【社内ルール資料】の組織図と帰社日スケジュールを照らし合わせ、社員の帰社日を回答してください。

    【重要：検索のコツ】
    - ユーザーが質問した社員名が資料の「どこ」に記載されているか（どの課か）を確認してください。
    - 課を特定した後、その課に指定された帰社日を探し出してください。
    - もし入力された名前が資料と微妙に異なる場合（例：スペースの有無）でも、類似度が高い場合は回答してください。

    【社内ルール資料】
    {manual_content}

    【質問】
    {request.message}
    """

    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.0
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            res = await client.post("https://api.groq.com/openai/v1/chat/completions", 
                                    json=payload, 
                                    headers={"Authorization": f"Bearer {GROQ_API_KEY}"})
            data = res.json()
            if "choices" in data:
                return {"response": data["choices"][0]["message"]["content"]}
            return {"response": "回答が生成できませんでした。"}
        except Exception as e:
            return {"response": "サーバーエラーが発生しました。"}

@app.get("/")
async def get_index():
    return FileResponse("index.html")
