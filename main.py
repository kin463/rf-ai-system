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
    
    prompt = f"""あなたはR&F株式会社の専門AIアシスタントです。
    以下の【社内ルール資料】から、ユーザーの質問に対する答えを正確に抽出して回答してください。
    【回答ルール】
    1. ユーザーの名前が含まれる組織や帰社日を資料から探し出し、回答してください。
    2. 資料に答えがない場合は「記載がありません」と伝えてください。
    3. 余計な前置きは不要です。

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
