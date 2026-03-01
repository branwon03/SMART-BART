import argparse
import shutil
import subprocess
from pathlib import Path

from nemotron import build_query, chat_with_media, get_extension, invoke_url

IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}


def pick_image_with_dialog(start_dir: str) -> str | None:
    """
    Open a file chooser dialog and return selected image path.

    Uses zenity or kdialog when available, so the selected file is returned
    directly to the CLI without requiring users to paste a path.
    """
    if shutil.which("zenity"):
        cmd = [
            "zenity",
            "--file-selection",
            "--title=Select incident image",
            f"--filename={start_dir}/",
            "--file-filter=Images | *.png *.jpg *.jpeg *.webp",
        ]
    elif shutil.which("kdialog"):
        cmd = [
            "kdialog",
            "--getopenfilename",
            start_dir,
            "Images (*.png *.jpg *.jpeg *.webp)",
        ]
    else:
        print("No supported file picker found (install zenity or kdialog).")
        return None

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    except OSError as exc:
        print(f"Failed to launch file picker: {exc}")
        return None

    if result.returncode != 0:
        return None
    selected = result.stdout.strip()
    return selected or None


def prompt_for_image_path() -> str:
    """Prompt user for image path or choose image with file picker."""
    while True:
        print("\nImage selection:")
        print("  [B] Browse and select image")
        print("  [P] Paste image path directly")
        print("  [Q] Quit")
        choice = input("Choose an option [B/P/Q]: ").strip().lower()

        if choice == "q":
            raise KeyboardInterrupt("User cancelled image selection.")

        if choice == "b":
            start_dir = str(Path.home())
            selected_path = pick_image_with_dialog(start_dir)
            if not selected_path:
                print("No file selected. Try again.")
                continue
            path_text = selected_path
        elif choice == "p":
            path_text = input("Enter image path: ").strip().strip('"').strip("'")
        else:
            print("Invalid option. Please choose B, P, or Q.")
            continue

        path = Path(path_text).expanduser()

        if not path.is_file():
            print("That path is not a file. Please try again.")
            continue

        ext = get_extension(path.name)
        if ext not in IMAGE_EXTENSIONS:
            print(f"Unsupported image type '.{ext}'. Use: {', '.join(sorted(IMAGE_EXTENSIONS))}.")
            continue
        return str(path)


def run_interactive_cli() -> None:
    """Interactive command-line flow for description + image."""
    print("BART Incident Classifier CLI")
    print("----------------------------")
    user_summary = input("Enter a short issue description: ").strip()
    image_path = prompt_for_image_path()
    final_query = build_query(user_summary)
    chat_with_media(invoke_url, [image_path], final_query, stream=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Interactive CLI for image + description Nemotron inference"
    )
    parser.parse_args()
    run_interactive_cli()
