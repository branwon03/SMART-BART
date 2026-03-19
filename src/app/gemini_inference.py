import os
import google.generativeai as genai
from datetime import datetime
from dotenv import load_dotenv
from pathlib import Path

# Load your own key from .env (e.g., GEMINI_API_KEY=xxx)
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash')

# Reusing your teammate's exact logic categories
BASE_QUERY = (
    "You are a transit infrastructure inspector. "
    "Classify the provided image(s) into exactly ONE of the following disciplines based on what is shown:\n\n"
    "- FARE COLLECTION: Fare gates, Clipper card dispensers, add-on machines, parking pay machines, change dispensers\n"
    "- BUILDINGS: Station and parking lots only — cracked floors, cracked walls, columns, water intrusion, paint, vandalism, doors, parking lots, missing signs, drainage issues\n"
    "- COMMS: Emergency telephones, electronic destination signs, old telephones\n"
    "- ELEVATOR AND ESCALATOR: All elevator and escalator related issues (except cleaning — that is System Service)\n"
    "- GROUNDS: Landscaping, fencing, maintaining outdoor spaces, grass, trimming, irrigation systems, tree removals\n"
    "- MECHANICAL: Fire suppression (sprinklers, extinguishers), piping (water, in/out of station), HVAC, ventilation fans\n"
    "- SYSTEM SERVICE: Cleaning stations and trains, garbage collection, spills on floors, bathroom cleaning\n"
    "- STRUCTURES: Non-station structures like aerials, columns, picking up trash in tracks\n"
    "- TRACK: All track issues (except garbage in tracks — that is Structures)\n"
    "- ELECTRICAL: Lights, light switches, electrical plugs, exposed cables, anything related to electrical systems\n"
    "- RSS: Broken train, broken train seats, broken train windows, vandalism in train\n\n"
    "If multiple images are provided, consider them together as depicting the same incident.\n"
    "Respond with ONLY the discipline name, nothing else."
)

def get_extension(filename):
    return os.path.splitext(filename)[1][1:].lower()

def build_query(description: str = None):
    if not description: return BASE_QUERY
    return f"{BASE_QUERY}\n\nContext: {description}"

def chat_with_media(unused_url, media_files, query, description=None):
    # 1. Upload/Process images for Gemini
    content_parts = [query]
    for path in media_files:
        img_file = genai.upload_file(path=path)
        content_parts.append(img_file)

    # 2. Get AI Response
    response = model.generate_content(content_parts)
    
    # Clean response to ensure it's just the category (Gemini can be chatty)
    classification = response.text.strip().upper()

    return {
        "classification": classification,
        "description": description,
        "num_images": len(media_files),
        "timestamp": datetime.utcnow().isoformat(),
    }

# Constants to keep main.py happy
invoke_url = "GEMINI_MODE"
kSupportedList = ["png", "jpg", "jpeg", "webp"]