import os
import google.generativeai as genai
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

app = FastAPI()

# 環境変数から Gemini API キーを取得して設定
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# フロントエンドとの通信を許可
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str

def get_all_manuals() -> str:
    """社内規定ファイル（rules.txt）を読み込む"""
    if os.path.exists("rules.txt"):
        with open("rules.txt", "r", encoding="utf-8") as f:
            return f.read()
    return "社内マニュアルが見つかりません。"

@app.post("/api/chat")
async def chat(request: ChatRequest):
    # APIキーがRenderで正しく設定されているかチェック
    if not GEMINI_API_KEY:
        return {"response": "システムエラー：RenderのEnvironmentに GEMINI_API_KEY が設定されていません。"}
    
    manual_data = get_all_manuals()
    
    # AIへの指示（プロンプト）
    prompt = f"""あなたはR&F株式会社のAIアシスタントです。
    以下の【社内マニュアル】のみを根拠に回答してください。
    もしマニュアル内に回答が見当たらない場合は「マニュアルに記載がないため、正確な回答ができません」と答えてください。
    
    【社内マニュアル】
    {manual_data}
    
    【質問】
    {request.message}
    """
    
    try:
        # 軽くて速い gemini-1.5-flash モデルを使用
        model = genai.GenerativeModel('gemini-1.5-pro')
        response = model.generate_content(prompt)
        return {"response": response.text}
    except Exception as e:
        return {"response": f"Gemini API エラーが発生しました: {str(e)}"}

@app.get("/")
async def get_index():
    return FileResponse("index.html")
