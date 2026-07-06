# Korean Study App

Desktop app for preparing Anki import cards from English/Korean study material. Paste card data, generate Korean audio, copy images, and export TSV files ready for Anki.

## What it does

- **English → Korean** — prepare cards from pasted input; images are looked up in `anki/`
- **Korean → English** — select a date folder from `KoreanSaver/`, auto-load `input-cards.txt`, and prepare cards using images from that folder
- Generates Korean TTS audio via Edge TTS and copies it into your Anki `collection.media` folder
- Writes output TSV files to `anki/English-to-KR.tsv` or `anki/Korean-to-EN.tsv`

## Requirements

- Python 3.11+
- Anki with a known `collection.media` path
- A `KoreanSaver/` directory (from [chrome-korean-saver](https://github.com/hriosnl/chrome-korean-saver)) for Korean-mode image folders
- An `anki/` directory for English-mode output and image lookup

The app searches upward from its install directory to find `KoreanSaver/` and `anki/`. In a typical layout:

```
Korean Study/
├── anki/
├── KoreanSaver/
│   └── 2026-07-06/
│       ├── input-cards.txt
│       └── *.webp / *.png
└── src/app/          ← this repo
```

## Setup

```bash
python3 -m venv myenv
source myenv/bin/activate        # Windows: myenv\Scripts\activate
pip install -r requirements.txt
```

### Anki media directory

Create `anki_audio_config.json` in the app root:

```json
{
  "anki_media_dir": "/Users/you/Library/Application Support/Anki2/User 1/collection.media"
}
```

On macOS, replace `User 1` with your Anki profile name. This file is gitignored because the path is machine-specific.

## Run

**Desktop window (recommended):**

```bash
python main.py
```

**Flask server only** (open `http://127.0.0.1:5000` in a browser):

```bash
python -c "from server import app; app.run(port=5000)"
```

## Card input format

Semicolon-separated rows (tabs also accepted):

```
English;Korean;KoreanWithEmojis;Romanization;Chunking;Notes;Priority;ImageName
```

`ImageName` is the image hash/filename stem used to find `.webp`, `.png`, or `.jpg` files in the relevant folder.

## Korean mode

1. Switch the language toggle to **Korean**
2. Pick a date folder with the calendar button
3. The textarea loads `input-cards.txt` from that folder automatically
4. Click **Prepare cards**

If `input-cards.txt` is empty, a warning is shown in the textarea instead.

## Output

| Mode    | Output file           | Image source        |
|---------|-----------------------|---------------------|
| English | `anki/English-to-KR.tsv` | `anki/`          |
| Korean  | `anki/Korean-to-EN.tsv`  | `KoreanSaver/{date}/` |

Output is written to the `anki/` folder at the project root (the directory that contains `KoreanSaver/`), not inside the app repo. The success message shows the full saved path.

Generated audio and copied images are placed in your Anki `collection.media` folder.

## Project structure

```
.
├── main.py                 # Desktop app entry point (pywebview)
├── server.py               # Flask API + static file server
├── create_anki_cards.py    # Card parsing, audio, image copy logic
├── requirements.txt
└── web/
    ├── index.html
    ├── styles.css
    ├── app.js
    └── assets/plant.png
```

## API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/saver-folders` | GET | List `KoreanSaver/` date folders |
| `/api/input-cards?folder=` | GET | Read `input-cards.txt` for a folder |
| `/api/prepare` | POST | Prepare cards from pasted text |

## License

Public repository. Use and adapt as needed.