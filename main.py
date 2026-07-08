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
    資料から社員情報を抽出する。完全一致ではなく部分一致を許容する。
    """
    if not os.path.exists(filepath): return ""
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    for line in lines:
        # [名前] を取得する
        match = re.search(r'\[(.*?)\]', line)
        if match:
            employee_name = match.group(1)
            # ユーザーの質問文の中に、資料内の社員名が「含まれている」だけでOKとする
            # これにより「山下光輝次」と入力しても「山下光輝」を特定できる
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
        # 社員名検索を実行
        context = get_employee_info(request.message, "rules.txt")
        # ヒットしなかった場合
        if not context:
            return {"response": "該当する社員情報が見つかりません。お名前を正しく入力してください。"}
    
    prompt = f"""あなたはR&F株式会社のAIアシスタントです。
    以下の情報を元に、帰社日や休暇ルールについて回答してください。
    情報が足りない場合は「該当の情報がありません」と伝えてください。

    【参照資料】
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
            return {"response": "回答を生成できませんでした。"}
        except Exception:
            return {"response": "通信エラーが発生しました。もう一度送信してください。"}

@app.get("/")
async def get_index():
    return FileResponse("index.html")
