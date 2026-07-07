from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import httpx
import os
import re

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

def get_relevant_sections(user_query: str, filepath: str) -> str:
    """
    ルールファイルを読み込み、質問に関連するセクションを網羅的に抽出します。
    ファイル構成を変えずに最大限情報を拾うために、検索範囲を拡大しました。
    """
    if not os.path.exists(filepath):
        return ""
        
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception:
        return ""
    
    # ファイル全体を段落単位で分割
    sections = [s.strip() for s in content.split('\n\n') if s.strip()]
    
    scored_sections = []
    # 検索キーワードを広げ、ヒット率を向上
    for section in sections:
        score = 0
        # 人名、キーワードが少しでも含まれていれば加点
        if any(name in user_query for name in ["大関", "中山", "竹本", "山下", "山田", "石井"]): score += 100
        if any(kw in user_query for kw in ["所属", "課", "帰社日", "勉強会", "手当", "有給", "欠勤", "提出"]): score += 100
        if any(kw in user_query for kw in ["結婚", "死亡", "災害", "資格"]): score += 100
        
        # 該当セクションをリスト化
        if score > 0:
            scored_sections.append(section)
            
    # ヒットしたセクションをすべて結合（情報の欠落を防ぐ）
    return "\n\n".join(scored_sections if scored_sections else sections[:10])

@app.post("/api/chat")
async def chat(request: ChatRequest):
    user_message = request.message
    relevant_manual = get_relevant_sections(user_message, "rules.txt")
    
    # 強化されたプロンプト：資料を統合的に読み解く指示
    prompt = f"""あなたはR&F株式会社の専門AIアシスタントです。
    提供された【社内ルール資料】の内容を統合し、ユーザーの質問に正確に回答してください。

    【重要事項】
    1. ユーザーが社員名（例：竹本伊吹）を聞いた場合、資料内の「組織構成」セクションを読み解き回答してください。
    2. 制度（例：資格手当）について聞かれた場合、詳細な数値や条件を資料から抽出してください。
    3. 資料に情報が断片的に存在する場合でも、文脈を整理して論理的に説明してください。
    4. 質問に関連する情報がない場合は「記載がありません」と報告してください。

    【社内ルール資料】
    {relevant_manual}

    【ユーザーの質問】
    {user_message}
    """

    if not GROQ_API_KEY:
        return {"response": "APIキーが設定されていません。"}
        
    url = "https://api.groq.com/openai/v1/chat/completions"
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.0
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            res = await client.post(url, json=payload, headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"})
            text = res.json()["choices"][0]["message"]["content"]
            return {"response": text}
        except Exception as e:
            return {"response": f"通信エラーが発生しました: {str(e)}"}

@app.get("/")
async def get_index():
    return FileResponse("index.html")
