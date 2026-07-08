import os
import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class ChatRequest(BaseModel):
    message: str

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

@app.post("/api/chat")
async def chat(request: ChatRequest):
    # 讀取整個 rules.txt 檔案內容
    try:
        with open("rules.txt", "r", encoding="utf-8") as f:
            full_context = f.read()
    except Exception:
        return {"response": "資料文件讀取失敗，請確認伺服器配置。"}
    
    # 讓 AI 根據全文來進行判斷
    prompt = f"""あなたはR&F株式会社のAIアシスタントです。
    以下の【資料】に基づき、ユーザーの質問に回答してください。
    
    【資料】
    {full_context}

    【質問】
    {request.message}
    
    もし質問に関連する情報が資料内にない場合は「該当する情報が見つかりません」と答えてください。
    また、特定の社員の帰社日を聞かれた場合は、資料内の組織構成を確認して所属課の帰社日を回答してください。
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
            data = res.json()
            return {"response": data["choices"][0]["message"]["content"]}
        except Exception:
            return {"response": "サーバーエラーが発生しました。"}

@app.get("/")
async def get_index():
    return FileResponse("index.html")
