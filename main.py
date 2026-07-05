from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import requests
import os

app = FastAPI()

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

GROK_API_KEY = os.environ.get("GROQ_API_KEY")

class QueryRequest(BaseModel):
    question: str

@app.get("/")
async def get_index():
    return FileResponse("index.html")

@app.post("/api/ask")
async def ask_grok(payload: QueryRequest):
    # rules.txtの読み込み
    try:
        with open("rules.txt", "r", encoding="utf-8") as f:
            rules_content = f.read()
    except:
        raise HTTPException(status_code=500, detail="rules.txt が見つかりません")

    system_instruction = (
        "あなたはＲ＆Ｆ株式会社の厳格な社内AIアシスタントです。"
        "以下の【社内マニュアル】のみに基づき回答してください。\n\n"
        f"【社内マニュアル】\n{rules_content}"
    )

    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": payload.question}
                ],
                "temperature": 0.0
            },
            headers={"Authorization": f"Bearer {GROK_API_KEY}"}
        )
        return {"answer": response.json()["choices"][0]["message"]["content"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000)
