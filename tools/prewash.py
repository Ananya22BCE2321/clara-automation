"""Prewash script: move non-.txt files from data/* into data/raw_media/ and create a report.

Report format: data/media_report.json
{
  "found": [ {"path": "data/demo/video.mp4", "type": "video", "size_bytes": 12345, "action": "move-to-raw"}, ... ],
  "summary": { "total_files": 3, "total_size_bytes": 12345 }
}

This script is conservative: it does NOT delete anything. It moves files into data/raw_media/<subdir>/ and writes a JSON report.
"""
from pathlib import Path
import json
import shutil
import mimetypes

BASE = Path(__file__).resolve().parent.parent
DATA = BASE / "data"
RAW = DATA / "raw_media"

def _ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)

def classify(path: Path):
    mt, _ = mimetypes.guess_type(path.as_posix())
    if mt is None:
        return "unknown"
    if mt.startswith("audio"):
        return "audio"
    if mt.startswith("video"):
        return "video"
    if mt.startswith("text"):
        return "text"
    return "other"


def run():
    report = {"found": [], "summary": {"total_files": 0, "total_size_bytes": 0}}
    for sub in [p for p in DATA.iterdir() if p.is_dir()]:
        # skip the raw_media dir itself if present
        if sub.name == RAW.name:
            continue
        for f in sub.iterdir():
            if f.is_file():
                # consider .txt as acceptable; everything else will be moved
                if f.suffix.lower() == ".txt":
                    continue
                # ignore dotfiles
                if f.name.startswith("."):
                    continue
                ftype = classify(f)
                size = f.stat().st_size
                rel = str(f.relative_to(BASE))
                report["found"].append({"path": rel, "type": ftype, "size_bytes": size, "original_name": f.name, "action": "move-to-raw"})
                report["summary"]["total_files"] += 1
                report["summary"]["total_size_bytes"] += size
                # move file to RAW/<subdir>/
                dest_dir = RAW / sub.name
                _ensure_dir(dest_dir)
                dest_path = dest_dir / f.name
                # if destination exists, do not overwrite; append a suffix
                if dest_path.exists():
                    i = 1
                    while True:
                        candidate = dest_dir / f"{f.stem}_{i}{f.suffix}"
                        if not candidate.exists():
                            dest_path = candidate
                            break
                        i += 1
                shutil.move(str(f), str(dest_path))
    # write report
    out = DATA / "media_report.json"
    with out.open("w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)
    print(f"Prewash completed. Report: {out}")

if __name__ == '__main__':
    run()
