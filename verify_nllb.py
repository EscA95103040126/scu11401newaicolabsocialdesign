
import sys
import os
import asyncio
from dotenv import load_dotenv

# Load env
load_dotenv()

print("Importing app to trigger model load...")
try:
    # Notice: we import translate_to_korean which is now async
    # And we need to init models manually for script
    from services.translator import translate_to_korean, init_models, nllb_translator
    # Load models
    init_models(os.getenv("GEMINI_API_KEY"))
    # Re-import to get the initialized object if needed (or just access the module variable if we imported module)
    # Since we imported nllb_translator name, it might be None if we imported before init?
    # Actually, "from module import var" imports the value at that time. 
    # Better to import the module.
    import services.translator as translator_service
    print("App services imported successfully.")
except ImportError as e:
    print(f"Import failed: {e}")
    sys.exit(1)

async def run_tests():
    # Check updated module variable
    if translator_service.nllb_translator:
        print("✅ NLLB Translator is loaded.")
        
        test_cases = [
            "我想吃烤肉",
            "機票", # Should be dictionary
            "Olive Young", # Should be dictionary (regex check)
            "IVE在哪裡", # Should match IVE
            "明天天氣如何"
        ]
        
        for text in test_cases:
            print(f"--- Testing: {text} ---")
            # Call async function
            result = await translate_to_korean(text)
            print(f"Result: {result}")
            
        print("Verification complete.")
    else:
        print("❌ NLLB Translator NOT loaded.")

if __name__ == "__main__":
    asyncio.run(run_tests())
