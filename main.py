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
    """最も関連性の高いセクションを1つだけ抽出し、トークン消費を抑える"""
    if not os.path.exists(filepath): return "規定資料が見つかりません。"
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except: return "資料読み込みエラー"
    
    sections = re.split(r'\n(?=\[)', content)
    
    # スコアリング：キーワードの出現回数で関連度を判定
    best_section = sections[0]
    max_score = 0
    for section in sections:
        # クエリ内の名詞を1つずつ検索してスコア加算
        score = sum(1 for kw in user_query if kw in section)
        if score > max_score:
            max_score = score
            best_section = section
    return best_section

@app.post("/api/chat")
async def chat(request: ChatRequest):
    user_message = request.message
    relevant_section = get_best_section(user_message, "rules.txt")
    
    # ユーザーの質問意図を正確に捉え、捏造や無関係な回答を防ぐプロンプト
    prompt = f"""あなたはR&F株式会社の専門AIアシスタントです。
    以下の【社内ルール資料】のみを使用して、ユーザーの質問にピンポイントで回答してください。

    【回答のルール】
    1. 質問と無関係な内容（休暇のルール等）は一切含めないでください。
    2. 資料内に質問された名称（例：「就労手当」）がない場合、類似した制度（例：「各種手当」、「基本給」など）を探し、「〇〇という項目はありますが、その名称の規定はありません」と正直に伝えてください。
    3. 資料に答えがない場合は「記載がありません」と回答してください。

    【社内ルール資料】
    {relevant_section}

    【ユーザーの質問】
    {user_message}
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
                return {"response": "現在アクセスが集中しています。1分ほど待ってから再度お試しください。"}
            
            data = res.json()
            return {"response": data["choices"][0]["message"]["content"]}
        except Exception as e:
            return {"response": "通信エラーが発生しました。時間を置いて再度お試しください。"}

@app.get("/")
async def get_index():
    return FileResponse("index.html")
