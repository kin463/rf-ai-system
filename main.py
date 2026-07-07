import os
import glob
import httpx
import re
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

def get_all_manual_content():
    """全テキストファイルを読み込み統合"""
    combined_text = ""
    for file_path in glob.glob("*.txt"):
        with open(file_path, "r", encoding="utf-8") as f:
            combined_text += f.read() + "\n\n"
    return combined_text

def get_relevant_sections(user_query: str, all_text: str) -> str:
    """構造化検索ロジック：質問内容に応じて関連性の高いブロックを抽出"""
    # セクション分割
    sections = [s.strip() for s in re.split(r'\n(?=\[)', all_text) if s.strip()]
    
    scored_sections = []
    names = [
        "大関颯人", "中山大揮", "陶山誠仁", "麻生成彦", "宮田琉生", "川田一喜", "稲森功士郎", "中元蘭", "山田大暉",
        "石井純一", "牛澤真美", "戸ヶ崎愛美", "神林裕和", "村越史夫", "寺岡健", "山口聖子",
        "山田京右", "泉谷優馬", "山口晃広", "小栗泰雅", "山下光輝", "濱田一輝", "金智賢",
        "山崎百夏", "宮崎亜衣里", "福島怜奈", "藤岡佳純", "竹本伊吹", "矢野誉大", "立原美柚", "茶円康汰",
        "渡ちなみ", "山本光希", "小林琴子", "高橋明里", "神吉沙弥", "河村梨香"
    ]
    
    target_keywords = ["帰社日", "勉強会", "有給", "休暇", "連絡", "提出", "期限", "手当", "所属", "賞与", "寝坊", "遅刻"]
    
    for section in sections:
        score = 0
        # 人名検索（完全・部分一致）
        for name in names:
            if name in user_query: score += 100
            elif len(name) > 2 and name[:2] in user_query: score += 60
        
        # 業務キーワード検索
        if any(kw in user_query for kw in target_keywords): score += 70
        
        # 勉強会特化検索
        if "勉強会" in user_query and ("勉強会" in section or any(k in section for k in ["RPA", "SQL", "Java"])):
            score += 200
            
        if score > 0:
            scored_sections.append((score, section))
            
    scored_sections.sort(key=lambda x: x[0], reverse=True)
    # 上位10個の情報をAIに渡す
    return "\n\n".join([s[1] for s in scored_sections[:10]]) if scored_sections else all_text[:5000]

@app.post("/api/chat")
async def chat(request: ChatRequest):
    if not GROQ_API_KEY:
        return {"response": "システムエラー：APIキーが設定されていません。"}
    
    context = get_relevant_sections(request.message, get_all_manual_content())
    
    prompt = f"""あなたはR&F株式会社の専門AIアシスタントです。以下の【社内資料】の内容に基づき回答してください。

    【回答ガイドライン】
    1. 用語の揺らぎ（就労手当→資格手当等）は推察して回答してください。
    2. 資料に該当する情報がない場合は憶測せず「記載がありません」と報告してください。
    3. 同じ説明を繰り返さないでください。
    4. 勉強会、帰社日、緊急時ルールについては、社内資料の情報を優先してください。

    【社内資料】
    {context}

    【ユーザーの質問】
    {request.message}
    """
    
    url = "https://api.groq.com/openai/v1/chat/completions"
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        res = await client.post(url, json=payload, headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"})
        return {"response": res.json()["choices"][0]["message"]["content"]}

@app.get("/")
async def get_index():
    return FileResponse("index.html")
