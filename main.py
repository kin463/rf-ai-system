import os
import re
import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str

# APIキーの読み込み
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

def get_relevant_sections(user_query: str) -> str:
    """マニュアルから関連する内容を抽出する関数"""
    full_content = ""
    # rules.txtとrules.txt2を読み込み
    for filename in ["rules.txt", "rules.txt2"]:
        if os.path.exists(filename):
            with open(filename, "r", encoding="utf-8") as f:
                full_content += f.read() + "\n"
    
    if not full_content: return "マニュアルデータが見つかりません。"

    # 単純なキーワードマッチング（全一致が難しい場合でもヒットさせる）
    sections = [s.strip() for s in re.split(r'\n\s*\r?\n', full_content) if s.strip()]
    keywords = user_query.split()
    
    hits = [s for s in sections if any(k in s for k in keywords)]
    return "\n\n".join(hits[:3]) if hits else full_content[:1500]

@app.post("/api/chat")
async def chat(request: ChatRequest):
    if not GROQ_API_KEY:
        return {"response": "システムエラー：APIキーが設定されていません。"}
        
    relevant_manual = get_relevant_sections(request.message)
    
    prompt = f"""あなたはR&F株式会社のAI秘書です。以下のマニュアル情報のみを根拠に回答してください。
    【マニュアル情報】
    {relevant_manual}
    【質問】
    {request.message}
    """
    
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.0
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            res_json = response.json()
            if "choices" in res_json:
                return {"response": res_json["choices"][0]["message"]["content"]}
            else:
                return {"response": f"AIエラー: {res_json}"}
    except Exception as e:
        return {"response": f"通信エラー: {str(e)}"}

@app.get("/")
async def get_index():
    return FileResponse("index.html")
