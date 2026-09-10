"""
Run chapter_detection on a real public-domain Arabic excerpt (Sindbad the
Sailor, from Arabic Wikisource) -- a real structural-signal stress test,
since it uses "night" markers, not "chapter".
Run: python scripts/test_real_chapter_detection.py
"""
import io
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, str(Path(__file__).parent.parent))
from chapter_detection import detect_chapters

EXCERPT = Path(__file__).parent.parent / "output" / "ingestion_test" / "sindbad_excerpt.txt"
text = EXCERPT.read_text(encoding="utf-8")

chapters = detect_chapters(text)
print(f"Detected {len(chapters)} sections:\n")
for ch in chapters:
    print(f"--- Section {ch.index}: {ch.title!r} ---")
    print(ch.text[:150].replace("\n", " "), "...\n")
