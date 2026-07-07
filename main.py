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
    """安全地讀取文件並提取相關內容，即使文件缺失也不會報錯"""
    if not os.path.exists(filepath):
        return "社內規定資料尚未設定。"
    
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception:
        return "資料讀取失敗。"
    
    # 按照 [見出し] 分割文件
    sections = re.split(r'\n(?=\[)', content)
    
    # 進行關鍵字比對，確保能拾取資訊
    scored_sections = []
    for section in sections:
        # 將資料庫中的內容與用戶問題進行比對
        if any(kw in user_query for kw in ["帰社日", "勉強会", "有給", "休暇", "手当", "欠勤", "資格", "組織", "連絡"]):
            scored_sections.append(section)
            
    return "\n\n".join(scored_sections if scored_sections else sections[:10])

@app.post("/api/chat")
async def chat(request: ChatRequest):
    user_message = request.message
    relevant_manual = get_relevant_sections(user_message, "rules.txt")
    
    # 系統指示 (Prompt)
    prompt = f"""あなたはR&F株式会社のAIアシスタントです。
    提供された【社内ルール資料】のみに基づき回答してください。

    【回答の指針】
    1. ユーザーの質問が曖昧な場合（例：「休暇」）は、具体的に何を知りたいか聞き返してください。
    2. 具体的な質問（例：竹本伊吹の所属、帰社日）には資料から数値を抽出して回答してください。
    3. 資料に情報がない場合は憶測せず「記載がありません」と伝えてください。
    4. 回答は簡潔にまとめてください。

    【社内ルール資料】
    {relevant_manual}

    【ユーザーの質問】
    {user_message}
    """

    if not GROQ_API_KEY:
        return {"response": "APIキーが設定されていません。環境変数を確認してください。"}
        
    url = "https://api.groq.com/openai/v1/chat/completions"
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.0
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            res = await client.post(url, json=payload, headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"})
            data = res.json()
            
            # 【重要】通信エラーやAPIの構造変化に対応した防衛的コーディング
            if "choices" in data and len(data["choices"]) > 0:
                answer = data["choices"][0].get("message", {}).get("content", "回答が生成されませんでした。")
                return {"response": answer}
            else:
                return {"response": f"AIからの返答が取得できませんでした。詳細: {str(data.get('error', '不明なエラー'))}"}
                
        except Exception as e:
            return {"response": f"システム通信エラー: {str(e)}"}

@app.get("/")
async def get_index():
    return FileResponse("index.html")
