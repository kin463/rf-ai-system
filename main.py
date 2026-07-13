import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from groq import Groq
from database import get_member_schedule

app = FastAPI()

# 静的ファイルの設定
app.mount("/static", StaticFiles(directory="."), name="static")

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Groqの初期化
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

class ChatRequest(BaseModel):
    message: str
    mode: str

# ヘルスチェック用ルート
@app.get("/health")
async def health():
    return {"status": "success", "message": "RF AI System is online."}

# トップページでindex.htmlを表示
@app.get("/")
async def root():
    html_file = os.path.join(os.path.dirname(__file__), "index.html")
    return FileResponse(html_file)

def get_rules_text():
    try:
        with open("rules.txt", "r", encoding="utf-8") as f:
            return f.read()
    except:
        return "規定データが読み込めません。"

@app.post("/api/chat")
async def chat(request: ChatRequest):
    # AIの幻覚を禁止する厳格なSystem Prompt
    system_prompt = """
    必ず渡された資料に記載されている内容だけで回答してください。
    資料に記載がない事項に関しては「資料に記載がありません」と回答し、自分で推測や常識、外部知識を追加しないでください。
    回答は丁寧な日本語で簡潔にまとめてください。
    """

    if request.mode == "kisha":
        # Python側でrules.txtから正確に帰社日を抽出、AIにデータ作成させない
        results = get_member_schedule(request.message)
        if not results:
            return {"response": "該当するメンバーが見つかりませんでした。"}
        context = "\n".join([f"{dept}: {date_time}" for dept, date_time in results])
        final_prompt = f"""
        こちらの情報だけを利用して丁寧な日本語でまとめてください。
        情報を追加・改変しないでください。
        {context}
        """
    else:
        rules = get_rules_text()
        final_prompt = f"""
        下記の社内規定の範囲内だけで回答してください。記載のない事項は絶対に答えないこと。
        【社内規定】
        {rules}
        【質問】
        {request.message}
        """
    try:
        completion = client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": final_prompt}
            ],
            temperature=0.1,  # 値を0.1に下げてAIの独創性を抑え正確性を上げる
            top_p=0.2
        )
        return {"response": completion.choices[0].message.content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
