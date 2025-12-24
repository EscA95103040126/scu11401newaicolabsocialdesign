# 韓國生活搜尋引擎（作業用）

## 功能
- 用戶輸入中文關鍵字（例如「仁寺洞咖啡廳」）
- Gemini AI 自動翻譯成韓文
- 用 Naver Search API 搜尋韓國本土結果（部落格、評價等）
- Gemini AI 將結果翻譯成中文並整理推薦

## 執行步驟
1. 建立虛擬環境：`python -m venv venv`
2. 啟動：`venv\Scripts\activate`
3. 安裝套件：`pip install -r requirements.txt`
4. 設定 .env 檔（API Key）
5. 執行：`uvicorn app:app --reload`
6. 開瀏覽器：http://127.0.0.1:8000

## 技術
- 後端：FastAPI
- AI：Gemini 3 Flash Preview
- 搜尋：Naver Open API

GitHub：https://github.com/EscA95103040126/korea-search-engine
