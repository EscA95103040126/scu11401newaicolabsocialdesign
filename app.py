
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv
import os
import logging
from contextlib import asynccontextmanager

# Import Services
from services.translator import translate_to_korean, init_models
from services.naver import naver_search

# Load Environment
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")

# Logging Setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("app")

# Lifecycle Manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Load Models
    logger.info("Application Startup: Initializing Models...")
    init_models(GEMINI_API_KEY)
    yield
    # Shutdown
    logger.info("Application Shutdown")

app = FastAPI(lifespan=lifespan)

# Static & Templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# === Routes ===

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

    logger.info(f"Received Search Request: {query} [{search_type}]")
    
    # 1. Translate
    korean_query = await translate_to_korean(query)
    
    # 2. Search Naver
    naver_results, total_pages = await naver_search(
        korean_query, page, display=10, search_type=search_type,
        client_id=NAVER_CLIENT_ID, client_secret=NAVER_CLIENT_SECRET
    )
    
    # 3. Format Results
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