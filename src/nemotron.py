
import argparse
import base64
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

env_path = Path(__file__).resolve().parent.parent / ".env"
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
    "STRUCTURES",
    "TRACK",
    "ELECTRICAL",
    "RSS",
]

BASE_QUERY = (
    "You are a transit infrastructure inspector. "
    "Classify this image into exactly ONE of the following disciplines based on what is shown:\n\n"
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
    "Respond with ONLY the discipline name, nothing else."
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
        "User-reported summary (use as secondary context after visual evidence):\n"
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


def chat_with_media(infer_url, media_files, query: str, stream: bool = False):
    assert isinstance(media_files, list), f"{media_files}"

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
        "model": "meta/llama-3.2-11b-vision-instruct",
        "messages": [
            {"role": "user", "content": content},
        ],
        "max_tokens": 512,
        "temperature": 1.00,
        "top_p": 1.00,
        "frequency_penalty": 0.00,
        "presence_penalty": 0.00,
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
    text = result["choices"][0]["message"]["content"]
    print(text)
    return text


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Llama Vision multimodal inference helper")
    parser.add_argument("media", nargs="*", help="Optional image files")
    parser.add_argument(
        "-d",
        "--description",
        default=None,
        help="Optional user summary to append to the classification prompt",
    )
    args = parser.parse_args()

    final_query = build_query(args.description)
    chat_with_media(invoke_url, list(args.media), final_query, stream)
