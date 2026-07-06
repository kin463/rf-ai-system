import os
import google.generativeai as genai
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

app = FastAPI()

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str

def get_all_manuals() -> str:
    if os.path.exists("rules.txt"):
        with open("rules.txt", "r", encoding="utf-8") as f:
            return f.read()
    return "社内マニュアルが見つかりません。"

@app.post("/api/chat")
async def chat(request: ChatRequest):
    if not GEMINI_API_KEY:
        return {"response": "システムエラー：APIキーが設定されていません。"}
    
    manual_data = get_all_manuals()
    prompt = f"あなたはR&F株式会社のAIアシスタントです。以下の【社内マニュアル】のみを根拠に回答してください。\n\n【社内マニュアル】\n{manual_data}\n\n【質問】\n{request.message}"
    
    try:
        # 現在利用可能なモデルをリストアップし、その中から最初の一つを使用する
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_methods]
        if not models:
            return {"response": "エラー：利用可能なモデルが見つかりません。"}
        
        # 取得したモデル名（例: 'models/gemini-1.5-flash-latest' など）を使って生成
        model = genai.GenerativeModel(models[0])
        response = model.generate_content(prompt)
        return {"response": response.text}
    except Exception as e:
        return {"response": f"Gemini API エラー詳細: {str(e)}"}

@app.get("/")
async def get_index():
    return FileResponse("index.html")
