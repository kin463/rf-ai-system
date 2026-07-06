# R&F 社員専用 FAQアシスタント

本システムは、R&F株式会社の就業規則、各種規定、組織構成、帰社日スケジュール等を統合管理し、AIが回答を行う社員専用FAQシステムです。

## 使用技術
- Python (FastAPI)
- Groq API (llama-3.1-8b-instant)
- Render (デプロイ環境)

## 設定方法
1. `.txt` ファイル（`manual_shain.txt`, `rules.txt`）をルートディレクトリに配置してください。
2. Render の `Environment` 設定で `GROQ_API_KEY` を設定してください。
