from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
import os

app = FastAPI(title="R&F株式会社 社内AIアシスタント Backend")

# CORSの設定（フロントエンド HTML からの通信を許可）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🔑 Groq APIキー
GROK_API_KEY = "YOUR_GROQ_API_KEY_HERE"" 

class QueryRequest(BaseModel):
    question: str

@app.post("/api/ask")
async def ask_grok(payload: QueryRequest):
    # 1. 常に最新の社内規定（rules.txt）を読み込む
    rules_content = ""
    rules_file_path = "rules.txt"
    if os.path.exists(rules_file_path):
        with open(rules_file_path, "r", encoding="utf-8") as f:
            rules_content = f.read()
    else:
        raise HTTPException(
            status_code=500, 
            detail="rules.txt が見つかりません。main.pyと同じフォルダに配置してください。"
        )

    # 2. システムプロンプトの厳格化（Llama-3.3向けに構造を完全最適化）
    system_instruction = (
        "# あなたの役割\n"
        "あなたはＲ＆Ｆ株式会社の極めて厳格で優秀な社内AIアシスタントです。\n"
        "後半にある【社内マニュアル】のセクションに記載されている事実・データ「のみ」に基づいて回答してください。\n\n"
        
        "# 最優先遵守ルール（違反した場合はシステムエラーとなります）\n"
        "## 1. 未記載事項に対する推測の絶対禁止（総務部への誘導）\n"
        "- ユーザーから質問されたイベントや条件（例：「親友の結婚」「ペットの忌引き」「友人の葬儀」など）が、下の【社内マニュアル】の中に**直接かつ明示的に記載されていない場合**は、いかなる推測、類推、解釈も行ってはなりません。\n"
        "- 「結婚」という単語が含まれているからといって、本人の結婚規定を適用したり、関係のない「死亡休暇（忌引き）」の規定（1日など）を適用して日数を案内することは絶対に禁止します。\n"
        "- マニュアルに具体的な記載がない場合は、例外なく、文脈を問わず、必ず以下の固定テキスト【のみ】を出力して回答を終了してください。余計な解説は一切不要です。\n"
        "  固定回答：「その件については社内マニュアルに記載がないため、総務部へご確認ください」\n"
        "- 「自分の有給残り日数を確認したい」等の個人データに関する質問に対しても、マニュアルの指示通り「自分の有給日数を確認したい場合は会社に連絡すること」とだけ案内してください。\n\n"
        
        "## 2. 情報の横断的・網羅的な回答（マニュアルに記載がある場合）\n"
        "- マニュアルに正式に記載されているイベント（例：社員本人の結婚、入社5年などの勤続年数）について聞かれた場合は、複数の章や条文に分散している関連情報を漏れなくすべて組み合わせて回答してください。\n"
        "  - 例：「結婚する場合（社員本人）」：休暇日数（5日・無給）の案内に加え、慶弔見舞金（結婚祝金）の金額も必ずセットで網羅すること。\n"
        "  - 例：「入社5年（勤続年数）」：有給休暇の付与日数に関する案内に加え、結婚祝金が50,000円に昇給する点など、年資に関連するすべての規定をまとめて答えること。\n\n"
        
        "## 3. 勉強会情報の表示制限（個人情報の厳格なフィルタリング）\n"
        "- 社内勉強会に関する質問（実績や評価など）を受けた場合、開示してよい情報はマニュアルにある『講師』『期間』『実施内容（テーマ）』の3点のみです。\n"
        "- 参加者の個人名（山崎、山本、麻生、小林など）や、個人の参加態度・理解度・自主性の数値、講師による個人評価コメント（「トップ生徒」「再学習推奨」など）は、プライバシー保護のため【絶対に】回答に含めてはなりません。完全に非表示（フィルタリング）にしてください。\n\n"
        
        f"# 【Ｒ＆Ｆ株式会社 社内規定・組織情報総合マニュアル】\n{rules_content}"
    )

    # 3. Groq (groq.com) の OpenAI互換エンドポイントを設定
    groq_url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROK_API_KEY}",
        "Content-Type": "application/json"
    }
    
    groq_payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": payload.question}
        ],
        "temperature": 0.0,  # 完全に遊びをなくし、マニュアルと指示に100%縛るため 0.0 を維持
        "stream": False
    }

    try:
        response = requests.post(groq_url, json=groq_payload, headers=headers)
        response.raise_for_status()
        result = response.json()
        
        choices = result.get("choices", [])
        if choices:
            answer = choices[0].get("message", {}).get("content", "")
            return {"answer": answer}
        else:
            return {"answer": "Groq APIから有効な返答を得られませんでした。"}
            
    except requests.exceptions.RequestException as e:
        error_msg = e.response.text if e.response else str(e)
        raise HTTPException(status_code=500, detail=f"Groq APIとの通信に失敗しました: {error_msg}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)