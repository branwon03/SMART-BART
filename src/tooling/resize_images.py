"""Batch-resize images in a dataset directory.

For each image, computes two possible scale factors:
  1. 80% of the original dimensions
  2. Fitting the longest side to 1024px
and applies whichever produces the smaller result.

Resized images are written to an output directory (default: <dataset>_resized)
so the originals are preserved.
"""

import argparse
import sys
from pathlib import Path

from PIL import Image

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
SCALE_FACTOR = 0.80
MAX_LONGEST_SIDE = 1024


def _target_size(width: int, height: int) -> tuple[int, int]:
    longest = max(width, height)

    scale_pct = SCALE_FACTOR
    scale_fit = MAX_LONGEST_SIDE / longest if longest > MAX_LONGEST_SIDE else 1.0

    scale = min(scale_pct, scale_fit)

    new_w = max(1, round(width * scale))
    new_h = max(1, round(height * scale))
    return new_w, new_h


def resize_dataset(dataset_dir: str, output_dir: str | None = None) -> None:
    dataset_path = Path(dataset_dir)
    if not dataset_path.is_dir():
        sys.exit(f"Dataset directory not found: {dataset_dir}")

    if output_dir is None:
        output_path = dataset_path.parent / (dataset_path.name + "_resized")
    else:
        output_path = Path(output_dir)

    output_path.mkdir(parents=True, exist_ok=True)

    images = sorted(
        f for f in dataset_path.iterdir()
        if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS
    )

    if not images:
        sys.exit(f"No images found in {dataset_dir}")

    print(f"Dataset : {dataset_path}")
    print(f"Output  : {output_path}")
    print(f"Images  : {len(images)}")
    print()

    for idx, img_path in enumerate(images, 1):
        try:
            with Image.open(img_path) as img:
                orig_w, orig_h = img.size
                new_w, new_h = _target_size(orig_w, orig_h)

                if (new_w, new_h) == (orig_w, orig_h):
                    resized = img.copy()
                else:
                    resized = img.resize((new_w, new_h), Image.LANCZOS)

                out_file = output_path / img_path.name
                resized.save(out_file, quality=85, optimize=True)

                print(
                    f"[{idx}/{len(images)}] {img_path.name}: "
                    f"{orig_w}x{orig_h} -> {new_w}x{new_h}"
                )
        except Exception as exc:
            print(f"[{idx}/{len(images)}] {img_path.name}: ERROR - {exc}")

    print(f"\nDone. Resized images saved to {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Resize images to 80% or 1024px longest side (whichever is smaller)",
    )
    parser.add_argument(
        "dataset_dir",
        help="Directory containing image files to resize",
    )
    parser.add_argument(
        "-o", "--output",
        default=None,
        help="Output directory (default: <dataset_dir>_resized)",
    )
    args = parser.parse_args()

    resize_dataset(args.dataset_dir, args.output)


if __name__ == "__main__":
    main()
