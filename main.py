import os
import re
import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

app = FastAPI()

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

def get_relevant_sections(user_query: str) -> str:
    """
    複数のマニュアルファイルを読み込み、関連性の高いセクションを抽出する
    """
    full_content = ""
    # rules.txtとrules.txt2の両方を読み込む
    for filename in ["rules.txt", "rules.txt2"]:
        if os.path.exists(filename):
            with open(filename, "r", encoding="utf-8") as f:
                full_content += f.read() + "\n"
    
    if not full_content:
        return ""

    # セクション分割
    sections = [s.strip() for s in re.split(r'\n\s*\r?\n', full_content) if s.strip()]
    
    # クエリキーワード抽出
    blocks = re.findall(r'[\u4E00-\u9FFF\u30A0-\u30FF_a-zA-Z0-9ーァ-ヶー]+', user_query)
    scored_sections = []

    for section in sections:
        score = 0
        for block in blocks:
            if block in section: score += 100
            elif len(block) >= 2 and any(block[i:i+2] in section for i in range(len(block)-1)): score += 40
        
        if score > 0:
            scored_sections.append((score, section))
            
    scored_sections.sort(key=lambda x: x[0], reverse=True)
    
    # 関連性の高い上位2セクションを結合
    return "\n\n".join([s[1] for s in scored_sections[:2]])

@app.post("/api/chat")
async def chat(request: ChatRequest):
    relevant_manual = get_relevant_sections(request.message)
    
    if not relevant_manual.strip():
        # マニュアルにない質問へのデフォルト対応
        relevant_manual = "社内規定に記載がない事柄については、営業担当またはリーダーにLINE WORKSで確認してください。"

    prompt = f"""あなたはR&F株式会社の社員専用FAQアシスタントです。
以下の【社内マニュアル】のみを根拠に回答してください。

【回答ガイドライン】
- 丁寧な日本語（です・ます調）で回答すること。
- マニュアルの事実をそのまま伝え、勝手な要約はしないこと。
- 前置きや結びの定型文は最小限にし、結論から答えること。

【社内マニュアル】
{relevant_manual}

【質問】
{request.message}
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
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            if response.status_code != 200:
                return {"response": "現在サーバーが混み合っています。少し待ってから再度お試しください。"}
            
            result = response.json()
            return {"response": result["choices"][0]["message"]["content"].strip()}
    except Exception as e:
        return {"response": f"通信エラーが発生しました: {str(e)}"}

@app.get("/")
async def get_index():
    return FileResponse("index.html")
