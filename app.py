from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import google.generativeai as genai
import requests
import urllib.request
import urllib.parse
import json
from dotenv import load_dotenv
import os
import math
import re
from functools import lru_cache

# 載入環境變數
load_dotenv()

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
NAVER_CLIENT_ID = os.getenv('NAVER_CLIENT_ID')
NAVER_CLIENT_SECRET = os.getenv('NAVER_CLIENT_SECRET')

# 設定 Gemini
# 建議使用 gemini-1.5-flash，速度快且穩定
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash') 

app = FastAPI()

# 設定靜態檔案與模板目錄
# 請確保目錄結構中有 static 和 templates 資料夾
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# === 1. Papago 翻譯工具 ===
def translate_with_papago(text, source="zh-TW", target="ko"):
    """
    使用 Naver Papago NMT API 翻譯。
    優點：對韓文語法與專有名詞支援度比 Gemini 更好且更快。
    """
    try:
        enc_text = urllib.parse.quote(text)
        data = f"source={source}&target={target}&text=" + enc_text
        url = "https://openapi.naver.com/v1/papago/n2mt"
        
        request = urllib.request.Request(url)
        request.add_header("X-Naver-Client-Id", NAVER_CLIENT_ID)
        request.add_header("X-Naver-Client-Secret", NAVER_CLIENT_SECRET)
        
        response = urllib.request.urlopen(request, data=data.encode("utf-8"))
        rescode = response.getcode()
        
        if rescode == 200:
            response_body = response.read()
            result = json.loads(response_body.decode('utf-8'))
            translated = result['message']['result']['translatedText']
            return translated
        else:
            print(f"Papago 錯誤碼：{rescode}")
            return None # 回傳 None 讓主程式知道要用 fallback
    except Exception as e:
        print(f"Papago 呼叫失敗：{str(e)}")
        return None

# === 2. 核心翻譯邏輯 (字典 -> Papago -> Gemini) ===
@lru_cache(maxsize=100) # 加入快取，節省 API
def translate_to_korean(text):
    """
    搜尋意圖轉譯器：
    1. 先查字典 (修正語意，如：航班 -> 機票)
    2. 嘗試 Papago (精準翻譯)
    3. 失敗則用 Gemini (保底)
    """
    
    # --- 意圖修正字典 (Intent Correction) ---
    corrections = {
        # [交通類]
        "航班": "항공권",      # 航班 -> 機票
        "機票": "항공권",
        "飛機": "비행기표",
        "怎麼去": "가는법",
        "交通": "교통편",
        "高鐵": "KTX",
        
        # [熱門地名]
        "首爾": "서울", "釜山": "부산", "大邱": "대구", 
        "濟州": "제주", "弘大": "홍대", "明洞": "명동", 
        "漢南洞": "한남동", "聖水洞": "성수동", "延南洞": "연남동",
        
        # [購物/美食]
        "必買": "쇼핑리스트",
        "美食": "맛집",
        "好吃": "맛집",
        "藥妝": "올리브영",    # Olive Young
        "推薦": "추천",
        "評價": "후기",
        "菜單": "메뉴",
        
        # [追星/娛樂]
        "舞台": "직캠",        # Fancam/直拍
        "好笑": "웃긴 영상",
        "同款": "손민수"
    }

    processed_text = text
    replaced = False

    # 步驟 A: 字典替換
    for ch_key, kr_value in corrections.items():
        if ch_key in processed_text:
            processed_text = processed_text.replace(ch_key, kr_value + " ")
            replaced = True
    
    # 如果替換後已經沒有中文，直接回傳
    if replaced and not re.search(r'[\u4e00-\u9fff]', processed_text):
        return processed_text.strip()

    # 步驟 B: Papago 翻譯 (處理剩下的中文)
    papago_result = translate_with_papago(processed_text, source="zh-TW", target="ko")
    
    if papago_result:
        # 清洗：移除特殊符號，只留韓文英文數字
        cleaned = re.sub(r'[^\uac00-\ud7a3a-zA-Z0-9\s]', '', papago_result).strip()
        return cleaned

    # 步驟 C: Gemini Fallback
    print("Papago 失敗，切換至 Gemini...")
    try:
        prompt = f"將搜尋詞 '{processed_text}' 轉為韓文搜尋關鍵字。直接輸出韓文，不要解釋。"
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"Gemini 也失敗: {e}")
        return processed_text 

# === 3. Naver 搜尋 API (支援多種類型) ===
def naver_search(query, page=1, display=10, search_type="blog"):
    """
    呼叫 Naver Search API
    search_type 支援: 'blog' (部落格), 'news' (新聞), 'webkr' (網站)
    """
    start = (page - 1) * display + 1
    
    # 動態切換 API 端點，預設為 blog
    valid_types = ["blog", "news", "webkr"]
    if search_type not in valid_types:
        search_type = "blog"
        
    url = f"https://openapi.naver.com/v1/search/{search_type}.json"
    
    headers = {
        "X-Naver-Client-Id": NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET
    }
    
    params = {"query": query, "display": display, "start": start, "sort": "sim"}
    
    try:
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            data = response.json()
            results = []
            for item in data.get('items', []):
                # 移除 HTML tag
                clean_title = re.sub('<[^<]+?>', '', item['title'])
                clean_desc = re.sub('<[^<]+?>', '', item['description'])
                
                results.append({
                    "title": clean_title,
                    "description": clean_desc,
                    "link": item['link']
                })
            
            total = data.get('total', 0)
            real_total_pages = math.ceil(total / display)
            total_pages = min(real_total_pages, 5) # 限制最多顯示 5 頁
            
            return results, total_pages
        else:
            print(f"Naver API Error: {response.status_code}")
            return [], 1
            
    except Exception as e:
        print(f"Naver Request Failed: {str(e)}")
        return [], 1

# === 4. 路由設定 ===

@app.get("/", response_class=HTMLResponse)
async def search_form(request: Request):
    return templates.TemplateResponse("index.html", {
        "request": request, 
        "results": [], 
        "page": 1, 
        "total_pages": 1,
        "search_type": "blog" # 預設類型
    })

@app.post("/", response_class=HTMLResponse)
@app.get("/search", response_class=HTMLResponse)
async def search(
    request: Request, 
    query: str = Form(None), 
    page: int = 1, 
    # [關鍵修正] 使用 alias="type" 來正確接收表單中的 name="type"
    search_type: str = Form(None, alias="type") 
):
    # 1. 處理輸入參數 (支援 Query String 與 Form Data)
    if query is None:
        query = request.query_params.get("query", "")
    
    # 處理 search_type：如果是分頁(GET)請求，search_type 會是 None，要從網址參數抓
    if search_type is None:
        search_type = request.query_params.get("type", "blog")

    # 如果還是空的，回首頁
    if not query:
        return templates.TemplateResponse("index.html", {
            "request": request, 
            "results": [], 
            "page": 1, 
            "total_pages": 1,
            "search_type": "blog"
        })

    print(f"搜尋: {query} | 頁碼: {page} | 類型: {search_type}")
    
    # 2. 轉譯關鍵字
    korean_query = translate_to_korean(query)
    
    # 3. 執行搜尋 (傳入正確的 search_type)
    naver_results, total_pages = naver_search(korean_query, page, display=10, search_type=search_type)
    
    # 4. 結果翻譯 (標題與描述翻成中文)
    final_results = []
    for result in naver_results:
        # 標題翻譯
        trans_title = translate_with_papago(result['title'], source="ko", target="zh-TW")
        if not trans_title: 
            trans_title = result['title']
            
        # 描述翻譯
        trans_desc = translate_with_papago(result['description'], source="ko", target="zh-TW")
        if not trans_desc:
            trans_desc = result['description']

        final_results.append({
            "title": trans_title,
            "original_title": result['title'],
            "summary": trans_desc,
            "link": result['link']
        })

    # 5. 回傳結果與狀態
    return templates.TemplateResponse("index.html", {
        "request": request,
        "results": final_results,
        "original_query": query,
        "korean_query": korean_query,
        "page": page,
        "total_pages": total_pages,
        "search_type": search_type # 回傳類型，確保前端下拉選單位置正確
    })
