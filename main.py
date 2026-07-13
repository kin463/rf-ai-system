import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from groq import Groq
from database import get_member_schedule

app = FastAPI()

app.mount("/static", StaticFiles(directory="."), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

class ChatRequest(BaseModel):
    message: str
    mode: str

@app.get("/health")
async def health():
    return {"status": "success", "message": "RF AI System is online."}

@app.get("/")
async def root():
    html_file = os.path.join(os.path.dirname(__file__), "index.html")
    return FileResponse(html_file)

def get_rules_text():
    try:
        with open("rules.txt", "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except Exception as e:
        print("rules.txt読み込み失敗:", str(e))
        return "規定データが読み込めません。"

@app.post("/api/chat")
async def chat(request: ChatRequest):
    system_prompt = """
    必ず渡された資料に記載されている内容だけで回答してください。
    資料に記載がない事項に関しては「資料に記載がありません」と回答し、自分で推測や常識、外部知識を追加しないでください。
    回答は丁寧な日本語で簡潔にまとめてください。
    """
    try:
        if request.mode == "kisha":
            # 帰社日検索：Groqを使用せずPythonのみで文章作成、モデルの影響を受けない
            results = get_member_schedule(request.message)
            if not results:
                return {"response": "該当するメンバーが見つかりませんでした。"}
            lines = []
            for dept, date_time in results:
                lines.append(f"{dept}：{date_time}")
            content_text = "\n".join(lines)
            reply = f"ご確認いただきありがとうございます。該当者の帰社日は以下です。\n{content_text}"
            return {"response": reply}
        else:
            # 勤怠・規定質問のみGroqを使用
            rules = get_rules_text()
            final_prompt = f"""
            下記の社内規定の範囲内だけで回答してください。記載のない事項は絶対に答えないこと。
            【社内規定】
            {rules}
            【質問】
            {request.message}
            """
            completion = client.chat.completions.create(
                model="llama-3.3-8b-versatile",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": final_prompt}
                ],
                temperature=0.1,
                top_p=0.2
            )
            return {"response": completion.choices[0].message.content}
    except Exception as e:
        print("API処理エラー：", str(e))
        return {"response": f"サーバーエラー：{str(e)}"}
