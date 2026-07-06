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
    manual_data = get_all_manuals()
    prompt = f"【社内マニュアル】\n{manual_data}\n\n質問: {request.message}\n回答してください。"
    
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.0
    }
    
    try:
        # タイムアウトを60秒に設定
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            res_json = response.json()
            
            # デバッグ用に構造を確認
            if "choices" in res_json:
                return {"response": res_json["choices"][0]["message"]["content"]}
            else:
                # 失敗した場合、生の応答を返す
                return {"response": f"APIエラー: {str(res_json)}"}
    except Exception as e:
        return {"response": f"通信エラーの詳細: {str(e)}"}

@app.get("/")
async def get_index():
    return FileResponse("index.html")
