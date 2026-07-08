from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import httpx
import os

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class ChatRequest(BaseModel):
    message: str

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

def get_relevant_line(user_query: str, filepath: str) -> str:
    """質問に含まれる名前がある行だけを抽出する"""
    if not os.path.exists(filepath): return ""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()
            # ユーザーの質問から名前部分を特定（例：山下光輝）
            for line in lines:
                if any(name in line for name in ["山下光輝", "大関颯人", "中山大揮", "竹本伊吹", "山田京右", "泉谷優馬", "山口晃広", "小栗泰雅", "濱田一輝", "金智賢"]):
                    # 質問の中にその名前があれば、その行を返す
                    if any(name in user_query for name in ["山下光輝", "大関颯人", "中山大揮", "竹本伊吹", "山田京右", "泉谷優馬", "山口晃広", "小栗泰雅", "濱田一輝", "金智賢"]):
                        return line
        return "" # 見つからない場合
    except: return ""

@app.post("/api/chat")
async def chat(request: ChatRequest):
    # 該当する社員の行だけを抽出
    employee_info = get_relevant_line(request.message, "rules.txt")
    
    # 資料全体も念のため読み込む（情報補完用）
    with open("rules.txt", "r", encoding="utf-8") as f:
        full_manual = f.read()

    # 抽出した情報があればそれを優先、なければ全体から推論させる
    context = employee_info if employee_info else full_manual
    
    prompt = f"""あなたはR&F株式会社のAIアシスタントです。
    以下の情報を元に、社員の帰社日を回答してください。

    【情報】
    {context}

    【質問】
    {request.message}

    ※もし情報に「記載がない」場合は、「記載がありません」と回答してください。
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
            if "choices" in data:
                return {"response": data["choices"][0]["message"]["content"]}
            return {"response": "回答が生成できませんでした。"}
        except Exception as e:
            return {"response": "サーバーエラーが発生しました。"}

@app.get("/")
async def get_index():
    return FileResponse("index.html")
