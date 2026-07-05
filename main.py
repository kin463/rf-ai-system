from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import requests
import os

app = FastAPI()

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
    if not os.path.exists("rules.txt"):
        raise HTTPException(status_code=500, detail="rules.txt not found")
        
    with open("rules.txt", "r", encoding="utf-8") as f:
        rules_content = f.read()

    system_instruction = f"あなたはＲ＆Ｆ株式会社の厳格な社内AIアシスタントです。以下のマニュアルに基づき回答してください。\n\n{rules_content}"

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
        response.raise_for_status()
        answer = response.json()["choices"][0]["message"]["content"]
        return {"answer": answer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
