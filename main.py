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
    資料データベースから、質問に関連する社員情報の行を抽出する関数
    正規表現を使用して、資料内の [名前] を正確に特定します。
    """
    if not os.path.exists(filepath): return ""
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    for line in lines:
        # [名前] という形式を正規表現で自動検出
        match = re.search(r'\[(.*?)\]', line)
        if match:
            employee_name = match.group(1)
            # ユーザーの質問文の中に、資料内の社員名（例：「山下光輝」）が含まれていれば
            # 「山下光輝次」のような入力でも正しくヒットさせる
            if employee_name in query:
                return line
    return ""

@app.post("/api/chat")
async def chat(request: ChatRequest):
    # 「一覧」という単語が含まれていれば、全資料をコンテキストとして渡す
    if "一覧" in request.message:
        with open("rules.txt", "r", encoding="utf-8") as f:
            context = f.read()
    else:
        # 特定社員の情報を検索
        context = get_employee_info(request.message, "rules.txt")
        # 検索結果が空の場合、AIに伝える
        if not context:
            return {"response": "該当する社員情報が見つかりません。お名前を確認してください。"}
    
    # AIへの指示プロンプト
    prompt = f"""あなたはR&F株式会社のAIアシスタントです。
    提供された【資料】に基づき、ユーザーの質問に正確に答えてください。
    情報がない場合は「記載がありません」と回答してください。

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
            if "choices" in data:
                return {"response": data["choices"][0]["message"]["content"]}
            return {"response": "回答の生成に失敗しました。"}
        except Exception as e:
            return {"response": f"通信エラーが発生しました: {str(e)}"}

@app.get("/")
async def get_index():
    return FileResponse("index.html")
