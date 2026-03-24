import os
import google.generativeai as genai
from dotenv import load_dotenv
from pathlib import Path

# Try to load the .env from the app folder where you saved it
env_path = Path("src/app/.env")
load_dotenv(dotenv_path=env_path)

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("❌ Error: No API Key found in src/app/.env")
else:
    print(f"Checking key: {api_key[:10]}...")
    genai.configure(api_key=api_key)

    try:
        # Step 1: List models to see what your account is allowed to use
        print("Fetching available models...")
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                print(f"✅ Available: {m.name}")

        # Step 2: Try a simple text prompt
        model = genai.GenerativeModel('models/gemini-2.5-flash-image')
        response = model.generate_content("API check: Reply with 'Active'")
        print(f"\n🚀 SUCCESS! Gemini says: {response.text}")

    except Exception as e:
        print(f"\n❌ FAILED: {e}")
        