import os
import httpx
import json
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class ChatRequest(BaseModel):
    message: str
    mode: str 

class FeedbackRequest(BaseModel):
    question: str
    correct_answer: str

# フィードバック保存用API
@app.post("/api/feedback")
async def save_feedback(request: FeedbackRequest):
    feedback_file = "feedback.json"
    data = []
    # 既存の記録があれば読み込む
    if os.path.exists(feedback_file):
        with open(feedback_file, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except:
                data = []
    
    # 新しいフィードバックを追加
    data.append(request.dict())
    
    # ファイルに保存
    with open(feedback_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return {"status": "success"}

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

@app.post("/api/chat")
async def chat(request: ChatRequest):
    # ファイル読み込み
    try:
        with open("rules.txt", "r", encoding="utf-8") as f:
            rules_data = f.read()
        
        # 修正履歴の読み込み
        feedback_data = ""
        if os.path.exists("feedback.json"):
            with open("feedback.json", "r", encoding="utf-8") as f:
                feedbacks = json.load(f)
                if feedbacks:
                    feedback_data = "\n【過去の修正履歴（優先的に反映すること）】\n" + json.dumps(feedbacks, ensure_ascii=False)
    except Exception as e:
        return {"response": f"ファイル読み込みエラー: {str(e)}"}

    # 帰社日モードのプロンプト
    if request.mode == "kisha":
        system_prompt = """あなたは帰社日検索アシスタントです。以下のルールを厳守してください。
1. 質問に含まれる社員の所属課を特定してください。
2. その課の帰社日スケジュールを漏らさず全てリスト形式で提示してください。
3. 勝手に日付を絞り込んだり、特定の日を選んだりしないでください。
4. 簡潔かつ正確に回答してください。
5. 【重複対応】検索した姓氏が複数の課にまたがって存在する場合は、その旨を明記し、該当する全ての課の所属チームと帰社日スケジュールを提示してください。
6. 【厳密な検索】検索した姓氏と完全一致するメンバーのみを抽出してください。検索した姓を含まないメンバーは表示しないでください。"""
    else:
        system_prompt = """あなたは勤怠検索アシスタントです。以下のルールを厳守してください。

1. 【正確な適用】回答は必ず【資料】の記載に基づき、対象や条件を正確に判断してください。
2. 【範囲外の排除】資料に記載されていない内容や、対象外の質問には「その件に関する規定はありません」と回答してください。
3. 【推論の禁止】記載内容を勝手に解釈したり、資料にない期限や範囲を勝手に作り出さないでください。
4. 【根拠の提示】回答には必ず、どの規定に基づいているか明記してください。
5. 【一般化の禁止】質問者が抽象的な表現を使った場合でも、資料に記載されている具体的な範囲を逸脱して適用対象を拡大しないでください。該当しない場合は「規定に該当する範囲ではありません」と伝えてください。
6. 【優先反映】過去の修正履歴がある場合は、その内容を優先的に反映して回答してください。"""

    # コンテキストの統合
    full_context = f"{rules_data}\n{feedback_data}"
    prompt = f"{system_prompt}\n\n【資料および履歴】\n{full_context}\n\n【質問】\n{request.message}"
    
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
