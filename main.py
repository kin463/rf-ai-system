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
    if os.path.exists("rules.txt"):
        with open("rules.txt", "r", encoding="utf-8") as f:
            return f.read()
    return "社内マニュアルが見つかりません。"

@app.post("/api/chat")
async def chat(request: ChatRequest):
    if not GROQ_API_KEY:
        return {"response": "システムエラー：APIキーが設定されていません。RenderのEnvironment設定を確認してください。"}
        
    manual_data = get_all_manuals()
    
    prompt = f"""あなたはR&F株式会社のAIアシスタントです。
    以下の【社内マニュアル】のみを根拠に回答してください。
    記載がない場合は「マニュアルに記載がないため回答できません」と答えてください。
    
    【社内マニュアル】
    {manual_data}
    
    【質問】
    {request.message}
    """
    
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.0
    }
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            res_json = response.json()
            
            # デバッグ用：エラー内容を詳細に返す
            if "choices" in res_json:
                return {"response": res_json["choices"][0]["message"]["content"]}
            else:
                return {"response": f"APIエラーが発生しました。詳細: {str(res_json)}"}
                
    except Exception as e:
        return {"response": f"通信エラーの詳細: {str(e)}"}

@app.get("/")
async def get_index():
    return FileResponse("index.html")
