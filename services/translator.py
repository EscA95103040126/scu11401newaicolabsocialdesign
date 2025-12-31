
import re
import asyncio
import logging
import google.generativeai as genai
from functools import lru_cache
# from transformers import pipeline
# Using absolute import assuming running from root, or relative if package.
# Since app.py is entry point, 'dictionary' is at root level.
# We might need to adjust python path or move dictionary.
# For now, let's assume we import from dictionary at root.
try:
    from dictionary import CORRECTIONS, DICT_REGEX
except ImportError:
    # If running inside services package context (unlikely for this simple app structure without correct path)
    # Fallback or standard import
    import sys
    sys.path.append("..")
    from dictionary import CORRECTIONS, DICT_REGEX

# Logging
logger = logging.getLogger("translator_service")
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

# === Global Models ===
# We initialize them here or via an init function.
# For simplicity in this refactor, we keep them module-level but allow lazy init if needed.
nllb_translator = None
gemini_model = None

def init_models(gemini_key: str):
    """Initialize NLLB and Gemini models"""
    global nllb_translator, gemini_model
    
    # NLLB
    # try:
    #     logger.info("Loading NLLB-200 model...")
    #     nllb_translator = pipeline("translation", model="facebook/nllb-200-distilled-600M", device=-1)
    #     logger.info("NLLB-200 loaded successfully.")
    # except Exception as e:
    #     logger.error(f"NLLB load failed: {e}")
    #     nllb_translator = None
    logger.info("NLLB-200 disabled for memory optimization on Render free tier.")
    nllb_translator = None

    # Gemini
    if gemini_key:
        masked_key = gemini_key[:4] + "***" + gemini_key[-4:] if len(gemini_key) > 8 else "***"
        logger.info(f"Attempting to configure Gemini with key: {masked_key}")
        try:
            genai.configure(api_key=gemini_key)
            # gemini_model = genai.GenerativeModel('gemini-3-flash-preview')
            # Using stable model to avoid 429 Quota errors
            gemini_model = genai.GenerativeModel('gemini-1.5-flash')
            logger.info("Gemini configured successfully with model: gemini-1.5-flash")
        except Exception as e:
            logger.error(f"Gemini config failed CRITICAL ERROR: {e}")
            gemini_model = None
    else:
        logger.warning("Gemini API Key missing. Environment variable GEMINI_API_KEY is not set or empty.")

@lru_cache(maxsize=500)
def _get_nllb_translation(text):
    """Blocking NLLB inference"""
    if not nllb_translator:
        return None
    output = nllb_translator(text, src_lang="zho_Hant", tgt_lang="kor_Hang")
    return output[0]['translation_text']

async def translate_to_korean(text):
    """
    Async Translator Pipeline
    """
    processed_text = text
    
    # [Step 1] Super Dictionary (Regex)
    # Using lambda to lookup original key for correct replacement value
    # Simplified from app.py logic
    processed_text = DICT_REGEX.sub(
        lambda m: CORRECTIONS.get(
            next((k for k in CORRECTIONS if k.lower() == m.group(0).lower()), m.group(0)), 
            m.group(0)
        ) + " ", 
        processed_text
    )
    
    # Cleanup check
    if not re.search(r'[\u4e00-\u9fff]', processed_text):
        cleaned = re.sub(r'\s+', ' ', processed_text).strip()
        logger.info(f"Dictionary Match: '{text}' -> '{cleaned}'")
        return cleaned

    # [Step 2] NLLB
    if nllb_translator:
        logger.info(f"Calling NLLB: {processed_text}")
        try:
            korean_result = await asyncio.to_thread(_get_nllb_translation, processed_text)
            if korean_result:
                logger.info(f"NLLB Result: {korean_result}")
                return korean_result
        except Exception as e:
            logger.error(f"NLLB Error: {e}")

    # [Step 3] Gemini
    if gemini_model:
        logger.info(f"Calling Gemini: {processed_text}")
        try:
            prompt = f"""
            Role: Korean Search Keyword Generator.
            Task: Convert the user's search query (mixed Chinese/English) into natural Korean keywords for Naver/YouTube search.
            Input: "{processed_text}"
            Rules: 1. Output ONLY Korean keywords.
            """
            response = await asyncio.to_thread(gemini_model.generate_content, prompt)
            korean_result = response.text.strip()
            cleaned = re.sub(r'[^\uac00-\ud7a3a-zA-Z0-9\s]', '', korean_result).strip()
            logger.info(f"Gemini Result: {cleaned}")
            return cleaned if cleaned else processed_text
        except Exception as e:
            logger.error(f"Gemini Error: {e}")
            return processed_text
            
    return processed_text

async def generate_summary(query, search_results):
    """
    Generate a summary of the search results using Gemini.
    """
    if not gemini_model or not search_results:
        return None

    try:
        # Prepare context from top 5 results
        context_text = ""
        for i, res in enumerate(search_results[:5]):
            # Handle potential different key names from Naver API vs processed dict
            title = re.sub(r'<[^>]+>', '', res.get('title', ''))
            description = re.sub(r'<[^>]+>', '', res.get('description', res.get('summary', '')))
            context_text += f"{i+1}. {title}: {description}\n"

        logger.info(f"Generating summary for query: {query}")
        
        prompt = f"""
        Role: Helpful Assistant for Korea Travel/Living Information.
        Task: Summarize the following Korean search results into Traditional Chinese (Taiwan).
        User Query: "{query}"
        Search Results:
        {context_text}
        
        Rules:
        1. Summarize the key trends, popular spots, or main opinions found in the results.
        2. Keep it concise (under 150 words).
        3. Use friendly, helpful tone.
        4. Output in Traditional Chinese.
        """
        
        response = await asyncio.to_thread(gemini_model.generate_content, prompt)
        return response.text.strip()
    except Exception as e:
        logger.error(f"Summary Generation Error: {e}")
        return None
