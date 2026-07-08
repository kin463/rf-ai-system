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
    mode: str

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

@app.post("/api/chat")
async def chat(request: ChatRequest):
    try:
        with open("rules.txt", "r", encoding="utf-8") as f:
            full_data = f.read()
    except Exception as e:
        return {"response": f"Error: {str(e)}"}

    if request.mode == "kisha":
        system_prompt = "あなたは帰社日検索アシスタントです。ユーザーが質問した社員の所属課を特定し、その課の帰社日のみを正確に答えてください。"
    else:
        system_prompt = "あなたは社内規定FAQアシスタントです。提供された資料に基づき、休暇規定や手当などの質問に丁寧に回答してください。"

    prompt = f"{system_prompt}\n\n【資料】\n{full_data}\n\n【質問】\n{request.message}"

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
        except Exception as e:
            return {"response": f"Error: {str(e)}"}

@app.get("/")
async def get_index():
    return FileResponse("index.html")
