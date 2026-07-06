import os
import glob
import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

app = FastAPI()

# CORS設定：ブラウザからのアクセスを許可
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str

def load_and_split_manual():
    """
    ディレクトリ内のすべての .txt ファイルを読み込み、
    段落ごとに分割してリスト化する
    """
    all_text = ""
    # カレントディレクトリにあるすべての .txt を取得
    for file_path in glob.glob("*.txt"):
        with open(file_path, "r", encoding="utf-8") as f:
            all_text += f.read() + "\n\n"
    
    # 段落ごとに分割（空行で区切る）
    return [para for para in all_text.split("\n\n") if para.strip()]

@app.post("/api/chat")
async def chat(request: ChatRequest):
    # Renderの環境変数から GROQ_API_KEY を取得
    groq_api_key = os.environ.get("GROQ_API_KEY", "")
    if not groq_api_key:
        return {"response": "システムエラー：APIキー（GROQ_API_KEY）が設定されていません。"}
    
    # RAG: 質問に関連する段落だけを抽出
    manual_paragraphs = load_and_split_manual()
    keywords = request.message.split()
    
    # 質問に関連する内容を検索
    relevant_context = [p for p in manual_paragraphs if any(k in p for k in keywords)]
    
    # 関連情報がない場合のデフォルトメッセージ
    context_text = "\n".join(relevant_context) if relevant_context else "社内規定に該当する情報が見当たりませんでした。"
    
    # AIへの指示（プロンプト）
    prompt = f"""あなたはR&F株式会社のAIアシスタントです。
以下の【社内規定】のみを根拠にして、質問に日本語で回答してください。
規定に回答がない場合は「申し訳ありませんが、規定に記載がないため回答できません」と正直に答えてください。

【社内規定】
{context_text}

【質問】
{request.message}
"""
    
    # Groq API設定
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {groq_api_key}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            return {"response": data["choices"][0]["message"]["content"]}
    except Exception as e:
        return {"response": f"通信エラーが発生しました: {str(e)}"}

@app.get("/")
async def get_index():
    return FileResponse("index.html")
