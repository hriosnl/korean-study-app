import asyncio
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

from create_anki_cards import (
    list_korean_saver_folders,
    process_text,
    read_input_cards_file,
)

WEB_DIR = Path(__file__).resolve().parent / "web"

app = Flask(__name__, static_folder=str(WEB_DIR), static_url_path="")


@app.get("/")
def index():
    return send_from_directory(WEB_DIR, "index.html")


@app.get("/api/saver-folders")
def saver_folders():
    folders = list_korean_saver_folders()
    return jsonify({"folders": folders, "default": folders[0] if folders else None})


@app.get("/api/input-cards")
def input_cards():
    folder = (request.args.get("folder") or "").strip()
    if not folder:
        return jsonify({"ok": False, "error": "Choose a KoreanSaver folder."}), 400

    try:
        content = read_input_cards_file(folder)
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    except FileNotFoundError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 404

    stripped = content.strip()
    return jsonify(
        {
            "ok": True,
            "content": content,
            "empty": not stripped,
        }
    )


@app.post("/api/prepare")
def prepare():
    payload = request.get_json(silent=True) or {}
    text = (payload.get("text") or "").strip()
    language = (payload.get("language") or "").lower()
    saver_folder = (payload.get("saver_folder") or "").strip() or None

    if not text:
        return jsonify({"ok": False, "error": "Nothing to prepare."}), 400

    if language not in {"english", "korean"}:
        return jsonify({"ok": False, "error": "Choose English or Korean."}), 400

    try:
        result = asyncio.run(
            process_text(
                text,
                language,
                saver_folder=saver_folder,
                interactive=False,
            )
        )
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    except FileNotFoundError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"ok": False, "error": f"Preparation failed: {exc}"}), 500

    return jsonify({"ok": True, **result})