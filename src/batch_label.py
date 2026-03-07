"""Batch-label an image dataset using Llama 3.2 11B Vision via NVIDIA API.

Sends each image through the NVIDIA API, parses the structured
classification response, and saves results incrementally to a JSON file.
Already-labeled images are skipped on re-runs so the script is resumable.

Throttling strategy:
  - A configurable delay (--delay) is inserted between every API call.
  - On HTTP 429 (rate-limited) or 5xx errors the request is retried with
    exponential backoff, respecting the Retry-After header when present.
"""

import argparse
import json
import os
import sys
import time

import requests

from nemotron import (
    BASE_QUERY,
    DISCIPLINES,
    encode_media_base64,
    get_extension,
    invoke_url,
    kApiKey,
    kSupportedList,
    mime_type,
)

MAX_RETRIES = 6
INITIAL_BACKOFF = 2.0
MAX_BACKOFF = 240.0


def _classify_image(image_path: str) -> requests.Response:
    """Call the NVIDIA API for a single image and return the raw HTTP response."""
    ext = get_extension(image_path)
    base64_data = encode_media_base64(image_path)

    content = [
        {"type": "text", "text": BASE_QUERY},
        {
            "type": "image_url",
            "image_url": {
                "url": f"data:{mime_type(ext)};base64,{base64_data}",
            },
        },
    ]

    headers = {
        "Authorization": f"Bearer {kApiKey}",
        "Accept": "application/json",
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
        "stream": False,
    }

    return requests.post(invoke_url, headers=headers, json=payload, timeout=(5, 60))


def _parse_discipline(text: str | None) -> str | None:
    """Extract the discipline label from the model response.

    The prompt asks the model to reply with only the discipline name.
    We normalize and validate against the known list.
    """
    if not text:
        return None
    cleaned = text.strip().upper()
    for discipline in DISCIPLINES:
        if discipline in cleaned:
            return discipline
    return None


def _save_results(results: dict, output_path: str) -> None:
    tmp_path = output_path + ".tmp"
    with open(tmp_path, "w") as f:
        json.dump(results, f, indent=2)
    os.replace(tmp_path, output_path)


def _load_results(output_path: str) -> dict:
    if os.path.exists(output_path):
        with open(output_path) as f:
            return json.load(f)
    return {}


def _collect_images(dataset_dir: str) -> list[str]:
    images = []
    for entry in sorted(os.listdir(dataset_dir)):
        ext = get_extension(entry)
        if ext in kSupportedList:
            images.append(entry)
    return images


def run_batch(
    dataset_dir: str,
    output_path: str,
    delay: float = 1.0,
    retry_errors: bool = False,
) -> None:
    images = _collect_images(dataset_dir)
    results = _load_results(output_path)

    if retry_errors:
        error_keys = [k for k, v in results.items() if "error" in v]
        for k in error_keys:
            del results[k]
        if error_keys:
            print(f"Retrying {len(error_keys)} previously failed image(s)")
            _save_results(results, output_path)

    total = len(images)
    already_done = sum(1 for img in images if img in results)

    print(f"Dataset : {dataset_dir}")
    print(f"Output  : {output_path}")
    print(f"Images  : {total} total, {already_done} already labeled, "
          f"{total - already_done} remaining")
    print(f"Delay   : {delay}s between requests")
    print()

    for idx, filename in enumerate(images, 1):
        if filename in results:
            continue

        image_path = os.path.join(dataset_dir, filename)
        print(f"[{idx}/{total}] {filename} ... ", end="", flush=True)

        backoff = INITIAL_BACKOFF
        last_error = None

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = _classify_image(image_path)
            except requests.RequestException as exc:
                last_error = str(exc)
                print(f"network error ({last_error}), ", end="", flush=True)
                time.sleep(min(backoff, MAX_BACKOFF))
                backoff *= 2
                continue

            if response.status_code == 200:
                break

            if response.status_code == 429 or response.status_code >= 500:
                retry_after = response.headers.get("Retry-After")
                wait = float(retry_after) if retry_after else min(backoff, MAX_BACKOFF)
                print(f"HTTP {response.status_code}, retry in {wait:.0f}s ", end="", flush=True)
                time.sleep(wait)
                backoff *= 2
                continue

            last_error = f"HTTP {response.status_code}: {response.text[:200]}"
            break
        else:
            print(f"FAILED after {MAX_RETRIES} retries")
            results[filename] = {
                "error": last_error or "max retries exceeded",
                "raw_response": None,
            }
            _save_results(results, output_path)
            time.sleep(delay)
            continue

        if response.status_code != 200:
            print(f"FAILED ({last_error})")
            results[filename] = {
                "error": last_error,
                "raw_response": None,
            }
            _save_results(results, output_path)
            time.sleep(delay)
            continue

        body = response.json()
        raw_text = body["choices"][0]["message"]["content"]
        discipline = _parse_discipline(raw_text)

        results[filename] = {
            "discipline": discipline,
            "raw_response": raw_text,
        }

        if discipline:
            print(discipline)
        else:
            preview = (raw_text or "")[:60] or "<empty>"
            print(f"??? (raw: {preview})")

        _save_results(results, output_path)
        time.sleep(delay)

    labeled = sum(1 for v in results.values() if "error" not in v)
    errored = sum(1 for v in results.values() if "error" in v)
    print(f"\nDone. {labeled} labeled, {errored} errors. Results in {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Batch-label images with Llama 3.2 11B Vision via NVIDIA API",
    )
    parser.add_argument(
        "dataset_dir",
        help="Directory containing image files to label",
    )
    parser.add_argument(
        "-o", "--output",
        default="labels.json",
        help="Path to output JSON file (default: labels.json)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Seconds to wait between API calls (default: 1.0)",
    )
    parser.add_argument(
        "--retry-errors",
        action="store_true",
        help="Re-process images that previously failed with errors",
    )
    args = parser.parse_args()

    run_batch(args.dataset_dir, args.output, args.delay, args.retry_errors)


if __name__ == "__main__":
    main()
