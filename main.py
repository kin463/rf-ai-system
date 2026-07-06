import os
import httpx
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

# 將規則讀取並預處理（切分成段落）
def load_and_split_manual():
    if not os.path.exists("rules.txt"):
        return []
    with open("rules.txt", "r", encoding="utf-8") as f:
        # 以雙換行當作段落分割，這是一個簡單的切分方式
        return [para for para in f.read().split("\n\n") if para.strip()]

@app.post("/api/chat")
async def chat(request: BaseModel):
    user_query = request.message
    manual_paragraphs = load_and_split_manual()
    
    # --- RAG 核心：檢索 (Retrieval) ---
    # 簡單邏輯：找出包含「關鍵字」的段落
    keywords = user_query.split()
    relevant_context = [p for p in manual_paragraphs if any(k in p for k in keywords)]
    
    # 如果找不到相關資訊，給予提示
    context_text = "\n".join(relevant_context) if relevant_context else "無相關規定"
    
    # --- RAG 核心：增強 (Augmentation) ---
    prompt = f"""請根據以下社內規定回答問題。若規定中沒有提及，請回答不知道。
    
    【相關規定內容】
    {context_text}
    
    【問題】
    {user_query}
    """
    
    # --- Groq 呼叫 ---
    GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
    url = "https://api.groq.com/openai/v1/chat/completions"
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [{"role": "user", "content": prompt}]
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload, headers={"Authorization": f"Bearer {GROQ_API_KEY}"})
        return {"response": response.json()["choices"][0]["message"]["content"]}
