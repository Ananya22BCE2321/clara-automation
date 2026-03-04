"""Mock transcription: create simple text transcripts for any media files found under data/raw_media.

This allows the pipeline to consume them as if they were transcripts. The transcript text will be a placeholder noting the filename.
"""
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
DATA = BASE / "data"
RAW = DATA / "raw_media"


def _ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)


def run():
    for sub in RAW.iterdir():
        if not sub.is_dir():
            continue
        dest_dir = DATA / sub.name
        _ensure_dir(dest_dir)
        for media in sub.iterdir():
            if not media.is_file():
                continue
            # create a transcript file if not already exists
            txtname = media.stem + "_auto.txt"
            txtpath = dest_dir / txtname
            if txtpath.exists():
                continue
            content = f"[AUTOGEN TRANSCRIPT for {media.name}]\n(placeholder content)"
            with txtpath.open("w", encoding="utf-8") as f:
                f.write(content)
            print(f"Created mock transcript: {txtpath}")

if __name__=='__main__':
    run()
