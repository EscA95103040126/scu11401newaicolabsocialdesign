# 🇰🇷 韓國生活資訊搜尋引擎 (Korea Living Search Engine)

這是一個結合 **Google Gemini AI**、**NLLB-200 翻譯模型** 與 **Naver Search API** 的智慧搜尋引擎專案。

旨在解決「不懂韓文」的台灣使用者在搜尋韓國在地資訊（如餐廳、景點、生活資訊）時遇到的語言隔閡。使用者只需輸入中文，系統便會透過 **混合式翻譯引擎 (Hybrid Translation Engine)** 自動將關鍵字精準轉換為韓文，並搜尋韓國最大的入口網站 Naver，最後呈現最道地的結果。

🔗 **線上演示 (Live Demo):** [點擊這裡前往網站](https://korea-search-engine.onrender.com)

## 🚀 功能特色 (Features)

* **中文直覺輸入**：不需要輸入韓文，直接使用中文關鍵字搜尋。
* **🛡️ 混合式 AI 翻譯 (Hybrid Translation System)**：
    1. **在地化字典**：針對「弘大」、「明洞」等專有名詞進行字典優先匹配，確保準確度。
    2. **NLLB-200**：使用 Meta 的開源翻譯模型 (No Language Left Behind) 進行快速基礎翻譯。
        * *(註：因 Render 免費版資源限制，線上演示版暫時關閉此功能，僅使用 Gemini)*
    3. **Google Gemini AI**：利用 LLM 強大的語意理解能力，生成最自然的韓文搜尋語法。
* **Naver 原生搜尋**：直接串接 Naver API，獲取最道地的韓國部落格與新聞資訊。
* **AI 摘要總結**：搜尋結果過多不想看？AI 會自動閱讀標題與摘要，生成一份中文的重點懶人包。(功能開發中)
* **響應式設計**：簡潔的網頁介面，支援手機與電腦瀏覽。

## 🛠️ 技術架構 (Tech Stack)

* **Backend**: Python, FastAPI
* **Frontend**: HTML, CSS, JavaScript (Jinja2 Templates)
* **AI & Translation**: 
    * Google Gemini Pro (via `google-generativeai`)
    * Meta NLLB-200 (via `transformers`)
    * Custom Regex Dictionary
* **Search Provider**: Naver Search API
* **Deployment**: Render (Cloud Application Hosting)

## ⚠️ 使用注意事項 (Important Note)

本系統搜尋結果皆直接串接自 **韓國 Naver 搜尋引擎**，因此點擊標題後導向的網頁內容均為 **韓文原文**。

* **看不懂韓文怎麼辦？**
    建議使用瀏覽器內建的翻譯功能閱讀全文：
    * 💻 **電腦版**：在網頁上點擊「滑鼠右鍵」→ 選擇「翻譯成中文」。
    * 📱 **手機版**：點擊網址列旁的「Aa」或「翻譯」圖示進行網頁翻譯。

## ⚙️ 本地端執行 (Installation)

如果你想要在自己的電腦上執行這個專案，請按照以下步驟操作：

1.  **複製專案 (Clone the repo)**
    ```bash
    git clone https://github.com/EscA95103040126/scu11401newaicolabsocialdesign.git
    cd scu11401newaicolabsocialdesign
    ```

2.  **安裝依賴套件 (Install dependencies)**
    ```bash
    pip install -r requirements.txt
    ```
    *注意：第一次執行時會下載 NLLB-200 模型 (約 600MB-1GB)，請耐心等候。*

3.  **設定環境變數 (Environment Variables)**
    請在專案根目錄建立一個 `.env` 檔案，並填入你的 API Key：
    ```env
    GEMINI_API_KEY=你的_Google_Gemini_Key
    NAVER_CLIENT_ID=你的_Naver_Client_ID
    NAVER_CLIENT_SECRET=你的_Naver_Client_Secret
    ```

4.  **啟動伺服器 (Run the server)**
    ```bash
    uvicorn app:app --reload
    ```

5.  **開啟瀏覽器**
    前往 `http://127.0.0.1:8000` 即可看到畫面。

## 📂 專案結構 (Project Structure)

```text
├── app.py              # FastAPI 主程式邏輯 (路由與 View)
├── dictionary.py       # 自定義中韓對照字典
├── requirements.txt    # Python 套件清單
├── .env                # 環境變數設定檔 (不需上傳)
├── services/           # 核心服務模組
│   ├── naver.py        # Naver API 搜尋邏輯
│   └── translator.py   # 混合式翻譯邏輯 (NLLB + Gemini)
├── templates/
│   └── index.html      # 網頁前端介面
└── static/             # 靜態檔案 (CSS, 圖片等)
```
