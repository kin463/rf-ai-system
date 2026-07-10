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
    # ファイル読み込み
    try:
        with open("rules.txt", "r", encoding="utf-8") as f:
            full_data = f.read()
    except Exception as e:
        return {"response": f"資料ファイルが読み込めません: {str(e)}"}

    # 帰社日モードのプロンプト
    if request.mode == "kisha":
        system_prompt = """あなたは帰社日検索アシスタントです。以下のルールを厳守してください。
1. 質問に含まれる社員の所属課を特定してください。
2. その課の帰社日スケジュールを漏らさず全てリスト形式で提示してください。
3. 勝手に日付を絞り込んだり、特定の日を選んだりしないでください。
4. 簡潔かつ正確に回答してください。"""
    else:
        system_prompt = """あなたは社内規定FAQアシスタントです。以下のルールを厳守してください。

1. **根拠の明確化**: 回答は提供された【資料】の内容のみを根拠としてください。
2. **意味の解釈**: 質問の言葉と資料の記載が完全に一致していなくても、意味的に等しい（例：「病気の為、休みたい」＝「病気欠勤」）と判断できる場合は、資料の内容に基づいて回答してください。
3. **推論の禁止**: ただし、資料に存在しない事実や期限を勝手に作り出すことは禁止です。
4. **回答の提供**: 該当する規定がある場合は、その条文や項目を引用して正確に回答してください。記載がない場合にのみ「記載がありません」と回答してください。"""

    prompt = f"{system_prompt}\n\n【資料】\n{full_data}\n\n【質問】\n{request.message}"
    
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.0
    }
    
    # API呼び出し
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            res = await client.post("https://api.groq.com/openai/v1/chat/completions", 
                                    json=payload, 
                                    headers={"Authorization": f"Bearer {GROQ_API_KEY}"})
            
            if res.status_code != 200:
                return {"response": "AIサーバーへの接続でエラーが発生しました。"}

            data = res.json()
            return {"response": data["choices"][0]["message"]["content"]}
        except Exception as e:
            return {"response": f"通信エラーが発生しました: {str(e)}"}
@app.get("/")
async def get_index():
    return FileResponse("index.html")
