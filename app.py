from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import google.generativeai as genai
import requests
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
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-3-flash-preview') 

app = FastAPI()

# 設定靜態檔案與模板目錄
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# === 核心翻譯邏輯 (超級字典 -> Gemini 補位) ===
@lru_cache(maxsize=500) # 因為詞彙量變大，擴大快取容量
def translate_to_korean(text):
    """
    搜尋意圖轉譯器：
    1. 查「超級字典」：針對偶像、地名、專有名詞直接替換。
    2. 問 Gemini：如果字典沒涵蓋，用 AI 進行語意翻譯。
    """
    
    # --- [K-POP 本地超級資料庫] ---
    corrections = {
        # === 1. 音樂節目與大型舞台 (Music Shows & Events) ===
        "音樂銀行": "뮤직뱅크", "Music Bank": "뮤직뱅크", "音銀": "뮤직뱅크",
        "人氣歌謠": "인기가요", "Inkigayo": "인기가요",
        "音樂中心": "쇼! 음악중심", "Music Core": "쇼! 음악중심", "音中": "쇼! 음악중심",
        "M Countdown": "엠카운트다운", "MCD": "엠카운트다운", "엠카": "엠카",
        "The Show": "더쇼",
        "Show Champion": "쇼챔피언",
        
        # 年末舞台與頒獎典禮
        "歌謠大戰": "가요대전", # SBS
        "歌謠大祝祭": "가요대축제", # KBS
        "歌謠大祭典": "가요대제전", # MBC
        "MMA": "멜론뮤직어워드", "Melon": "멜론",
        "MAMA": "마마", "Mnet Asian Music Awards": "마마",
        "GDA": "골든디스크", "金唱片": "골든디스크",
        "AAA": "아시아 아티스트 어워즈",
        "TMA": "더팩트 뮤직 어워즈",
        "Waterbomb": "워터밤", "潑水節": "워터밤",
        "大學祭": "대학축제", "校慶": "대학축제",
        
        # 舞台相關用語
        "舞台": "무대", "Stage": "무대",
        "直拍": "직캠", "Fancam": "직캠",
        "全哥": "전체 직캠", "單人直拍": "개인 직캠",
        "臉拍": "페이스캠", "Facecam": "페이스캠",
        "練習室": "안무영상", "Dance Practice": "안무영상",
        "消音": "MR 제거", "MR Removed": "MR 제거",
        "安可": "앵콜", "Encore": "앵콜",
        "一位": "1위",
        "預錄": "사녹", "事前錄製": "사녹",
        "上班路": "출근길", "下班路": "퇴근길",
        "Ending妖精": "엔딩요정",

        # === 2. 女團成員 (Girl Groups) ===
        # NMIXX
        "NMIXX": "엔믹스",
        "薛侖娥": "설윤", "薛侖": "설윤", "Sullyoon": "설윤",
        "海嫄": "해원", "Haewon": "해원", "吳海嫄": "오해원",
        "Lily": "릴리", "朴珍": "릴리",
        "Bae": "배이", "真率": "배이",
        "智佑": "지우", "Jiwoo": "지우",
        "圭珍": "규진", "Kyujin": "규진",

        # NewJeans
        "NewJeans": "뉴진스", "紐吉斯": "뉴진스",
        "Minji": "민지", "玟池": "민지", "金玟池": "김민지",
        "Hanni": "하니", "哈尼": "하니",
        "Danielle": "다니엘",
        "Haerin": "해린", "海麟": "해린", "姜海麟": "강해린",
        "Hyein": "혜인", "惠仁": "혜인",

        # IVE
        "IVE": "아이브",
        "員瑛": "원영", "張員瑛": "장원영", "Wonyoung": "원영",
        "兪真": "유진", "安兪真": "안유진", "Yujin": "유진",
        "Gaeul": "가을", "秋天": "가을",
        "Rei": "레이", "直井怜": "레이",
        "Liz": "리즈", "金志垣": "리즈",
        "Leeseo": "이서", "李賢瑞": "이서",

        # aespa
        "aespa": "에스파",
        "Karina": "카리나", "柳智敏": "카리나",
        "Giselle": "지젤", "内永枝利": "지젤",
        "Winter": "윈터", "金旼炡": "윈터", "旼炡": "윈터", "冬冬": "윈터",
        "Ningning": "닝닝", "寧寧": "닝닝",

        # LE SSERAFIM
        "LE SSERAFIM": "르세라핌", "熾": "르세라핌",
        "Chaewon": "채원", "金采源": "김채원", "采源": "채원",
        "Sakura": "사쿠라", "小櫻花": "사쿠라", "宮脇咲良": "사쿠라",
        "Yunjin": "윤진", "許允眞": "허윤진", "允眞": "윤진",
        "Kazuha": "카즈하", "中村一葉": "카즈하",
        "Eunchae": "은채", "洪恩採": "홍은채", "恩採": "은채",

        # BLACKPINK
        "BLACKPINK": "블랙핑크", "BP": "블랙핑크",
        "Jisoo": "지수", "智秀": "지수",
        "Jennie": "제니",
        "Rosé": "로제", "Rose": "로제",
        "Lisa": "리사",

        # TWICE
        "TWICE": "트와이스", "兔": "트와이스",
        "Nayeon": "나연", "娜璉": "나연",
        "Jeongyeon": "정연", "定延": "정연",
        "Momo": "모모",
        "Sana": "사나",
        "Jihyo": "지효", "志效": "지효",
        "Mina": "미나",
        "Dahyun": "다현", "多賢": "다현",
        "Chaeyoung": "채영", "彩瑛": "채영",
        "Tzuyu": "쯔위", "子瑜": "쯔위",

        # KISS OF LIFE
        "KISS OF LIFE": "키스오브라이프", "KIOF": "키스오브라이프", "吻": "키스오브라이프",
        "Julie": "쥴리",
        "Natty": "나띠",
        "Belle": "벨",
        "Haneul": "하늘",

        # QWER
        "QWER": "큐더블유이알",
        "Chodan": "쵸단",
        "Magenta": "마젠타",
        "Hina": "히나",
        "Siyeon": "시연",

        # === 3. 男團成員 (Boy Groups) ===
        # SEVENTEEN
        "SEVENTEEN": "세븐틴", "SVT": "세븐틴", "次": "세븐틴",
        "S.Coups": "에스쿱스", "勝哲": "에스쿱스",
        "Jeonghan": "정한", "淨漢": "정한",
        "Joshua": "조슈아",
        "Jun": "준", "文俊輝": "준",
        "Hoshi": "호시", "權順榮": "호시",
        "Wonwoo": "원우", "圓佑": "원우",
        "Woozi": "우지", "李知勳": "우지",
        "The8": "디에잇", "徐明浩": "디에잇",
        "Mingyu": "민규", "珉奎": "민규",
        "DK": "도겸", "碩珉": "도겸",
        "Seungkwan": "승관", "勝寛": "승관",
        "Vernon": "버논",
        "Dino": "디노",

        # Stray Kids
        "Stray Kids": "스트레이 키즈", "SKZ": "스키즈", "迷": "스키즈",
        "Bang Chan": "방찬", "方燦": "방찬",
        "Lee Know": "리노",
        "Changbin": "창빈", "彰彬": "창빈",
        "Hyunjin": "현진", "鉉辰": "현진",
        "Han": "한", "知城": "한",
        "Felix": "필릭스",
        "Seungmin": "승민", "昇玟": "승민",
        "I.N": "아이엔", "精寅": "아이엔",

        # TXT
        "TXT": "투모로우바이투게더", "TOMORROW X TOGETHER": "투모로우바이투게더", "檔": "투모로우바이투게더",
        "Yeonjun": "연준", "然竣": "연준",
        "Soobin": "수빈", "秀彬": "수빈",
        "Beomgyu": "범규", "Beomgyu": "범규",
        "Taehyun": "태현", "太顯": "태현",
        "HueningKai": "휴닝카이",

        # RIIZE
        "RIIZE": "라이즈",
        "Shotaro": "쇼타로",
        "Eunseok": "은석",
        "Sungchan": "성찬",
        "Wonbin": "원빈",
        "Sohee": "소희",
        "Anton": "앤톤",

        # === 4. 一般用語補強 ===
        "小卡": "포카", "Photo Card": "포카",
        "手燈": "응원봉", "周邊": "굿즈",
        "官咖": "팬카페", "Bubble": "버블", "Weverse": "위버스",
        "簽售": "팬싸", "回歸": "컴백",
        "JYP": "제이와이피", "HYBE": "하이브", "SM": "에스엠", "YG": "와이지",
        
        # === 5. 旅遊與生活 (保留原本的) ===
        "航班": "항공권", "機票": "항공권", "飛機": "비행기표",
        "怎麼去": "가는법", "路線": "코스", "交通": "교통편",
        "地鐵": "지하철", "公車": "버스", "計程車": "택시",
        "首爾": "서울", "釜山": "부산", "弘大": "홍대", "聖水": "성수",
        "必買": "쇼핑리스트", "美食": "맛집", "好吃": "맛집",
        "藥妝": "올리브영", "Olive Young": "올리브영"
    }

    processed_text = text
    replaced = False

    # 步驟 1: 查字典替換 (忽略大小寫)
    for ch_key, kr_value in corrections.items():
        if ch_key.lower() in processed_text.lower():
            # 使用 re.sub 進行不分大小寫的替換
            processed_text = re.sub(re.escape(ch_key), kr_value + " ", processed_text, flags=re.IGNORECASE)
            replaced = True
    
    # 清理多餘空白
    processed_text = re.sub(r'\s+', ' ', processed_text).strip()

    # 如果替換後已經沒有中文字了，直接回傳
    if replaced and not re.search(r'[\u4e00-\u9fff]', processed_text):
        return processed_text

    # 步驟 2: Gemini 翻譯 (處理剩下的未知中文)
    print(f"字典未完全命中，呼叫 Gemini 翻譯: {processed_text}")
    try:
        prompt = f"""
        Role: Korean Search Keyword Generator.
        Task: Convert the user's search query (mixed Chinese/English) into natural Korean keywords for Naver/YouTube search.
        
        Input: "{processed_text}"
        
        Rules:
        1. Output ONLY the Korean keywords. No explanations.
        2. If it's a specific person/place, use their official Korean name.
        3. Keep the intent (e.g., "flight" -> "항공권" for tickets).
        """
        response = model.generate_content(prompt)
        korean_result = response.text.strip()
        cleaned = re.sub(r'[^\uac00-\ud7a3a-zA-Z0-9\s]', '', korean_result).strip()
        return cleaned if cleaned else processed_text
        
    except Exception as e:
        print(f"Gemini 翻譯失敗: {e}")
        return processed_text

# === Naver 搜尋 API ===
def naver_search(query, page=1, display=10, search_type="blog"):
    start = (page - 1) * display + 1
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
                clean_title = re.sub('<[^<]+?>', '', item['title'])
                clean_desc = re.sub('<[^<]+?>', '', item['description'])
                results.append({
                    "title": clean_title,
                    "description": clean_desc,
                    "link": item['link']
                })
            
            total = data.get('total', 0)
            real_total_pages = math.ceil(total / display)
            total_pages = min(real_total_pages, 5)
            return results, total_pages
        else:
            print(f"Naver API Error: {response.status_code}")
            return [], 1
    except Exception as e:
        print(f"Naver Request Failed: {str(e)}")
        return [], 1

# === 路由設定 ===

@app.get("/", response_class=HTMLResponse)
async def search_form(request: Request):
    return templates.TemplateResponse("index.html", {
        "request": request, 
        "results": [], 
        "page": 1, 
        "total_pages": 1,
        "search_type": "blog"
    })

@app.post("/", response_class=HTMLResponse)
@app.get("/search", response_class=HTMLResponse)
async def search(
    request: Request, 
    query: str = Form(None), 
    page: int = 1, 
    search_type: str = Form(None, alias="type") 
):
    if query is None:
        query = request.query_params.get("query", "")
    
    if search_type is None:
        search_type = request.query_params.get("type", "blog")

    if not query:
        return templates.TemplateResponse("index.html", {
            "request": request, 
            "results": [], 
            "page": 1, 
            "total_pages": 1,
            "search_type": "blog"
        })

    print(f"原始搜尋: {query} | 類型: {search_type}")
    
    # 轉譯
    korean_query = translate_to_korean(query)
    print(f"轉譯結果: {korean_query}")
    
    # 搜尋
    naver_results, total_pages = naver_search(korean_query, page, display=10, search_type=search_type)
    
    # 結果整理
    final_results = []
    for result in naver_results:
        final_results.append({
            "title": result['title'],
            "original_title": result['title'],
            "summary": result['description'],
            "link": result['link']
        })

    return templates.TemplateResponse("index.html", {
        "request": request,
        "results": final_results,
        "original_query": query,
        "korean_query": korean_query,
        "page": page,
        "total_pages": total_pages,
        "search_type": search_type
    })
