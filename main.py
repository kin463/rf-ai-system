import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import requests

app = FastAPI()

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class QueryRequest(BaseModel):
    question: str

@app.get("/")
async def get_index():
    return FileResponse("index.html")

@app.post("/api/ask")
async def ask_grok(payload: QueryRequest):
    # ファイルがあるべきディレクトリ（プログラムと同じ場所）を明示
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 読み込むファイルリスト（GitHubに存在するファイル名を正確に記載）
    # もし rules.txt と rules.txt2 があるなら以下のように指定
    files_to_read = ["rules.txt", "rules.txt2"]
    
    rules_content = ""
    for filename in files_to_read:
        file_path = os.path.join(base_dir, filename)
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                rules_content += f.read() + "\n"
        else:
            return {"answer": f"エラー: {filename} が見つかりません。パス: {file_path}"}
    
    api_key = os.environ.get("GROQ_API_KEY")
    
    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": "llama-3.1-8b-instant",
                "messages": [
                    {"role": "system", "content": f"以下の社内規定に基づき、簡潔に回答せよ：\n{rules_content}"},
                    {"role": "user", "content": payload.question}
                ],
                "temperature": 0.0
            }
        )
        
        if response.status_code == 429:
            return {"answer": "AIが混雑しています。1分待ってから再送してください。"}
            
        response.raise_for_status()
        return {"answer": response.json()["choices"][0]["message"]["content"]}
    except Exception as e:
        return {"answer": f"通信エラー: {str(e)}"}
