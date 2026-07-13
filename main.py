import os
import re
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
    絶対に守るルール：
    1. 渡された社内規定のテキストだけを参照して回答してください。
    2. 規定文に記載されていない事柄については、余計な文章を一切追加せず「資料に記載がありません」の一文だけを返答する。
    3. 自分の知識や一般常識、外部情報を使って推測・補足しては絶対にいけません。
    4. 条件が限定されている場合は対象範囲を勝手に広げない。
       例：本人結婚の休暇は本人のみ適用、友人の結婚は対象外と判断する。
    5. 回答は簡潔な日本語にまとめ、余分な解説文を記述しない。
    """
    try:
        if request.mode == "kisha":
            results = get_member_schedule(request.message)
            if not results:
                return {"response": "該当するメンバーが見つかりませんでした。"}
            lines = []
            for fullname, dept, date_time in results:
                lines.append(f"{fullname} {dept}：帰社日：{date_time}")
            content_text = "\n".join(lines)
            reply = f"ご確認いただきありがとうございます。該当者の帰社日は以下です。\n{content_text}"
            return {"response": reply}
        else:
            full_rules = get_rules_text()
            question = request.message.strip()

            # rules.txtをブロックごとに分割
            block_kyuka = re.search(r"\[休暇規定\]([\s\S]*?)\[慶弔見舞金\]", full_rules).group(1)
            block_keijou = re.search(r"\[慶弔見舞金\]([\s\S]*?)\[災害補償\]", full_rules).group(1)
            block_saigai = re.search(r"\[災害補償\]([\s\S]*?)\[給与・手当・評価\]", full_rules).group(1)
            block_salary = re.search(r"\[給与・手当・評価\]([\s\S]*?)\[資格取得支援\]", full_rules).group(1)
            block_kintai = re.search(r"\[勤怠・提出・連絡ルール\][\s\S]*$", full_rules).group(0)

            selected_text = ""
            # キーワードにより必要なブロックだけ選択
            if any(word in question for word in ["休暇", "有給", "結婚", "死亡", "出産", "弔慰金"]):
                selected_text += block_kyuka + block_keijou
            if any(word in question for word in ["給与", "基本給", "手当", "昇給", "災害補償"]):
                selected_text += block_saigai + block_salary
            if any(word in question for word in ["寝坊", "遅刻", "欠勤", "提出", "連絡"]):
                selected_text += block_kintai
            
            # どのカテゴリにも該当しない場合Groqを呼び出さない
            if selected_text == "":
                return {"response": "資料に記載がありません"}

            final_prompt = f"""
            社内規定の記載内容だけを使用し回答してください。記載されていない内容に対しては「資料に記載がありません」と返してください。
            【社内規定】
            {selected_text}
            【質問】
            {request.message}
            """
            completion = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": final_prompt}
                ],
                temperature=0.0,
                top_p=0.1
            )
            return {"response": completion.choices[0].message.content.strip()}
    except Exception as e:
        print("API処理エラー：", str(e))
        return {"response": f"サーバーエラー：{str(e)}"}
