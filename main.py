import os
import google.generativeai as genai
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

app = FastAPI()

# 環境変数から Gemini API キーを取得
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
    prompt = f"""あなたはR&F株式会社のAIアシスタントです。
    以下の【社内マニュアル】のみを根拠に回答してください。
    マニュアルに記載がない場合は「マニュアルに記載がないため、回答できません」と答えてください。
    
    【社内マニュアル】
    {manual_data}
    
    【質問】
    {request.message}
    """
    
    try:
        # モデル名に 'models/' を明示的に付与して呼び出しを試みる
        model = genai.GenerativeModel('models/gemini-1.5-flash')
        response = model.generate_content(prompt)
        return {"response": response.text}
    except Exception as e:
        # エラー詳細を返す（これでなぜダメなのかが判明します）
        return {"response": f"Gemini API エラー詳細: {str(e)}"}

@app.get("/")
async def get_index():
    return FileResponse("index.html")
