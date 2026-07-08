import os
import re
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

def get_employee_info(query: str, filepath: str) -> str:
    """
    資料データベースから、質問に含まれる名前の行を柔軟に抽出する
    """
    if not os.path.exists(filepath): return ""
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    for line in lines:
        # [名前] という形式を抽出
        match = re.search(r'\[(.*?)\]', line)
        if match:
            employee_name = match.group(1)
            # ユーザーの質問文の中に、資料内の社員名が含まれていればOKとする（例：山下光輝次 -> 山下光輝が含まれる）
            if employee_name in query:
                return line
    return ""

@app.post("/api/chat")
async def chat(request: ChatRequest):
    # 「一覧」が含まれる場合は全資料を返す
    if "一覧" in request.message:
        with open("rules.txt", "r", encoding="utf-8") as f:
            context = f.read()
    else:
        # 社員名検索
        context = get_employee_info(request.message, "rules.txt")
        # 検索にヒットしなかった場合、AIに「記載がない」ことを伝えるためのフラグを立てる
        if not context:
            context = "NOT_FOUND"
    
    # プロンプトの構築
    prompt = f"""あなたはR&F株式会社のAIアシスタントです。
    提供された【資料】に基づき、ユーザーの質問に正確に答えてください。
    
    もし【資料】が「NOT_FOUND」である場合は、「該当する社員情報が見つかりません。お名前を確認してください」と回答してください。
    それ以外で情報がない場合は「記載がありません」と回答してください。

    【資料】
    {context}

    【質問】
    {request.message}
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
