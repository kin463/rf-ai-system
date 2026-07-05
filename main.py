from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class QueryRequest(BaseModel):
    question: str

@app.post("/api/ask")
async def ask_grok(payload: QueryRequest):
    # ファイル存在確認と読み込み
    if not os.path.exists("rules.txt"):
        raise HTTPException(status_code=500, detail="rules.txt がサーバー上に存在しません")
        
    try:
        with open("rules.txt", "r", encoding="utf-8") as f:
            rules_content = f.read()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ファイル読み込みエラー: {str(e)}")

    # 以下、Groq API 呼び出しロジック（省略せずそのまま記述してください）
    # ... (既存のrequests.postコード) ...
    # APIキーが空でないかも確認
    if not os.environ.get("GROQ_API_KEY"):
        raise HTTPException(status_code=500, detail="APIキーが設定されていません")
    
    # 成功したら以下を返す
    return {"answer": "回答生成テスト成功"}
