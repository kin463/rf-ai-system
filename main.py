import os
import glob
import httpx
import re
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

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

def get_all_manual_content():
    """ディレクトリ内の全ての.txtファイルを読み込み、結合して返す"""
    combined_text = ""
    for file_path in glob.glob("*.txt"):
        with open(file_path, "r", encoding="utf-8") as f:
            combined_text += f.read() + "\n\n"
    return combined_text

def get_relevant_sections(user_query: str, all_text: str, max_sections: int = 3) -> str:
    """質問に関連する段落をスコアリングして抽出する"""
    # 段落（空行区切り）で分割
    sections = [s.strip() for s in re.split(r'\n\s*\r?\n', all_text) if s.strip()]
    
    # 質問文の主要な文字（2文字以上の単語）を抽出
    keywords = [user_query[i:i+2] for i in range(len(user_query)-1)]
    
    scored_sections = []
    for section in sections:
        score = sum(1 for kw in keywords if kw in section)
        if score > 0:
            scored_sections.append((score, section))
            
    # スコアが高い順にソート
    scored_sections.sort(key=lambda x: x[0], reverse=True)
    
    # 上位を結合して返す
    top_sections = [s[1] for s in scored_sections[:max_sections]]
    return "\n\n".join(top_sections)

@app.post("/api/chat")
async def chat(request: ChatRequest):
    if not GROQ_API_KEY:
        return {"response": "システムエラー：APIキーが設定されていません。"}
    
    # 全マニュアル（manual_shain.txt + rules.txt）を読み込み
    full_content = get_all_manual_content()
    
    # 関連セクションを抽出
    relevant_context = get_relevant_sections(request.message, full_content)
    
    # 関連情報がなければ冒頭部分を渡す（セーフガード）
    context_text = relevant_context if relevant_context else full_content[:1500]
    
    prompt = f"""あなたはR&F株式会社の社員専用FAQアシスタントです。
以下の【社内資料】に基づいて、質問に日本語で回答してください。
マニュアル内の事実を優先し、知らないことは「マニュアルに記載がないため回答できません」と答えてください。

【社内資料】
{context_text}

【質問】
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
        return {"response": f"通信エラーが発生しました: {str(e)}"}

@app.get("/")
async def get_homepage():
    return FileResponse("index.html")
