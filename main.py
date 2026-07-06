import os
import glob
import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import re

app = FastAPI()

# CORSの設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str

# GROQ_API_KEYを環境変数から取得
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

def load_and_merge_manuals():
    """ディレクトリ内の全.txtを結合してセクションごとに分割する"""
    all_text = ""
    for file_path in glob.glob("*.txt"):
        with open(file_path, "r", encoding="utf-8") as f:
            all_text += f.read() + "\n\n"
    
    # 改行でセクションに分割
    sections = re.split(r'\n\s*\r?\n', all_text)
    return [s.strip() for s in sections if s.strip()]

def get_relevant_sections(user_query, sections):
    """質問に関連する段落をスコアリングして抽出"""
    scored_sections = []
    # 質問文をキーワードに分解
    keywords = [k for k in user_query if len(k) > 1]
    
    for section in sections:
        score = sum(1 for kw in keywords if kw in section)
        if score > 0:
            scored_sections.append((score, section))
            
    # スコア順にソートして上位3つを返す
    scored_sections.sort(key=lambda x: x[0], reverse=True)
    return "\n\n".join([s[1] for s in scored_sections[:3]])

@app.post("/api/chat")
async def chat(request: ChatRequest):
    if not GROQ_API_KEY:
        return {"response": "システムエラー：APIキーが設定されていません。"}
    
    sections = load_and_merge_manuals()
    relevant_context = get_relevant_sections(request.message, sections)
    
    # 関連情報がない場合は冒頭部分を渡す
    context_text = relevant_context if relevant_context else "\n\n".join(sections[:5])
    
    prompt = f"""あなたはR&F株式会社のAIアシスタントです。提供された【社内規定・資料】のみを根拠に回答してください。
    
【社内規定・資料】
{context_text}

【ユーザーの質問】
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
            data = response.json()
            return {"response": data["choices"][0]["message"]["content"]}
    except Exception as e:
        return {"response": f"通信エラーが発生しました: {str(e)}"}

@app.get("/")
async def get_index():
    return FileResponse("index.html")
