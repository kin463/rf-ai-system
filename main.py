import os
import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

def get_all_manuals() -> str:
    """全マニュアルを読み込む"""
    full_content = ""
    for filename in ["rules.txt", "rules.txt2"]:
        if os.path.exists(filename):
            with open(filename, "r", encoding="utf-8") as f:
                full_content += f.read() + "\n"
    return full_content if full_content else "マニュアルデータが見つかりません。"

@app.post("/api/chat")
async def chat(request: ChatRequest):
    if not GROQ_API_KEY:
        return {"response": "システムエラー：APIキーが設定されていません。"}
        
    manual_data = get_all_manuals()
    
    prompt = f"""あなたはR&F株式会社の厳格なAI秘書です。
    以下の【社内マニュアル】のみを根拠に回答してください。
    記載がない場合は「マニュアルに記載がないため回答できません。総務部へ確認してください」と答えてください。
    
    【社内マニュアル】
    {manual_data}

    【質問】
    {request.message}
    """
    
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": "正確で安全な社内AIアシスタントです。"},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.0
    }
    
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            res_json = response.json()
            if "choices" in res_json:
                return {"response": res_json["choices"][0]["message"]["content"]}
            else:
                return {"response": "AIからの応答生成に失敗しました。"}
    except httpx.ReadTimeout:
        return {"response": "回答の生成に時間がかかりすぎています。もう一度送信してください。"}
    except Exception as e:
        return {"response": f"エラーが発生しました: {str(e)}"}

@app.get("/")
async def get_index():
    return FileResponse("index.html")
