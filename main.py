import os
import glob
import httpx
import re
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

app = FastAPI()

# CORS設定（ブラウザからのリクエストを許可）
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
    """ディレクトリ内の全ての.txtファイルを統合して読み込む"""
    combined_text = ""
    for file_path in glob.glob("*.txt"):
        with open(file_path, "r", encoding="utf-8") as f:
            combined_text += f.read() + "\n\n"
    return combined_text

def get_relevant_sections(user_query: str, all_text: str) -> str:
    """質問に関連する段落を抽出し、AIに渡すコンテキストを作成する"""
    sections = [s.strip() for s in re.split(r'\n\s*\r?\n', all_text) if s.strip()]
    
    scored_sections = []
    for section in sections:
        score = 0
        # 人名検索とキーワード検索のスコアリング
        if any(name in section for name in ["大関", "中山", "陶山", "麻生", "宮田", "川田", "稲森", "中元", "山田", "石井", "牛澤", "戸ヶ崎", "神林", "村越", "寺岡", "山口", "泉谷", "小栗", "山下", "濱田", "金", "山崎", "宮崎", "福島", "藤岡", "竹本", "矢野", "立原", "茶円", "渡", "山本", "小林", "高橋", "神吉", "河村"]):
            if any(name in user_query for name in ["大関", "中山", "陶山", "麻生", "宮田", "川田", "稲森", "中元", "山田", "石井", "牛澤", "戸ヶ崎", "神林", "村越", "寺岡", "山口", "泉谷", "小栗", "山下", "濱田", "金", "山崎", "宮崎", "福島", "藤岡", "竹本", "矢野", "立原", "茶円", "渡", "山本", "小林", "高橋", "神吉", "河村"]):
                score += 500
        
        # 一般キーワードのスコア加算
        keywords = ["帰社日", "連絡", "寝坊", "遅刻", "勤怠", "有給", "チーム", "勉強会"]
        for kw in keywords:
            if kw in user_query and kw in section:
                score += 100
        
        if score > 0:
            scored_sections.append((score, section))
            
    scored_sections.sort(key=lambda x: x[0], reverse=True)
    return "\n\n".join([s[1] for s in scored_sections[:3]])

@app.post("/api/chat")
async def chat(request: ChatRequest):
    if not GROQ_API_KEY:
        return {"response": "システムエラー：APIキーが設定されていません。"}
    
    # 知識ベースの読み込みと検索
    full_content = get_all_manual_content()
    relevant_context = get_relevant_sections(request.message, full_content)
    context_text = relevant_context if relevant_context else full_content[:1500]
    
    prompt = f"""あなたはR&F株式会社の社員専用AIアシスタントです。
以下の【社内資料】のみを根拠にして、質問に丁寧な日本語で回答してください。
資料に記載がない場合は「マニュアルに記載がないため回答できません」と正直に伝えてください。

【社内資料】
{context_text}

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
        try:
            response = await client.post(url, json=payload, headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"})
            data = response.json()
            return {"response": data["choices"][0]["message"]["content"]}
        except Exception as e:
            return {"response": f"通信エラーが発生しました: {str(e)}"}

@app.get("/")
async def get_index():
    return FileResponse("index.html")
