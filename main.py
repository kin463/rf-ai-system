import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from groq import Groq
from database import get_member_schedule

app = FastAPI()

# 確保環境變數已設定
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

class ChatRequest(BaseModel):
    message: str
    mode: str 

@app.get("/")
async def root():
    return {"status": "success", "message": "RF AI System is online."}

def get_rules_text():
    try:
        with open("rules.txt", "r", encoding="utf-8") as f:
            return f.read()
    except:
        return "規定データが読み込めません。"

@app.post("/api/chat")
async def chat(request: ChatRequest):
    system_prompt = "あなたは会社の親切で正確なアシスタントです。"
    
    if request.mode == "kisha":
        results = get_member_schedule(request.message)
        if not results:
            return {"response": "該当するメンバーが見つかりませんでした。"}
        context = "\n".join([f"{dept}: {date_time}" for dept, date_time in results])
        final_prompt = f"以下の帰社日情報を丁寧な日本語で伝えてください：\n{context}"
    else:
        rules = get_rules_text()
        final_prompt = f"以下の社内規定に基づいて回答してください：\n{rules}\n\n質問：{request.message}"

    try:
        completion = client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": final_prompt}],
            temperature=0.3
        )
        return {"response": completion.choices[0].message.content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
