#!/usr/bin/env python3
"""
Create Anki cards from semicolon-separated lines.
Format: English;Korean;KoreanWithEmojis;Romanization;Chunking;Notes;Priority;ImageName
"""

import asyncio
import csv
import hashlib
import json
import shutil
import sys
from pathlib import Path

import edge_tts
import pandas as pd

APP_DIR = Path(__file__).resolve().parent
CONFIG_FILE = APP_DIR / "anki_audio_config.json"
VOICE = "ko-KR-SunHiNeural"

OUTPUT_FILENAMES = {
    "english": "English-to-KR.tsv",
    "korean": "Korean-to-EN.tsv",
}


def find_project_root() -> Path:
    current = APP_DIR
    for _ in range(5):
        if (current / "KoreanSaver").is_dir() or (current / "anki").is_dir():
            return current
        if current.parent == current:
            break
        current = current.parent
    return APP_DIR.parent.parent


PROJECT_ROOT = find_project_root()
ANKI_DIR = PROJECT_ROOT / "anki"
KOREAN_SAVER_DIR = PROJECT_ROOT / "KoreanSaver"


def get_anki_media_dir(interactive: bool = True) -> Path:
    if CONFIG_FILE.exists():
        config = json.loads(CONFIG_FILE.read_text())
        path = Path(config["anki_media_dir"]).expanduser()
        if path.exists():
            return path

    if not interactive:
        raise FileNotFoundError(
            "Anki media directory not configured. "
            f"Create {CONFIG_FILE} with your collection.media path."
        )

    print("\nAnki media directory not configured.\n")
    print("Examples:")
    print("macOS: ~/Library/Application Support/Anki2/User 1/collection.media")
    print()
    user_input = input("Enter your Anki collection.media path:\n> ").strip()
    media_dir = Path(user_input).expanduser()
    if not media_dir.exists():
        raise FileNotFoundError(f"Directory does not exist:\n{media_dir}")
    CONFIG_FILE.write_text(json.dumps({"anki_media_dir": str(media_dir)}, indent=2))
    return media_dir


def list_korean_saver_folders() -> list[str]:
    if not KOREAN_SAVER_DIR.exists():
        return []

    folders = [
        path.name
        for path in KOREAN_SAVER_DIR.iterdir()
        if path.is_dir() and not path.name.startswith(".")
    ]
    return sorted(folders, reverse=True)


INPUT_CARDS_FILENAME = "input-cards.txt"


def resolve_saver_folder(saver_folder: str) -> Path:
    if not saver_folder or saver_folder != Path(saver_folder).name:
        raise ValueError("Invalid KoreanSaver folder.")

    folder_path = (KOREAN_SAVER_DIR / saver_folder).resolve()
    if folder_path.parent != KOREAN_SAVER_DIR.resolve():
        raise ValueError("Invalid KoreanSaver folder.")
    if not folder_path.is_dir():
        raise FileNotFoundError(f"KoreanSaver folder not found: {saver_folder}")
    return folder_path


def read_input_cards_file(saver_folder: str) -> str:
    folder_path = resolve_saver_folder(saver_folder)
    file_path = folder_path / INPUT_CARDS_FILENAME
    if not file_path.is_file():
        raise FileNotFoundError(
            f"{INPUT_CARDS_FILENAME} not found in {saver_folder}."
        )
    return file_path.read_text(encoding="utf-8")


def make_filename(text: str) -> str:
    digest = hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]
    return f"ko_{digest}.mp3"


async def generate_audio(text: str, output_path: Path) -> None:
    communicate = edge_tts.Communicate(text=text, voice=VOICE)
    await communicate.save(str(output_path))


def parse_cards(text: str) -> list[dict]:
    cards = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue

        delimiter = "\t" if "\t" in line else ";"
        parts = [p.strip() for p in line.split(delimiter)]
        if len(parts) < 8:
            continue

        cards.append(
            {
                "English": parts[0],
                "Korean": parts[1],
                "KoreanWithEmojis": parts[2],
                "Romanization": parts[3],
                "Chunking": parts[4],
                "Notes": parts[5],
                "Priority": parts[6],
                "ImageName": parts[7],
            }
        )
    return cards


def find_image_file(image_hash: str, search_dirs: list[Path]) -> Path | None:
    if not image_hash:
        return None

    for search_dir in search_dirs:
        candidates = [
            search_dir / f"{image_hash}.webp",
            search_dir / f"{image_hash}.png",
            search_dir / f"{image_hash}.jpg",
            search_dir / f"{image_hash}.jpeg",
            search_dir / image_hash,
        ]
        image_file = next((c for c in candidates if c.exists()), None)
        if image_file:
            return image_file

        for file_path in search_dir.glob(f"*{image_hash}*"):
            if file_path.is_file() and file_path.suffix.lower() in {
                ".webp",
                ".png",
                ".jpg",
                ".jpeg",
            }:
                return file_path

    return None


async def prepare_cards(
    cards: list[dict],
    output_file: Path,
    image_search_dirs: list[Path],
    interactive: bool = False,
) -> dict:
    if not cards:
        raise ValueError("No valid card rows found in input.")

    media_dir = get_anki_media_dir(interactive=interactive)
    df = pd.DataFrame(cards)
    df["Audio"] = ""

    generated_audio = 0
    reused_audio = 0
    copied_images = 0
    reused_images = 0
    missing_images = 0
    image_tags = []

    for idx, row in df.iterrows():
        korean = str(row["Korean"]).strip()
        if not korean:
            image_tags.append("")
            continue

        audio_filename = make_filename(korean)
        mp3_path = media_dir / audio_filename
        if not mp3_path.exists():
            print(f"Generating audio: {audio_filename}")
            try:
                await generate_audio(korean, mp3_path)
                generated_audio += 1
            except Exception as exc:
                print(f"Failed audio {audio_filename}: {exc}")
                df.at[idx, "Audio"] = ""
                image_tags.append("")
                continue
        else:
            reused_audio += 1
        df.at[idx, "Audio"] = f"[sound:{audio_filename}]"

        image_hash = str(row["ImageName"]).strip()
        img_tag = ""
        image_file = find_image_file(image_hash, image_search_dirs)
        if image_file:
            ext = image_file.suffix.lower() or ".webp"
            target_name = f"ko_img_{image_hash}{ext}"
            target_path = media_dir / target_name

            if not target_path.exists():
                shutil.copy2(image_file, target_path)
                print(f"Copied image: {target_name}")
                copied_images += 1
            else:
                reused_images += 1

            img_tag = f'<img src="{target_name}">'
        elif image_hash:
            print(f"Image not found for ImageName: {image_hash}")
            missing_images += 1

        image_tags.append(img_tag)

    df["Image"] = image_tags

    output_cols = [
        "English",
        "Korean",
        "KoreanWithEmojis",
        "Romanization",
        "Chunking",
        "Notes",
        "Priority",
        "Audio",
        "Image",
    ]

    output_file.parent.mkdir(parents=True, exist_ok=True)
    df[output_cols].to_csv(
        output_file,
        sep="\t",
        index=False,
        header=False,
        quoting=csv.QUOTE_NONE,
        escapechar="\\",
    )

    result = {
        "output_file": str(output_file),
        "output_filename": output_file.name,
        "media_dir": str(media_dir),
        "card_count": len(cards),
        "audio_generated": generated_audio,
        "audio_reused": reused_audio,
        "images_copied": copied_images,
        "images_reused": reused_images,
        "images_missing": missing_images,
    }

    print()
    print(f"Audio - Generated: {generated_audio} | Reused: {reused_audio}")
    print(
        "Images - "
        f"Copied: {copied_images} | Reused: {reused_images} | Missing: {missing_images}"
    )
    print(f"Output: {output_file}")
    print(f"Media folder: {media_dir}")
    return result


async def process_text(
    text: str,
    language: str,
    saver_folder: str | None = None,
    interactive: bool = False,
) -> dict:
    if language not in OUTPUT_FILENAMES:
        raise ValueError("Language must be 'english' or 'korean'.")

    cleaned = text.strip()
    if not cleaned:
        raise ValueError("Nothing to process.")

    cards = parse_cards(cleaned)
    output_file = ANKI_DIR / OUTPUT_FILENAMES[language]

    if language == "korean":
        if not saver_folder:
            raise ValueError("Choose a KoreanSaver folder for Korean cards.")
        image_dir = KOREAN_SAVER_DIR / saver_folder
        if not image_dir.is_dir():
            raise FileNotFoundError(f"KoreanSaver folder not found: {saver_folder}")
        image_search_dirs = [image_dir]
    else:
        image_search_dirs = [ANKI_DIR]

    result = await prepare_cards(
        cards,
        output_file,
        image_search_dirs,
        interactive=interactive,
    )
    result["language"] = language
    if saver_folder:
        result["saver_folder"] = saver_folder
    return result


async def process_file(input_path: Path, interactive: bool = True) -> dict:
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    cards = parse_cards(input_path.read_text(encoding="utf-8"))
    input_dir = input_path.parent
    search_dirs = [input_dir]
    if KOREAN_SAVER_DIR.exists():
        search_dirs.extend(
            sorted(
                (p for p in KOREAN_SAVER_DIR.iterdir() if p.is_dir()),
                reverse=True,
            )
        )

    output_dir = input_dir / "anki_cards_input"
    output_file = output_dir / "prepared-anki-cards.tsv"
    return await prepare_cards(cards, output_file, search_dirs, interactive=interactive)


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage:\npython create_anki_cards.py yourfile.txt")
        sys.exit(1)
    asyncio.run(process_file(Path(sys.argv[1])))


if __name__ == "__main__":
    main()