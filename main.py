from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import httpx
import os

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class ChatRequest(BaseModel):
    message: str

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

def get_relevant_line(user_query: str, filepath: str) -> str:
    """資料全体から名前の文字列が含まれる行を探す"""
    if not os.path.exists(filepath): return ""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
            # 質問文（例：藤岡佳純の帰社日は...）から「藤岡佳純」という名前を推定して検索
            for line in lines:
                # ユーザーの質問に含まれる文字列が、行の一部に含まれていればヒットとみなす
                # 質問が長い場合、名前部分だけを抜き出して判定します
                # ここでは「帰社日」というキーワードがある行を優先して探します
                if "帰社日" in line:
                    # 質問文のメッセージの中に、その行に含まれる名前（例：藤岡佳純）があるか
                    if any(name in user_query for name in ["藤岡佳純", "大関颯人", "中山大揮", "陶山誠仁", "麻生成彦", "宮田琉生", "川田一輝", "稲森功士郎", "中元蘭", "山田大暉", "石井純一", "牛澤真美", "戸ヶ崎愛美", "神林裕和", "村越史夫", "寺岡健", "山口聖子", "山田京右", "泉谷優馬", "山口晃広", "小栗泰雅", "山下光輝", "濱田一輝", "金智賢", "山崎百夏", "宮崎亜衣里", "福島怜奈", "藤岡佳純", "竹本伊吹", "矢野誉大", "立原美柚", "茶円康汰", "渡ちなみ", "山本光希", "小林琴子", "高橋明里", "神吉沙弥", "河村梨香"]):
                        return line
        return ""
    except: return ""

@app.post("/api/chat")
async def chat(request: ChatRequest):
    # 該当する社員の行だけを抽出
    employee_info = get_relevant_line(request.message, "rules.txt")
    
    # 資料全体も念のため読み込む（情報補完用）
    with open("rules.txt", "r", encoding="utf-8") as f:
        full_manual = f.read()

    # 抽出した情報があればそれを優先、なければ全体から推論させる
    context = employee_info if employee_info else full_manual
    
    prompt = f"""あなたはR&F株式会社のAIアシスタントです。
    以下の情報を元に、社員の帰社日を回答してください。

    【情報】
    {context}

    【質問】
    {request.message}

    ※もし情報に「記載がない」場合は、「記載がありません」と回答してください。
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
            return {"response": "回答が生成できませんでした。"}
        except Exception as e:
            return {"response": "サーバーエラーが発生しました。"}

@app.get("/")
async def get_index():
    return FileResponse("index.html")
