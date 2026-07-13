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
4. 簡潔かつ正確に回答してください。
5. **重複対応**: 検索した姓氏が複数の課にまたがって存在する場合は、その旨を明記し、該当する全ての課の所属チームと帰社日スケジュールを提示してください。
6. **検索の厳密化**: 検索した姓氏と一致するメンバーのみを抽出してください。検索した姓を含まないメンバー（例：検索が「山田」なのに「山本」などを含めること）は、絶対に表示しないでください。"""
    else:
        system_prompt = """あなたは勤怠検索アシスタントです。以下のルールを厳守してください。

1. **正確な適用**: 回答は必ず【資料】の記載に基づき、対象や条件（「本人」限定や勤続年数など）を正確に判断してください。
2. **範囲外の排除**: 資料に記載されていない内容や、対象外の質問には「その件に関する規定はありません」と回答してください。
3. **推論の禁止**: 異なる項目の規定を勝手に組み合わせたり、勝手な解釈で新しいルールを作らないでください。
4. **根拠の提示**: 回答には必ず、どの規定に基づいているか明記してください。
5. **一般化の禁止**: 質問者が抽象的な表現を使った場合でも、資料に記載されている具体的な範囲を逸脱して適用対象を拡大しないでください。該当しない場合はその旨を伝えてください。"""
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
