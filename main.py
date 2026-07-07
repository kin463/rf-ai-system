from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import httpx
import os
import re

app = FastAPI()

# CORSの設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=False,  
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

def get_relevant_sections(user_query: str, filepath: str, max_sections: int = 4) -> str:
    """
    rules.txt から関連セクションを抽出します。
    組織構成や勉強会などのデータにも対応するため、max_sectionsを少し広げています。
    """
    if not os.path.exists(filepath):
        return ""
        
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        return ""
    
    # セクション分割（組織データなどは[見出し]で分かれていると想定）
    # 空行または[で始まる行を区切りとする
    sections = re.split(r'\n(?=\[)', content)
    
    # クエリの重要単語抽出
    blocks = re.findall(r'[\u4E00-\u9FFF\u30A0-\u30FF_a-zA-Z0-9ー]+', user_query)
    
    scored_sections = []
    for section in sections:
        score = 0
        for block in blocks:
            if block in section:
                score += 100
        
        # 特定キーワードのブースト（組織、帰社日、勉強会）
        if "帰社日" in user_query and "帰社日" in section: score += 150
        if "勉強会" in user_query and "勉強会" in section: score += 150
        if "所属" in user_query or any(name in user_query for name in ["課", "メンバー"]): score += 100
            
        if score > 0:
            scored_sections.append((score, section))
            
    scored_sections.sort(key=lambda x: x[0], reverse=True)
    
    # 上位セクションを結合
    top_sections = [s[1] for s in scored_sections[:max_sections]]
    return "\n\n".join(top_sections)

@app.post("/api/chat")
async def chat(request: ChatRequest):
    user_message = request.message
    
    # rules.txt を検索対象に変更
    relevant_manual = get_relevant_sections(user_message, "rules.txt", max_sections=4)
    
    if not relevant_manual.strip():
        return {"response": "マニュアルに記載がないため、会社へ直接お問い合わせください。"}

    prompt = f"""あなたは社員専用のFAQアシスタントです。提供された【社内ルール資料】のみを元に回答してください。

【回答のガイドライン】
1. 組織構成、帰社日、勉強会、各種規定について正確に答えてください。
2. 不要な前置きはせず、事実を簡潔に伝えてください。
3. 資格手当や休暇ルールは、資料の数値を正確に参照してください。

【社内ルール資料】
{relevant_manual}

【ユーザーの質問】
{user_message}
"""

    if not GROQ_API_KEY:
        return {"response": "APIキーが設定されていません。"}
        
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.0
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, json=payload, headers=headers)
        if response.status_code == 200:
            text = response.json()["choices"][0]["message"]["content"]
            return {"response": text.strip()}
        return {"response": "通信エラーが発生しました。"}

@app.get("/")
async def get_homepage():
    return FileResponse("index.html")
