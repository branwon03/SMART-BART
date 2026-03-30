import argparse
import base64
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from google import genai
from google.genai import types
from google.oauth2 import service_account
from dotenv import load_dotenv
import requests

env_path = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(dotenv_path=env_path)

# --- VERTEX AI CONFIGURATION ---
KEY_PATH = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "credentials.json")
PROJECT_ID = "project-51a9be3f-d2d4-42cc-b2d"
LOCATION = "us-central1"

# Load Service Account
credentials = service_account.Credentials.from_service_account_file(
    KEY_PATH, 
    scopes=['https://www.googleapis.com/auth/cloud-platform']
)

client = genai.Client(
    vertexai=True, 
    project=PROJECT_ID,
    location=LOCATION, 
    credentials=credentials
)

TUNED_MODEL_ID = "projects/178919740846/locations/us-central1/endpoints/544109271923556352"

DISCIPLINES = [
    "FARE COLLECTION",
    "BUILDINGS",
    "COMMS",
    "ELEVATOR AND ESCALATOR",
    "GROUNDS",
    "MECHANICAL",
    "SYSTEM SERVICE",
    "ELECTRICAL",
    "UNCLASSIFIED"
]

PRIORITIES = [
    "LOW",
    "STANDARD",
    "HIGH",
    "CRITICAL"
]

BASE_QUERY = (
    "You are a BART maintenance issue classifier. Your goal is to output a Brief Summary, a Discipline, and a Priority Level. You will receive an image and/or text input.\n"
    "The Logic Rule: If the image appears visually NOMINAL but the user describes a functional failure, you must treat the situation as an active issue.\n"
    "If the image appears visually NOMINAL and there is NO user description, assign a LOW priority, unless the photo is of a blue phone tower or a fire sprinkler system, then it MUST be CRITICAL."
    "Reason from the image AND/or text input to:\n"
    "1) Output the name of exactly ONE discipline from the list below\n"
    "2) Output exactly ONE fitting priority level from this list: LOW, STANDARD, HIGH, CRITICAL\n"
    "3) Output a very Brief Summary of the issue.\n\n"
    
    "Possible disciplines are:\n"
    "- FARE COLLECTION: Card scanners\n"
    "- BUILDINGS: Cracked floors, cracked walls, water intrusion, faded paint, vandalism, doors, missing signs, drainage issues\n"
    "- COMMS: Emergency telephones, electronic destination signs\n"
    "- ELEVATOR AND ESCALATOR: All elevator and escalator related issues (except cleaning — that is System Service)\n"
    "- GROUNDS: Landscaping, fencing, maintaining outdoor spaces, grass, trimming, irrigation systems, tree removals\n"
    "- MECHANICAL: Fire suppression (sprinklers, extinguishers), piping (water, in/out of station), HVAC, ventilation fans\n"
    "- SYSTEM SERVICE: Garbage collection, spills on floors, bathroom cleaning\n"
    "- ELECTRICAL: Lights, light switches, electrical plugs, exposed cables, anything related to electrical systems\n"
    "- UNCLASSIFIED: If the issue cannot be confidently classified into any of the above disciplines, choose this pseudo-discipline\n\n"
)

kSupportedList = {
    "png": ["image/png", "image_url"],
    "jpg": ["image/jpeg", "image_url"],
    "jpeg": ["image/jpeg", "image_url"],
    "webp": ["image/webp", "image_url"],
}


def build_query(description: str | None = None):
    """Combines the static base query with optional user context."""
    if not description:
        return BASE_QUERY
    return f"{BASE_QUERY}\n\nUser Context: {description}"


def get_extension(filename):
    _, ext = os.path.splitext(filename)
    ext = ext[1:].lower()
    return ext



def chat_with_media(media_paths: list[Path], query: str):
    """
    Performs inference using the fine-tuned Gemini VLM with the full base query.
    """
    # Start with the full prompt (Base Query + Context)
    content_parts = [query]

    # Add the images
    for path in media_paths:
        with open(path, "rb") as f:
            image_bytes = f.read()
            content_parts.append(
                types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg")
            )

    try:
        response = client.models.generate_content(
            model=TUNED_MODEL_ID,
            config=types.GenerateContentConfig(
                temperature=0.1, # Keep it low for consistent MVP results
            ),
            contents=content_parts
        )
        
        classification = response.text.strip()
        
        return {
            "discipline": classification, 
            "num_images": len(media_paths),
            
        }
    except Exception as e:
        print(f"Inference Error: {e}")
        return None


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Gemini VLM inference helper")
    parser.add_argument("media", nargs="*", help="Optional image files")
    parser.add_argument(
        "-d",
        "--description",
        default=None,
        help="Optional user summary to append to the classification prompt",
    )
    args = parser.parse_args()

    # Convert strings from argparse to Path objects
    media_paths = [Path(m) for m in args.media]
    
    final_query = build_query(args.description)
    
    print(f"Running inference on {len(media_paths)} images...")
    
    result = chat_with_media(media_paths, final_query)
    
    if result:
        print("\n--- AI RESPONSE ---")
        print(result["discipline"])
        print("-------------------\n")
        
