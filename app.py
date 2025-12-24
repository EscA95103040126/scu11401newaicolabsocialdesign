from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import google.generativeai as genai
import requests
from dotenv import load_dotenv
import os

load_dotenv()

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
NAVER_CLIENT_ID = os.getenv('NAVER_CLIENT_ID')
NAVER_CLIENT_SECRET = os.getenv('NAVER_CLIENT_SECRET')

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-3-flash-preview')  # 你的模型

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

def translate_to_korean(text):
    prompt = f"只輸出簡短的韓文搜尋關鍵字，不要加任何解釋或額外文字。輸入：'{text}'"
    try:
        response = model.generate_content(prompt)
        korean = response.text.strip()
        print("Gemini 翻譯結果：", korean)
        return korean
    except Exception as e:
        print("Gemini 翻譯錯誤：", str(e))
        return text  # 失敗用原文

def naver_search(query, display=10):
    url = "https://openapi.naver.com/v1/search/blog.json"  # 正確端點
    headers = {
        "X-Naver-Client-Id": NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET
    }
    params = {"query": query, "display": display}
    
    print("呼叫 Naver API，關鍵字：", query)
    print("Headers：", headers)
    print("Params：", params)
    
    response = requests.get(url, headers=headers, params=params)
    
    print("Naver 回應狀態碼：", response.status_code)
    print("Naver 回應內容（前500字）：", response.text[:500])
    
    if response.status_code == 200:
        data = response.json()
        results = []
        for item in data.get('items', []):
            title = item['title']
            description = item['description']
            link = item['link']
            results.append({"title": title, "description": description, "link": link})
        print("抓到結果數：", len(results))
        return results
    else:
        print("Naver 錯誤：", response.status_code)
        return []

@app.get("/", response_class=HTMLResponse)
async def search_form(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "results": []})

@app.post("/", response_class=HTMLResponse)
async def search(request: Request, query: str = Form(...)):
    print("使用者輸入：", query)
    
    korean_query = translate_to_korean(query)
    naver_results = naver_search(korean_query)
    
    summaries = []
    for result in naver_results:
        prompt = f"將以下韓文內容翻譯成繁體中文，並簡短摘要成 2-3 句：\n標題: {result['title']}\n描述: {result['description']}"
        try:
            response = model.generate_content(prompt)
            translated_summary = response.text
        except Exception as e:
            print("Gemini 摘要錯誤：", str(e))
            translated_summary = result['description']  # 失敗時用原文
        
        summaries.append({
            "title": result['title'],
            "summary": translated_summary,
            "link": result['link']
        })
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "results": summaries,
        "original_query": query,
        "korean_query": korean_query
    })