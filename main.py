import os
import glob
import httpx
import re
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

app = FastAPI()

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str

# APIキーの取得
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

def get_all_manual_content():
    """テキストファイルの内容を全て取得する"""
    combined_text = ""
    for file_path in glob.glob("*.txt"):
        with open(file_path, "r", encoding="utf-8") as f:
            combined_text += f.read() + "\n\n"
    return combined_text

def get_relevant_sections(user_query: str, all_text: str) -> str:
    """検索機能：構造化データに基づいて関連セクションを抽出する"""
    # セクション区切り（「[」で始まる行を新たなブロックとみなす）
    sections = [s.strip() for s in re.split(r'\n(?=\[)', all_text) if s.strip()]
    
    scored_sections = []
    
    # 社員名リスト
    names = [
        "大関颯人", "中山大揮", "陶山誠仁", "麻生成彦", "宮田琉生", "川田一喜", "稲森功士郎", "中元蘭", "山田大暉",
        "石井純一", "牛澤真美", "戸ヶ崎愛美", "神林裕和", "村越史夫", "寺岡健", "山口聖子",
        "山田京右", "泉谷優馬", "山口晃広", "小栗泰雅", "山下光輝", "濱田一輝", "金智賢",
        "山崎百夏", "宮崎亜衣里", "福島怜奈", "藤岡佳純", "竹本伊吹", "矢野誉大", "立原美柚", "茶円康汰",
        "渡ちなみ", "山本光希", "小林琴子", "高橋明里", "神吉沙弥", "河村梨香"
    ]
    
    for section in sections:
        score = 0
        
        # 1. 人名マッチング
        if any(name in user_query for name in names):
            score += 100
        
        # 2. 業務キーワードマッチング
        keywords = ["帰社日", "有給", "休暇", "寝坊", "遅刻", "提出", "期限", "手当", "所属", "メンバー"]
        for kw in keywords:
            if kw in user_query:
                score += 50
        
        # 3. 組織キーワードマッチング
        if "RandF" in user_query and "RandF" in section:
            score += 80
            
        if score > 0:
            scored_sections.append((score, section))
            
    # スコア順にソートし、上位8つを抽出
    scored_sections.sort(key=lambda x: x[0], reverse=True)
    
    selected_context = "\n\n".join([s[1] for s in scored_sections[:8]])
    return selected_context if selected_context else all_text[:4000]

@app.post("/api/chat")
async def chat(request: ChatRequest):
    if not GROQ_API_KEY:
        return {"response": "システムエラー：APIキーが設定されていません。"}
    
    context = get_relevant_sections(request.message, get_all_manual_content())
    
    # プロンプトの定義
    prompt = f"""あなたはR&F株式会社のAIアシスタントです。以下の【社内資料】の内容に基づき、正確かつ簡潔に回答してください。

    【制約事項】
    1. 帰社日とは「各課がオフィスに集まるスケジュール」を指します。
    2. 回答は簡潔にまとめ、同じ説明を繰り返さないでください。
    3. 資料に該当する情報がない場合は、憶測で答えず「記載がありません」と報告してください。
    4. 「寝坊」や「遅刻」については、緊急時の連絡ルールを最優先で参照してください。

    【社内資料】
    {context}

    【ユーザーの質問】
    {request.message}
    """
    
    url = "https://api.groq.com/openai/v1/chat/completions"
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.0
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        res = await client.post(url, json=payload, headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"})
        return {"response": res.json()["choices"][0]["message"]["content"]}

@app.get("/")
async def get_index():
    return FileResponse("index.html")
