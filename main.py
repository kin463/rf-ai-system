from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import httpx
import os
import re

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class ChatRequest(BaseModel):
    message: str

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

def get_best_section(user_query: str, filepath: str) -> str:
    """資料から最も関連性の高い1セクションを特定して抽出する"""
    if not os.path.exists(filepath): return "規定資料が見つかりません。"
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except: return "資料読み込みエラー"
    
    # [見出し]単位で分割
    sections = re.split(r'\n(?=\[)', content)
    
    best_section = sections[0]
    max_score = 0
    
    # ユーザーの質問に含まれる単語を解析してスコア付け
    query_words = [w for w in user_query.split() if len(w) > 1]
    
    for section in sections:
        score = 0
        # 人名やキーワードの出現をスコア化
        for word in query_words:
            if word in section:
                score += 20
        # 重要な見出しキーワードの加点
        if any(kw in section for kw in ["帰社日", "組織", "勉強会", "手当"]):
            score += 10
            
        if score > max_score:
            max_score = score
            best_section = section
            
    return best_section

@app.post("/api/chat")
async def chat(request: ChatRequest):
    if not GROQ_API_KEY:
        return {"response": "システムエラー：APIキーが設定されていません。"}

    relevant_section = get_best_section(request.message, "rules.txt")
    
    prompt = f"""あなたはR&F株式会社のAIアシスタントです。
    提供された【資料】に基づき、ユーザーの質問に簡潔に回答してください。
    【回答ルール】
    1. 質問と無関係な情報は含めないでください。
    2. 資料に答えがない場合は「記載がありません」と伝えてください。
    3. 資料が特定できれば、数値を正確に引用してください。

    【資料】
    {relevant_section}

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
            
            if res.status_code == 429:
                return {"response": "現在アクセスが集中しています。1分後に再度お試しください。"}
            
            data = res.json()
            if "choices" in data:
                return {"response": data["choices"][0]["message"]["content"]}
            return {"response": "回答の生成に失敗しました。"}
        except Exception as e:
            return {"response": "サーバーとの通信でエラーが発生しました。"}

@app.get("/")
async def get_index():
    return FileResponse("index.html")
