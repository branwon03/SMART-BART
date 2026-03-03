
import argparse
import base64
import os
from pathlib import Path

import requests
from dotenv import load_dotenv

env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)

invoke_url = "https://integrate.api.nvidia.com/v1/chat/completions"
stream = False

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
    "Respond with:\n"
    "1. Discipline: <one of the above>\n"
    "2. Confidence: Score from 0 to 100\n"
    "3. Evidence: <what in the image led to this classification>"
)

kApiKey = os.getenv("API_KEY")

if not kApiKey:
    raise RuntimeError(
        f"Missing API_KEY. Add it to {env_path} or set it in the environment."
    )

# ext: {mime, media_type}
kSupportedList = {
    "png": ["image/png", "image_url"],
    "jpg": ["image/jpeg", "image_url"],
    "jpeg": ["image/jpeg", "image_url"],
    "webp": ["image/webp", "image_url"],
    "mp4": ["video/mp4", "video_url"],
    "webm": ["video/webm", "video_url"],
    "mov": ["video/mov", "video_url"]
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
    """Encode media file to base64 string"""
    with open(media_file, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

def chat_with_media(infer_url, media_files, query: str, stream: bool = False):
    assert isinstance(media_files, list), f"{media_files}"
    
    has_video = False
    
    # Build content based on whether we have media files
    if len(media_files) == 0:
        # Text-only mode
        content = query
    else:
        # Build content array with text and media
        content = [{"type": "text", "text": query}]
        
        for media_file in media_files:
            ext = get_extension(media_file)
            assert ext in kSupportedList, f"{media_file} format is not supported"
            
            media_type_key = media_type(ext)
            if media_type_key == "video_url":
                has_video = True
            
            print(f"Encoding {media_file} as base64...")
            base64_data = encode_media_base64(media_file)
            
            # Add media to content array
            media_obj = {
                "type": media_type_key,
                media_type_key: {
                    "url": f"data:{mime_type(ext)};base64,{base64_data}"
                }
            }
            content.append(media_obj)
        
        if has_video:
            assert len(media_files) == 1, "Only single video supported."
    
    headers = {
        "Authorization": f"Bearer {kApiKey}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    if stream:
        headers["Accept"] = "text/event-stream"

    # Add system message with appropriate prompt
    # Videos only support /no_think, images support both
    
    system_prompt = "/think"
    
    
    messages = [
        {
            "role": "system",
            "content": system_prompt,
        },
        {
            "role": "user",
            "content": content,
        }
    ]
    payload = {
        "max_tokens": 4096,
        "temperature": 1,
        "top_p": 1,
        "frequency_penalty": 0,
        "presence_penalty": 0,
        "messages": messages,
        "stream": stream,
        "model": "nvidia/nemotron-nano-12b-v2-vl",
    }

    response = requests.post(infer_url, headers=headers, json=payload, stream=stream)
    if stream:
        for line in response.iter_lines():
            if line:
                print(line.decode("utf-8"))
    else:
        result = response.json()
        print(result["choices"][0]["message"]["content"])

if __name__ == "__main__":
    """ Usage:
        python nemotron_cli.py                                 # Interactive CLI
        python nemotron.py --description "broken light" img.jpg
        python nemotron.py sample.mp4                          # Legacy media-only mode
    """
    parser = argparse.ArgumentParser(description="Nemotron multimodal inference helper")
    parser.add_argument("media", nargs="*", help="Optional media files (images/videos)")
    parser.add_argument(
        "-d",
        "--description",
        default=None,
        help="Optional user summary to append to the classification prompt",
    )
    args = parser.parse_args()

    final_query = build_query(args.description)
    chat_with_media(invoke_url, list(args.media), final_query, stream)
