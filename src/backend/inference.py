import argparse
import base64
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

env_path = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(dotenv_path=env_path)

invoke_url = "https://integrate.api.nvidia.com/v1/chat/completions"
stream = False

DISCIPLINES = [
    "FARE COLLECTION",
    "BUILDINGS",
    "COMMS",
    "ELEVATOR AND ESCALATOR",
    "GROUNDS",
    "MECHANICAL",
    "SYSTEM SERVICE",
    "ELECTRICAL",
    "UNCLASSIFIED",
]

PRIORITIES = [
    "LOW",
    "STANDARD",
    "HIGH",
    "CRITICAL",
]

BASE_QUERY = (
    "You are a BART maintenance issue classifier. Your goal is to output a Brief Summary, a Discipline, and a Priority Level. You will receive an image and/or text input.\n"
    "The Logic Rule: If the image appears visually NOMINAL but the user describes a functional failure, you must treat the situation as an active issue.\n"
    "If the image appears visually NOMINAL but there is NO user description, assign a LOW priority" #after MVP deadline, we can worry about more granularity in assigning defaults
    "Use the image AND/or text input to:\n"
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

kApiKey = os.getenv("NVIDIA_API_KEY")

if not kApiKey:
    raise RuntimeError(
        f"Missing NVIDIA_API_KEY. Add it to {env_path} or set it in the environment."
    )

kSupportedList = {
    "png": ["image/png", "image_url"],
    "jpg": ["image/jpeg", "image_url"],
    "jpeg": ["image/jpeg", "image_url"],
    "webp": ["image/webp", "image_url"],
}


def build_query(user_summary: str | None = None) -> str:
    """Build final prompt by appending optional user summary context."""
    if not user_summary:
        return BASE_QUERY
    return (
        f"{BASE_QUERY}\n\n"
        "User Description (treat as primary evidence for functional state when provided):\n"
        f"{user_summary.strip()}"
    )


def get_extension(filename):
    _, ext = os.path.splitext(filename)
    ext = ext[1:].lower()
    return ext


def mime_type(ext):
    return kSupportedList[ext][0]


def media_type(ext):
    return kSupportedList[ext][1]


def encode_media_base64(media_file):
    """Encode media file to base64 string."""
    with open(media_file, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def chat_with_media(
    infer_url,
    media_files,
    query: str,
    description: str | None = None,
    stream: bool = False,
    submission_id: str | None = None,
):
    assert isinstance(media_files, list), f"{media_files}"

    content: str | list[dict[str, Any]]
    if len(media_files) == 0:
        content = query
    else:
        content = [{"type": "text", "text": query}]

        for media_file in media_files:
            ext = get_extension(media_file)
            assert ext in kSupportedList, f"{media_file} format is not supported"

            print(f"Encoding {media_file} as base64...")
            base64_data = encode_media_base64(media_file)

            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:{mime_type(ext)};base64,{base64_data}"
                },
            })

    headers = {
        "Authorization": f"Bearer {kApiKey}",
        "Accept": "text/event-stream" if stream else "application/json",
    }

    payload = {
        "model": "mistralai/ministral-14b-instruct-2512",
        "messages": [
            {"role": "user", "content": content},
        ],
        "max_tokens": 2048,
        "temperature": 0.15,
        "top_p": 1.00,
        "stream": stream,
    }

    response = requests.post(infer_url, headers=headers, json=payload, stream=stream)

    if response.status_code != 200:
        print(f"API error {response.status_code}: {response.text}", file=sys.stderr)
        return None

    if stream:
        for line in response.iter_lines():
            if line:
                print(line.decode("utf-8"))
        return None

    result = response.json()
    classification = result["choices"][0]["message"]["content"]
    print(classification)

    return {
        "submission_id": submission_id,
        "discipline": classification,
        "description": description,
        "num_images": len(media_files),
        "timestamp": datetime.utcnow().isoformat(),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ministral 14B multimodal inference helper")
    parser.add_argument("media", nargs="*", help="Optional image files")
    parser.add_argument(
        "-d",
        "--description",
        default=None,
        help="Optional user summary to append to the classification prompt",
    )
    args = parser.parse_args()

    final_query = build_query(args.description)
    result = chat_with_media(
        invoke_url, list(args.media), final_query,
        description=args.description, stream=stream,
    )
    if result:
        print(result)
