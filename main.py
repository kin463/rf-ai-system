import os
import glob
import httpx
import re
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

app = FastAPI()

# CORS設定：あらゆるオリジンからのリクエストを許可
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str

# APIキーの取得
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

def get_all_manual_content():
    """すべてのテキストファイルを読み込み統合する"""
    combined_text = ""
    for file_path in glob.glob("*.txt"):
        with open(file_path, "r", encoding="utf-8") as f:
            combined_text += f.read() + "\n\n"
    return combined_text

def get_relevant_sections(user_query: str, all_text: str) -> str:
    """検索機能：重複を排除し、質問に関連するセクションを抽出する"""
    # 改行でセクションを分割し、ユニークなリストを作成
    raw_sections = [s.strip() for s in re.split(r'\n\s*\n', all_text) if s.strip()]
    unique_sections = list(set(raw_sections))
    
    scored_sections = []
    for section in unique_sections:
        score = 0
        # 質問に含まれるキーワードに基づいたスコアリング
        keywords = ["帰社日", "有給", "休暇", "手当", "提出", "連絡", "欠勤", "賞与"]
        if any(kw in user_query for kw in keywords):
            score += 10
        # 社員名によるスコアリング強化
        names = ["大関", "中山", "石井", "渡", "山田", "山崎", "陶山", "麻生", "宮田", "川田", "稲森", "中元"]
        if any(name in user_query for name in names):
            score += 50
        
        if score > 0:
            scored_sections.append((score, section))
            
    # スコアが高い順にソートし、上位5件を抽出
    scored_sections.sort(key=lambda x: x[0], reverse=True)
    return "\n\n".join([s[1] for s in scored_sections[:5]]) if scored_sections else all_text[:2000]

@app.post("/api/chat")
async def chat(request: ChatRequest):
    if not GROQ_API_KEY:
        return {"response": "システムエラー：APIキーが設定されていません。"}
    
    context = get_relevant_sections(request.message, get_all_manual_content())
    
    # 日本語プロンプト
    prompt = f"""あなたはR&F株式会社のAIアシスタントです。以下の【社内資料】の内容に基づき、正確かつ簡潔に回答してください。

    【制約事項】
    1. 帰社日とは「各課がオフィスに集まるスケジュール」を指します。
    2. 回答は簡潔にまとめ、同じ説明を繰り返さないでください。
    3. 資料に該当する情報がない場合は、憶測で答えず「記載がありません」と報告してください。

    【社内資料】
    {context}

    【ユーザーの質問】
    {request.message}
    """
    
    url = "https://api.groq.com/openai/v1/chat/completions"
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.0
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        res = await client.post(url, json=payload, headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"})
        return {"response": res.json()["choices"][0]["message"]["content"]}

@app.get("/")
async def get_index():
    return FileResponse("index.html")
