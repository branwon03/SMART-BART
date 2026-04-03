import os
import sys
from datetime import datetime
from pathlib import Path
from google import genai
from google.genai import types
from google.oauth2 import service_account
from dotenv import load_dotenv

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

EMBEDDING_MODEL_ID = "gemini-embedding-2-preview"

def generate_embedding(text: str, image_paths: list[Path] | None = None):
    """Generates a multimodal embedding for the issue."""
    parts = [types.Part.from_text(text=text)]
    
    if image_paths:
        for path in image_paths:
            with open(path, "rb") as f:
                parts.append(
                    types.Part.from_bytes(data=f.read(), mime_type="image/jpeg")
                )

    try:
        # Generate the embedding
        result = client.models.embed_content(
            model=EMBEDDING_MODEL_ID,
            contents=parts,
            config=types.EmbedContentConfig(task_type="CLASSIFICATION")
        )

        embeddings = result.embeddings
        if not embeddings:
            return None
        return embeddings[0].values
    except Exception as e:
        print(f"Embedding Error: {e}")
        return None
    
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
    "3) Output what the problem is about the object in 2-5 words (e.g. broken light, non-functional power socket)\n\n"
    
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


def chat_with_media(media_paths, query, description=None, submission_id=None):
    """
    Runs Gemini classification on uploaded media and returns the
    structured result needed by the submissions endpoint.

    Notes:
    - submission_id is accepted so tests / callers can pass it through
      without breaking the real function
    - description is optional and currently unused here
    """
    # 1. Prepare parts for the prompt
    content_parts = [query]

    for path in media_paths:
        with open(path, "rb") as f:
            content_parts.append(
                types.Part.from_bytes(data=f.read(), mime_type="image/jpeg")
            )

    try:
        # 2. Run Classification
        response = client.models.generate_content(
            model=TUNED_MODEL_ID,
            config=types.GenerateContentConfig(temperature=0.1),
            contents=content_parts
        )
        classification = response.text.strip()

        vector = generate_embedding(classification, media_paths)

        return {
            "submission_id": submission_id,
            "discipline": classification,
            "embedding": vector,
            "num_images": len(media_paths),
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        print(f"Inference Error: {e}")
        return None

if __name__ == "__main__":
    # 1. Hardcoded Test Configuration
    TEST_IMAGE_PATH = Path("src/backend/test_outlet.jpg")
    TEST_DESCRIPTION = "The outlet is sparking and has black char marks."
    
    # 2. Path Validation
    if not TEST_IMAGE_PATH.exists():
        print(f"ERROR: Could not find test image at: {TEST_IMAGE_PATH.absolute()}")
        print("Make sure you are running the script from the project root.")
        sys.exit(1)

    # 3. Prepare the Query
    media_paths = [TEST_IMAGE_PATH]
    final_query = build_query(TEST_DESCRIPTION)
    
    print("--- TRIGGERING HARDCODED INFERENCE TEST ---")
    print(f"Target: {TEST_IMAGE_PATH}")
    
    # 4. Execute Inference
    result = chat_with_media(media_paths, final_query)
    
    # 5. Output Results
    if result:
        print("\n" + "="*60)
        print("FINAL CLASSIFICATION:")
        print(f"  {result['discipline']}")
        
        # Access the vector from the result dictionary
        vector = result.get("embedding")
        if vector:
            print("\nVECTOR PREVIEW (First 5 values):")
            print(f"  {vector[:5]}")
            print(f"  (Total Dimensions: {len(vector)})")
        
        print("="*60 + "\n")
