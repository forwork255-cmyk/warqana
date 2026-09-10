"""
Full pipeline test: real book text -> chapters -> understanding pass ->
story bible -> drawing pass. Generates real images for every scene in one
real chapter, using actual character descriptions for consistency.
Run: python scripts/test_drawing_pass.py
"""
import io
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, str(Path(__file__).parent.parent))
from chapter_detection import detect_chapters
from catchup import ensure_processed_through
from drawing_pass import generate_chapter_scenes
from story_bible import STORY_BIBLE_DIR

EXCERPT = Path(__file__).parent.parent / "output" / "ingestion_test" / "sindbad_excerpt.txt"
text = EXCERPT.read_text(encoding="utf-8")
chapters = detect_chapters(text)

print("Detected sections:")
for ch in chapters:
    print(f"  {ch.index}: {ch.title!r}")

# Target: the first section with real narrative content (the First Voyage
# tale) rather than the shorter frame-story night markers.
target_index = next(i for i, ch in enumerate(chapters) if "الحكاية" in ch.title)
print(f"\nTarget chapter: {target_index} ({chapters[target_index].title!r})\n")

BOOK_ID = "test_drawing_pipeline"
# Reuses the story bible from the previous run (which already processed
# chapters 0-3 and cached chapter 3's scenes) -- this also tests that
# already-processed chapters are correctly skipped, not redone.
bible = ensure_processed_through(BOOK_ID, chapters, target_index)
scenes = bible.chapter_scenes[target_index]
print(f"\n{len(scenes)} scenes cached for chapter {target_index}. Generating images...\n")

paths = generate_chapter_scenes(BOOK_ID, target_index, bible)
print(f"\nDone. {len(paths)} images generated:")
for p in paths:
    print(f" - {p}")
