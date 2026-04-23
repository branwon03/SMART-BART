"""
Batch upload BART station images to GCS, label with Vertex AI Gemini, append JSONL.

IAM (same project as Vertex; replace PROJECT_ID and BUCKET):

  # Your labeling/upload key (GOOGLE_APPLICATION_CREDENTIALS service account)
  gcloud storage buckets add-iam-policy-binding gs://BUCKET \\
    --member="serviceAccount:YOUR_SA@PROJECT_ID.iam.gserviceaccount.com" \\
    --role="roles/storage.objectAdmin"

  # Vertex AI must read gs:// URIs during generate_content (separate principal)
  PROJECT_NUMBER=$(gcloud projects describe PROJECT_ID --format='value(projectNumber)')
  gcloud storage buckets add-iam-policy-binding gs://BUCKET \\
    --member="serviceAccount:service-${PROJECT_NUMBER}@gcp-sa-aiplatform.iam.gserviceaccount.com" \\
    --role="roles/storage.objectViewer"
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from pathlib import Path

# ============================================================
# FILL THESE IN before running
# ============================================================
GOOGLE_APPLICATION_CREDENTIALS = "~/Documents/Github/S26-CSE-312/credentials.json"  # Path to your service account JSON key file
GOOGLE_CLOUD_PROJECT = "project-51a9be3f-d2d4-42cc-b2d"  # (e.g. "my-project-123")
GCS_BUCKET = "bart_images"  # (e.g. "bart-mvp-demo")
VERTEX_LOCATION = "us-central1"  # Vertex AI region (e.g. "us-central1")
# Model ID must match Vertex exactly; common: gemini-2.0-flash-001, gemini-1.5-flash-002
VERTEX_MODEL = "gemini-2.5-flash-lite"
# Paths (relative to repo root = this file's parent)
DATASET_DIR = Path(__file__).resolve().parent / "datasets" / "BART Stations"
REPO_DATASETS = Path(__file__).resolve().parent / "datasets"
OUTPUT_JSONL = REPO_DATASETS / "labeled_data.jsonl"
MANIFEST_TRAIN = REPO_DATASETS / "label_split_train.txt"
MANIFEST_VAL = REPO_DATASETS / "label_split_val.txt"
MANIFEST_TEST = REPO_DATASETS / "label_split_test.txt"

# Train/val/test split (deterministic via seed). Vertex labels train+val only; test unlabeled.
SPLIT_TRAIN_FRACTION = 0.7
SPLIT_VAL_FRACTION = 0.2
SPLIT_TEST_FRACTION = 0.1
LABEL_SPLIT_SEED = 42

# ~30 requests per minute
MIN_SECONDS_BETWEEN_REQUESTS = 2.0

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".JPG", ".JPEG"}

SYSTEM_TEXT = (
    "You are a BART maintenance inspector. Provide the Discipline, Condition, "
    "Priority, and Description for the observed asset."
)
USER_PROMPT_TEXT = "Analyze this infrastructure image."

GEMINI_USER_INSTRUCTION = """        
    CHOOSE ONE OF THE DISCIPLINES: 
        - FARE COLLECTION: Card scanners (they are colored black)
        - BUILDINGS: Cracked ground, Cracked floors, cracked walls, water intrusion, faded paint, vandalism, doors, missing signs, drainage issues
        - COMMS: Emergency telephones, electronic destination signs
        - ELEVATOR AND ESCALATOR: All elevator and escalator related issues (except cleaning — that is System Service)
        - GROUNDS: Landscaping, fencing, maintaining outdoor spaces, grass, trimming, irrigation systems, tree removals. Faded road paint and grounds cracks DO NOT BELONG IN THIS DISCIPLINE, they belong in BUILDINGS.
        - MECHANICAL: Fire suppression (sprinklers, extinguishers), piping (water, in/out of station), HVAC, ventilation fans
        - SYSTEM SERVICE: Garbage collection, spills on floors, bathroom cleaning
        - ELECTRICAL: Lights, light switches, electrical plugs, exposed cables, anything related to electrical systems
        - UNCLASSIFIED: If the issue cannot be confidently classified into any of the above disciplines, choose this pseudo-discipline
        
        Add text discription to positive images, so model can immidiately know what is wrong instead of guessing what is wrong
        label images as NOMINAL if the subject looks fine in the image (user context will weigh heavier in this case. If there is no user context, assign a default priority.)
        Label images as DEFECT if you can immidiately tell that the object needs service from looking at the image.

        example: an image can't capture the fact that a light is flickering, it just looks normal. NOMINAL. (user context will weigh heavier in this case. If there is no user context, assign a default priority.)
        Priority:
            - No Priority
            - Low
            - Medium
            - High
            - Critical

        Respond in exactly this format on one line:
        Discipline: <value>, Condition: <value>, Priority: <value>
        Description: <short description of the asset and any issues>"""

_split_sum = SPLIT_TRAIN_FRACTION + SPLIT_VAL_FRACTION + SPLIT_TEST_FRACTION
if abs(_split_sum - 1.0) > 1e-9:
    raise ValueError(f"SPLIT_* fractions must sum to 1.0, got {_split_sum}")


def _validate_config() -> None:
    missing = []
    if not GOOGLE_APPLICATION_CREDENTIALS.strip():
        missing.append("GOOGLE_APPLICATION_CREDENTIALS")
    if not GOOGLE_CLOUD_PROJECT.strip():
        missing.append("GOOGLE_CLOUD_PROJECT")
    if not GCS_BUCKET.strip():
        missing.append("GCS_BUCKET")
    if not VERTEX_LOCATION.strip():
        missing.append("VERTEX_LOCATION")
    if not VERTEX_MODEL.strip():
        missing.append("VERTEX_MODEL")
    if missing:
        raise SystemExit(
            "Fill in these constants at top of labeling.py: " + ", ".join(missing)
        )
    cred_path = Path(GOOGLE_APPLICATION_CREDENTIALS).expanduser()
    if not cred_path.is_file():
        raise SystemExit(f"Credentials file not found: {cred_path}")


def _apply_credentials() -> None:
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(
        Path(GOOGLE_APPLICATION_CREDENTIALS).expanduser().resolve()
    )


# Map Pillow format to Vertex-compatible MIME (must match actual object bytes in GCS).
_PIL_FORMAT_TO_MIME: dict[str, str] = {
    "JPEG": "image/jpeg",
    "JPG": "image/jpeg",
    "PNG": "image/png",
    "MPO": "image/jpeg",
    "WEBP": "image/webp",
    "GIF": "image/gif",
    "BMP": "image/bmp",
    "TIFF": "image/tiff",
    "TIF": "image/tiff",
}


def _mime_for_path(path: Path) -> str:
    s = path.suffix.lower()
    if s in (".jpg", ".jpeg"):
        return "image/jpeg"
    return "image/jpeg"


def _vertex_mime_from_file(path: Path) -> tuple[str | None, str | None]:
    """
    Open local file like Vertex will interpret bytes. Returns (mime, err).
    err set -> skip this path (corrupt, unsupported format, etc.).
    """
    try:
        from PIL import Image
    except ImportError:
        return _mime_for_path(path), None
    try:
        with Image.open(path) as im:
            im.load()
            fmt = (im.format or "").upper() or "UNKNOWN"
    except OSError as e:
        return None, f"cannot decode image: {e}"
    mime = _PIL_FORMAT_TO_MIME.get(fmt)
    if not mime:
        return None, f"unsupported for Vertex (Pillow format={fmt})"
    return mime, None


def _iter_image_files() -> list[Path]:
    if not DATASET_DIR.is_dir():
        raise SystemExit(f"Dataset directory missing: {DATASET_DIR}")
    out: list[Path] = []
    for p in sorted(DATASET_DIR.rglob("*")):
        if p.is_file() and p.suffix in IMAGE_SUFFIXES:
            out.append(p)
    return out


def _blob_name(local_path: Path) -> str:
    rel = local_path.relative_to(DATASET_DIR)
    return rel.as_posix()


def _gcs_uri(blob_name: str) -> str:
    return f"gs://{GCS_BUCKET.strip()}/{blob_name}"


def _split_for_labeling(
    files: list[Path],
) -> tuple[set[Path], list[Path], list[Path], list[Path]]:
    """
    Resolved paths to label (train+val), plus path lists for each split.
    Test split is not sent to Vertex.
    """
    resolved_list = [p.resolve() for p in files]
    n = len(resolved_list)
    if n == 0:
        return set(), [], [], []
    rng = random.Random(LABEL_SPLIT_SEED)
    order = resolved_list.copy()
    rng.shuffle(order)
    n_train = int(n * SPLIT_TRAIN_FRACTION)
    n_val = int(n * SPLIT_VAL_FRACTION)
    train_r = order[:n_train]
    val_r = order[n_train : n_train + n_val]
    test_r = order[n_train + n_val :]
    label_resolved = set(train_r) | set(val_r)
    res_to_orig = {p.resolve(): p for p in files}
    train_files = [res_to_orig[r] for r in train_r]
    val_files = [res_to_orig[r] for r in val_r]
    test_files = [res_to_orig[r] for r in test_r]
    return label_resolved, train_files, val_files, test_files


def _write_manifest(paths: list[Path], dest: Path) -> None:
    lines = sorted(_blob_name(p) for p in paths)
    dest.write_text(
        "\n".join(lines) + ("\n" if lines else ""),
        encoding="utf-8",
    )


def _load_done_uris(jsonl_path: Path) -> set[str]:
    done: set[str] = set()
    if not jsonl_path.is_file():
        return done
    with jsonl_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            for block in obj.get("contents") or []:
                if block.get("role") != "user":
                    continue
                for part in block.get("parts") or []:
                    fd = part.get("file_data") or {}
                    uri = fd.get("file_uri")
                    if uri:
                        done.add(uri)
    return done


def upload_images() -> None:
    from google.cloud import storage

    _validate_config()
    _apply_credentials()

    client = storage.Client(project=GOOGLE_CLOUD_PROJECT.strip())
    bucket = client.bucket(GCS_BUCKET.strip())
    files = _iter_image_files()
    total = len(files)
    for i, local in enumerate(files, start=1):
        name = _blob_name(local)
        blob = bucket.blob(name)
        if blob.exists():
            print(f"[{i}/{total}] skip (exists) {name}")
            continue
        print(f"[{i}/{total}] upload {name}")
        blob.upload_from_filename(str(local))
    print(f"Upload done. {total} files considered.")


def label_images() -> None:
    from google.api_core import exceptions as gapi_exc
    from google.cloud import storage
    import vertexai
    from vertexai.generative_models import GenerativeModel, Part

    _validate_config()
    _apply_credentials()

    vertexai.init(
        project=GOOGLE_CLOUD_PROJECT.strip(),
        location=VERTEX_LOCATION.strip(),
    )
    model = GenerativeModel(VERTEX_MODEL.strip(), system_instruction=SYSTEM_TEXT)
    gcs_client = storage.Client(project=GOOGLE_CLOUD_PROJECT.strip())
    gcs_bucket = gcs_client.bucket(GCS_BUCKET.strip())

    done = _load_done_uris(OUTPUT_JSONL)
    files = _iter_image_files()
    label_paths, train_files, val_files, test_files = _split_for_labeling(files)
    REPO_DATASETS.mkdir(parents=True, exist_ok=True)
    _write_manifest(train_files, MANIFEST_TRAIN)
    _write_manifest(val_files, MANIFEST_VAL)
    _write_manifest(test_files, MANIFEST_TEST)
    n_tr, n_va, n_te = len(train_files), len(val_files), len(test_files)
    print(
        f"Split: {n_tr} train, {n_va} val (both labeled), {n_te} test (no labels); "
        f"{MANIFEST_TRAIN.name}, {MANIFEST_VAL.name}, {MANIFEST_TEST.name}"
    )

    pending = [
        p
        for p in files
        if p.resolve() in label_paths and _gcs_uri(_blob_name(p)) not in done
    ]
    total = len(pending)
    skipped_missing = 0
    skipped_bad_file = 0
    skipped_vertex_image = 0
    wrote = 0

    for idx, local in enumerate(pending, start=1):
        blob_name = _blob_name(local)
        uri = _gcs_uri(blob_name)
        print(f"[{idx}/{total}] {blob_name}")

        blob = gcs_bucket.blob(blob_name)
        if not blob.exists():
            skipped_missing += 1
            print(
                f"  SKIP: object not in bucket (Vertex needs gs:// object). "
                f"Run: python labeling.py upload\n  Expected: {uri}"
            )
            continue

        mime, mime_err = _vertex_mime_from_file(local)
        if not mime or mime_err:
            skipped_bad_file += 1
            print(f"  SKIP (local decode / MIME): {mime_err or 'unknown'}")
            continue

        part_image = Part.from_uri(uri=uri, mime_type=mime)
        t0 = time.monotonic()
        try:
            response = model.generate_content(
                [
                    part_image,
                    f"{USER_PROMPT_TEXT}\n\n{GEMINI_USER_INSTRUCTION}",
                ],
            )
        except gapi_exc.InvalidArgument as e:
            err = str(e)
            if "not valid" in err or "image" in err.lower():
                skipped_vertex_image += 1
                print(
                    "  SKIP (Vertex rejected image / MIME mismatch with GCS). "
                    f"Re-upload after fixing file: {err}"
                )
                continue
            raise
        text = (response.text or "").strip()
        if not text:
            text = "Discipline: UNKNOWN, Condition: UNKNOWN, Priority: UNKNOWN\nDescription: (empty model response)"

        entry = {
            "system_instruction": {"parts": [{"text": SYSTEM_TEXT}]},
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {"text": USER_PROMPT_TEXT},
                        {"file_data": {"mime_type": mime, "file_uri": uri}},
                    ],
                },
                {"role": "model", "parts": [{"text": text}]},
            ],
        }
        with OUTPUT_JSONL.open("a", encoding="utf-8") as out:
            out.write(json.dumps(entry, ensure_ascii=False) + "\n")
        wrote += 1

        elapsed = time.monotonic() - t0
        sleep_for = max(0.0, MIN_SECONDS_BETWEEN_REQUESTS - elapsed)
        if sleep_for > 0:
            time.sleep(sleep_for)

    parts = [f"wrote {wrote} lines to {OUTPUT_JSONL}"]
    if skipped_missing:
        parts.append(f"skipped {skipped_missing} (missing in GCS)")
    if skipped_bad_file:
        parts.append(f"skipped {skipped_bad_file} (local decode/MIME)")
    if skipped_vertex_image:
        parts.append(f"skipped {skipped_vertex_image} (Vertex 400 on image)")
    print("Labeling done. " + "; ".join(parts))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="BART image upload + Gemini JSONL labeling"
    )
    parser.add_argument(
        "command",
        choices=["upload", "label", "all"],
        help="upload: GCS only; label: Gemini only; all: upload then label",
    )
    args = parser.parse_args()
    if args.command == "upload":
        upload_images()
    elif args.command == "label":
        label_images()
    else:
        upload_images()
        label_images()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
