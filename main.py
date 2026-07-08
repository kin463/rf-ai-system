import os
import re
import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

app = FastAPI()
# すべてのオリジンからのアクセスを許可（必要に応じて制限してください）
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class ChatRequest(BaseModel):
    message: str

# APIキーを環境変数から取得
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

def get_employee_info(query: str, filepath: str) -> str:
    """
    資料データベースから、質問に関連する社員情報の行を抽出する関数
    """
    if not os.path.exists(filepath): return ""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    
    # すべての行に対して検索を実行
    lines = content.splitlines()
    for line in lines:
        # [名前] という形式を正規表現で自動検出
        match = re.search(r'\[(.*?)\]', line)
        if match:
            employee_name = match.group(1)
            # 質問文の中に社員名が含まれていれば、その行を返す
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
        # 特定社員の情報を抽出
        context = get_employee_info(request.message, "rules.txt")
        if not context:
            return {"response": "該当する社員情報が見つかりませんでした。名前が正しく記載されているか確認してください。"}
    
    # AIへの指示プロンプト
    prompt = f"""あなたはR&F株式会社のAIアシスタントです。
    提供された【資料】に基づき、ユーザーの質問に正確に答えてください。
    情報がない場合は「記載がありません」と回答してください。

    【資料】
    {context}

    【質問】
    {request.message}
    """

    # Groq APIへのリクエストデータ
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.0
    }
    
    # 非同期通信でAIに問い合わせる
    async with httpx.AsyncClient(timeout=30.0) as client:
        res = await client.post("https://api.groq.com/openai/v1/chat/completions", 
                                json=payload, 
                                headers={"Authorization": f"Bearer {GROQ_API_KEY}"})
        data = res.json()
        if "choices" in data:
            return {"response": data["choices"][0]["message"]["content"]}
        return {"response": "回答の生成に失敗しました。"}

@app.get("/")
async def get_index():
    # フロントエンド用のHTMLファイルを返す
    return FileResponse("index.html")
