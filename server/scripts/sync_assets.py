"""Copy the image assets the API references from the H5 prototype build
(ui/dist/assets/generated/) into server/static/assets/.

Usage: uv run python scripts/sync_assets.py [--source DIR]
"""

import argparse
import re
import shutil
from pathlib import Path

SERVER_DIR = Path(__file__).resolve().parent.parent
DEFAULT_SOURCE = SERVER_DIR.parent / "ui" / "dist" / "assets" / "generated"
DEST = SERVER_DIR / "static" / "assets"

PATTERNS = [
    r"event-cover-\d+\.webp",
    r"theme-scene-\d+\.webp",
    r"category-[a-z-]+\.webp",
    r"reward-[a-z-]+\.webp",
]
NAMES = {
    "red-heart.webp",
    "sunset-talent.webp",
    "wellness.webp",
    "journey.webp",
    "warm-life.webp",
    "hero-community-v2.webp",
    "logo-linghua-li.webp",
    "icon-sprite.webp",
}


def wanted(name: str) -> bool:
    return name in NAMES or any(re.fullmatch(p, name) for p in PATTERNS)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    args = parser.parse_args()
    src: Path = args.source
    if not src.is_dir():
        raise SystemExit(f"source directory not found: {src}")
    DEST.mkdir(parents=True, exist_ok=True)
    copied = skipped = 0
    for f in sorted(src.iterdir()):
        if not f.is_file() or not wanted(f.name):
            continue
        target = DEST / f.name
        if target.exists() and target.stat().st_size == f.stat().st_size and target.stat().st_mtime >= f.stat().st_mtime:
            skipped += 1
            continue
        shutil.copy2(f, target)
        copied += 1
    missing = sorted(n for n in NAMES if not (DEST / n).exists())
    print(f"copied {copied}, up-to-date {skipped}, dest {DEST}")
    if missing:
        print("WARNING missing:", ", ".join(missing))


if __name__ == "__main__":
    main()
