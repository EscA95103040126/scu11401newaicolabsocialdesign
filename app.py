from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import google.generativeai as genai
import requests
from dotenv import load_dotenv
import os
import math  # 用來計算總頁數

# 載入環境變數
load_dotenv()

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
NAVER_CLIENT_ID = os.getenv('NAVER_CLIENT_ID')
NAVER_CLIENT_SECRET = os.getenv('NAVER_CLIENT_SECRET')

# 設定 Gemini
genai.configure(api_key=GEMINI_API_KEY)
# 請確認你的 API Key 支援的模型名稱 (如 'gemini-1.5-flash' 或 'gemini-pro')
model = genai.GenerativeModel('gemini-1.5-flash') 

app = FastAPI()

# 設定靜態檔案與模板目錄
# 請確保你的專案結構中有 static 和 templates 資料夾
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

import re

def translate_to_korean(text):
    """
    終極版：結合「超級字典」與「AI 翻譯」的混合模式。
    優先查字典，查不到才問 AI，並具備中文防呆機制。
    """
    
    # === 1. 超級字典 (涵蓋 90% 常見搜尋需求) ===
    # 這裡列出了台灣人最常搜的韓國關鍵字 -> 對應的精準韓文
    corrections = {
        # --- 熱門地名 (Cities & Areas) ---
        "首爾": "서울",
        "釜山": "부산",
        "大邱": "대구",
        "濟州": "제주",
        "濟州島": "제주도",
        "仁川": "인천",
        "弘大": "홍대",
        "明洞": "명동",
        "江南": "강남",
        "東大門": "동대문",
        "南大門": "남대문",
        "梨泰院": "이태원",
        "聖水": "성수",
        "聖水洞": "성수동",
        "漢南洞": "한남동",
        "延南洞": "연남동",
        "益善洞": "익선동",
        "汝矣島": "여의도",
        "蠶室": "잠실",
        "鐘路": "종로",
        "乙支路": "을지로",

        # --- 必去景點 (Landmarks) ---
        "景福宮": "경복궁",
        "北村": "북촌",
        "三清洞": "삼청동",
        "南山": "남산",
        "首爾塔": "N서울타워",
        "樂天世界": "롯데월드",
        "愛寶樂園": "에버랜드",
        "漢江": "한강",
        "清溪川": "청계천",
        "星空圖書館": "별마당 도서관",
        "廣藏市場": "광장시장",
        "通仁市場": "통인시장",
        "現代百貨": "현대백화점",

        # --- 購物與美妝 (Shopping) ---
        "化妝品": "화장품",
        "彩妝": "화장품",
        "藥妝": "올리브영",      # 搜藥妝通常是找 Olive Young
        "美妝": "화장품",
        "必買": "쇼핑리스트",    # 必買 -> Shopping List
        "戰利品": "쇼핑 하울",   # Haul
        "伴手禮": "기념품",
        "超市": "마트",
        "便利商店": "편의점",
        "大創": "다이소",
        "免稅店": "면세점",
        "衣服": "옷",
        "鞋子": "신발",
        "包包": "가방",

        # --- 美食與食物 (Food) ---
        "美食": "맛집",          # 最重要的關鍵字
        "好吃": "맛집",
        "餐廳": "식당",
        "咖啡": "카페",
        "咖啡廳": "카페",
        "甜點": "디저트",
        "下午茶": "카페",
        "烤肉": "고기집",
        "五花肉": "삼겹살",
        "炸雞": "치킨",
        "韓牛": "한우",
        "部隊鍋": "부대찌개",
        "年糕": "떡볶이",
        "紫菜包飯": "김밥",
        "豬腳": "족발",
        "蔘雞湯": "삼계탕",
        "冷麵": "냉면",

        # --- 交通與住宿 (Transport & Stay) ---
        "地鐵": "지하철",
        "公車": "버스",
        "計程車": "택시",
        "機場": "공항",
        "飯店": "호텔",
        "住宿": "숙소",
        "民宿": "게스트하우스",
        
        # --- 其他 (Others) ---
        "天氣": "날씨",
        "匯率": "환율",
        "翻譯": "번역",
        "地圖": "지도"
    }

    # === 2. 字典匹配邏輯 ===
    # 策略 A: 完全匹配 (使用者只輸入 "首爾")
    if text in corrections:
        print(f"字典直接命中：'{text}' -> '{corrections[text]}'")
        return corrections[text]

    # 策略 B: 部分替換 (使用者輸入 "首爾天氣" -> 替換成 "서울 날씨")
    # 我們將中文詞替換成韓文詞，保留剩下的部分給 AI 處理或直接回傳
    processed_text = text
    replaced = False
    for ch_key, kr_value in corrections.items():
        if ch_key in processed_text:
            processed_text = processed_text.replace(ch_key, kr_value + " ") # 加個空格分隔
            replaced = True
    
    # 如果有替換過，且剩下的沒有中文字了，就直接回傳 (省去 API 呼叫)
    if replaced and not re.search(r'[\u4e00-\u9fff]', processed_text):
        print(f"字典組合替換：'{text}' -> '{processed_text.strip()}'")
        return processed_text.strip()

    # === 3. AI 翻譯 (字典沒查到的才問 Gemini) ===
    # 如果字典替換後還有中文 (例如 "釜山旅遊")，或者完全沒替換到，就交給 AI
    prompt = (
        f"將中文搜尋詞翻譯成【韓文 Naver 搜尋關鍵字】。\n"
        f"輸入：'{processed_text}' (部分可能已是韓文)\n"
        f"規則：\n"
        f"1. 絕對禁止輸出任何漢字(中文)！只能輸出諺文(Hangul)。\n"
        f"2. 如果輸入包含地名，請給出精確的韓文地名。\n"
        f"3. 範例：'首爾 旅遊' -> '서울 여행', '化妝品' -> '화장품'\n"
    )
    
    try:
        response = model.generate_content(prompt)
        korean = response.text.strip()
        korean = korean.replace("'", "").replace('"', "").replace("\n", "")

        # === 4. 最終防呆機制 ===
        # 如果 AI 還是回傳中文 (檢查 unicode)，就用正則表達式強制刪除中文，只留韓文/英文
        if re.search(r'[\u4e00-\u9fff]', korean):
            print(f"警告：Gemini 回傳含中文 '{korean}'，啟動強制清洗...")
            # 嘗試只保留韓文和空格
            cleaned = re.sub(r'[^\uac00-\ud7a3a-zA-Z0-9\s]', '', korean).strip()
            if cleaned: 
                return cleaned
            # 如果清洗完變空的，只好回傳剛剛字典處理過的版本
            return processed_text 

        print(f"Gemini 翻譯結果：'{text}' -> '{korean}'")
        return korean

    except Exception as e:
        print("Gemini 翻譯錯誤：", str(e))
        return processed_text # 發生錯誤時，回傳字典處理過的文字

def naver_search(query, page=1, display=10):
    """
    呼叫 Naver Blog Search API，支援分頁
    """
    # Naver API 的 start 參數是從 1 開始計算
    start = (page - 1) * display + 1
    
    url = "https://openapi.naver.com/v1/search/blog.json"
    headers = {
        "X-Naver-Client-Id": NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET
    }
    # sort='sim' 代表按關聯度排序，這樣才會搜到最相關的內容
    params = {"query": query, "display": display, "start": start, "sort": "sim"}
    
    print(f"呼叫 Naver API，關鍵字：{query}，頁碼：{page}，start：{start}")
    
    try:
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code == 200:
            data = response.json()
            results = []
            for item in data.get('items', []):
                results.append({
                    "title": item['title'],
                    "description": item['description'],
                    "link": item['link']
                })
            
            total = data.get('total', 0)  # Naver 總結果數
            
            # 計算真實總頁數
            real_total_pages = math.ceil(total / display)
            
            # 強制鎖定最多顯示 3 頁 (即最多抓取 30 筆資料)
            total_pages = min(real_total_pages, 3)
            
            return results, total, total_pages
        else:
            print("Naver API 錯誤狀態碼：", response.status_code)
            return [], 0, 1
            
    except Exception as e:
        print("Naver 請求發生錯誤：", str(e))
        return [], 0, 1

@app.get("/", response_class=HTMLResponse)
async def search_form(request: Request):
    """
    首頁
    """
    return templates.TemplateResponse("index.html", {
        "request": request, 
        "results": [], 
        "page": 1, 
        "total_pages": 1
    })

@app.post("/", response_class=HTMLResponse)
@app.get("/search", response_class=HTMLResponse)
async def search(request: Request, query: str = Form(None), page: int = 1):
    """
    搜尋處理：包含 POST (表單送出) 與 GET (分頁連結)
    """
    # 1. 取得搜尋關鍵字
    if query is None:
        query = request.query_params.get("query", "")

    if not query:
        return templates.TemplateResponse("index.html", {
            "request": request, 
            "results": [], 
            "page": 1, 
            "total_pages": 1
        })

    print(f"使用者輸入：{query}，請求第 {page} 頁")
    
    # 2. 翻譯關鍵字 (中文 -> 韓文，使用增強版 Prompt)
    korean_query = translate_to_korean(query)
    
    # 3. 搜尋 Naver
    naver_results, total, total_pages = naver_search(korean_query, page)
    
    # 4. 使用 Gemini 進行摘要翻譯
    summaries = []
    for result in naver_results:
        # Prompt：要求 Gemini 翻譯並摘要
        prompt = (
            f"將以下韓文內容翻譯成繁體中文，並簡短摘要成 2-3 句，重點在於資訊傳遞：\n"
            f"標題: {result['title']}\n"
            f"描述: {result['description']}"
        )
        try:
            response = model.generate_content(prompt)
            translated_summary = response.text
        except Exception as e:
            print(f"Gemini 摘要錯誤 (連結: {result['link']})：", str(e))
            translated_summary = result['description']
        
        summaries.append({
            "title": result['title'],
            "summary": translated_summary,
            "link": result['link']
        })
    
    # 5. 回傳結果
    return templates.TemplateResponse("index.html", {
        "request": request,
        "results": summaries,
        "original_query": query,  # 回傳中文原字
        "korean_query": korean_query, # 回傳翻譯後的韓文
        "page": page,
        "total_pages": total_pages
    })