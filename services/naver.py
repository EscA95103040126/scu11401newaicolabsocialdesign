
import httpx
import re
import math
import os
import logging

# Configure Logging (Can be centralized later)
logger = logging.getLogger("naver_service")
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

async def naver_search(query: str, page: int = 1, display: int = 10, search_type: str = "blog", 
                       client_id: str = None, client_secret: str = None):
    """
    Async Naver Search Service
    """
    if not client_id or not client_secret:
        logger.error("Naver Client ID or Secret is missing.")
        return [], 1

    start = (page - 1) * display + 1
    valid_types = ["blog", "news", "webkr"]
    if search_type not in valid_types:
        search_type = "blog"
        
    url = f"https://openapi.naver.com/v1/search/{search_type}.json"
    
    headers = {
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret
    }
    
    params = {"query": query, "display": display, "start": start, "sort": "sim"}
    
    logger.info(f"Searching Naver: query='{query}', type='{search_type}', page={page}")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, params=params)
            
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
            logger.error(f"Naver API Error: {response.status_code} - {response.text}")
            return [], 1
    except Exception as e:
        logger.exception(f"Naver Request Failed: {str(e)}")
        return [], 1
