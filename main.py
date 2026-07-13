import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from groq import Groq
from database import get_member_schedule

# FastAPIの初期化
app = FastAPI()

# Groqクライアントの初期化
# 環境変数「GROQ_API_KEY」が設定されていることを確認してください
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

class ChatRequest(BaseModel):
    message: str
    mode: str  # "rule" (規定) または "kisha" (帰社日)

def get_rules_text():
    """rules.txtから規定内容を読み込む"""
    try:
        with open("rules.txt", "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return "規定データが読み込めません。"

@app.post("/api/chat")
async def chat(request: ChatRequest):
    system_prompt = "あなたは会社の親切で正確なアシスタントです。"
    user_input = request.message
    
    # モード別の処理ロジック
    if request.mode == "kisha":
        # データベースから帰社日を検索
        results = get_member_schedule(user_input)
        
        if not results:
            return {"response": "該当するメンバーが見つかりませんでした。お名前を確認してください。"}
        
        # データを整形してAIに渡す
        context = "\n".join([f"{dept}: {date_time}" for dept, date_time in results])
        final_prompt = f"以下の帰社日情報を丁寧な日本語で伝えてください：\n{context}"
        
    else:
        # 規定に関する質問を処理
        rules = get_rules_text()
        final_prompt = f"以下の社内規定に基づいて、簡潔かつ丁寧に回答してください：\n{rules}\n\n質問：{user_input}"

    # AIによる応答生成
    try:
        completion = client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": final_prompt}
            ],
            temperature=0.3 # 規定やスケジュール回答のため、創造性を抑えて正確性を優先
        )
        return {"response": completion.choices[0].message.content}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail="AI応答生成中にエラーが発生しました。")

# 起動コマンド（開発用）: uvicorn main:app --reload
