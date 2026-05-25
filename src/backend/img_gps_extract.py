"""
Prototype CLI: extract GPS latitude/longitude from image EXIF (JPEG, HEIC/HEIF).

Uses the same PIL-based EXIF parsing as gps_lookup.py. HEIC/HEIF requires
pillow-heif (registered on import).

Source - https://stackoverflow.com/a/73267185
Posted by gamingflexer
Retrieved 2026-05-21, License - CC BY-SA 4.0
"""

from __future__ import annotations

import argparse
import os
import sys

import pillow_heif
from PIL import Image
from PIL.ExifTags import GPSTAGS, TAGS

pillow_heif.register_heif_opener()

GPS_IFD_TAG = 0x8825
HEIC_EXTENSIONS = {".heic", ".heif"}


def to_decimal(coords, ref: str) -> float:
    parts = [float(x) for x in coords]
    d, m, s = parts
    decimal = d + (m / 60.0) + (s / 3600.0)
    return -decimal if ref in ("S", "W") else decimal


def _gps_info_from_image(img: Image.Image) -> dict:
    """Read GPS tags as a dict keyed by GPSTAGS names (e.g. GPSLatitude)."""
    exif = img.getexif()
    if exif:
        gps_ifd = exif.get_ifd(GPS_IFD_TAG)
        if gps_ifd:
            return {GPSTAGS.get(tag, tag): value for tag, value in gps_ifd.items()}

    get_legacy_exif = getattr(img, "_getexif", None)
    if get_legacy_exif is None:
        return {}

    raw_exif = get_legacy_exif()
    if not raw_exif:
        return {}

    for tag, value in raw_exif.items():
        if TAGS.get(tag, tag) == "GPSInfo":
            return {GPSTAGS.get(t, t): value[t] for t in value}

    return {}


def extract_gps_coordinates(file_path: str) -> tuple[float, float]:
    """Return (latitude, longitude) in decimal degrees from image EXIF."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    ext = os.path.splitext(file_path)[1].lower()
    try:
        img = Image.open(file_path)
    except Exception as exc:
        if ext in HEIC_EXTENSIONS:
            raise ValueError(
                "Could not open HEIC/HEIF image (is pillow-heif installed?)"
            ) from exc
        raise ValueError(f"Could not open image: {exc}") from exc

    gps_info = _gps_info_from_image(img)
    if not gps_info:
        raise ValueError("No GPS data in image EXIF")

    lat = _to_decimal(gps_info["GPSLatitude"], gps_info["GPSLatitudeRef"])
    lon = _to_decimal(gps_info["GPSLongitude"], gps_info["GPSLongitudeRef"])
    return lat, lon


