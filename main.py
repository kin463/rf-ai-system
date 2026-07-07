import os
import glob
import httpx
import re
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

def get_all_manual_content():
    """ディレクトリ内の全ての.txtファイルを結合して読み込む"""
    combined_text = ""
    # 複数のtxtファイルがある場合は全て読み込む
    for file_path in glob.glob("*.txt"):
        with open(file_path, "r", encoding="utf-8") as f:
            combined_text += f.read() + "\n\n"
    return combined_text

def get_relevant_sections(user_query: str, all_text: str) -> str:
    """質問に関連するセクションを抽出する（帰社日や人名検索に最適化）"""
    # 段落（空行）で分割
    sections = [s.strip() for s in re.split(r'\n\s*\r?\n', all_text) if s.strip()]
    
    # 検索のためのスコアリング
    scored_sections = []
    for section in sections:
        score = 0
        # 人名検索
        if any(name in user_query for name in ["大関", "中山", "陶山", "石井", "山田", "山崎", "渡"]):
            if any(name in section for name in ["大関", "中山", "陶山", "石井", "山田", "山崎", "渡"]):
                score += 500
        # 帰社日検索
        if "帰社日" in user_query and "帰社日" in section:
            score += 300
        # その他キーワード
        if any(kw in user_query for kw in ["連絡", "寝坊", "有給", "チーム"]):
            if any(kw in section for kw in ["連絡", "寝坊", "有給", "チーム"]):
                score += 100
        
        if score > 0:
            scored_sections.append((score, section))
            
    # スコア順にソートして上位を抽出
    scored_sections.sort(key=lambda x: x[0], reverse=True)
    return "\n\n".join([s[1] for s in scored_sections[:3]]) if scored_sections else all_text[:2000]

@app.post("/api/chat")
async def chat(request: ChatRequest):
    if not GROQ_API_KEY:
        return {"response": "システムエラー：APIキーが設定されていません。"}
    
    # 全マニュアル読み込み
    full_content = get_all_manual_content()
    # 関連情報抽出
    context = get_relevant_sections(request.message, full_content)
    
    prompt = f"""あなたはR&F株式会社のAIアシスタントです。
以下の【社内資料】に基づいて、質問に対して正確に回答してください。
帰社日のスケジュールや人名については、資料内の記述を優先し、曖昧な回答を避けてください。

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
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload, headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"})
            data = response.json()
            return {"response": data["choices"][0]["message"]["content"]}
    except Exception as e:
        return {"response": f"エラーが発生しました: {str(e)}"}

@app.get("/")
async def get_index():
    return FileResponse("index.html")
