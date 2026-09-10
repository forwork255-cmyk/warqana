"""
Simulate a reader jumping straight to a later chapter, skipping earlier
ones -- confirm catch-up processes all earlier chapters first, and that a
second reader hitting an already-processed chapter doesn't reprocess it.
Run: python scripts/test_catchup.py
"""
import io
import sys
import time
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, str(Path(__file__).parent.parent))
from chapter_detection import detect_chapters
from catchup import ensure_processed_through
from story_bible import STORY_BIBLE_DIR

EXCERPT = Path(__file__).parent.parent / "output" / "ingestion_test" / "sindbad_excerpt.txt"
text = EXCERPT.read_text(encoding="utf-8")
chapters = detect_chapters(text)
print(f"{len(chapters)} sections detected this run.\n")

BOOK_ID = "test_catchup_book"
bible_path = STORY_BIBLE_DIR / f"{BOOK_ID}.json"
if bible_path.exists():
    bible_path.unlink()  # fresh run

# --- Reader 1 jumps straight to the last section, skipping everything ---
target = len(chapters) - 1
print(f"Reader 1 requests section {target} directly (nothing processed yet).")
t0 = time.time()
bible = ensure_processed_through(BOOK_ID, chapters, target)
elapsed_1 = time.time() - t0
print(f" Processed chapters after catch-up: {sorted(bible.processed_chapters)}")
print(f" Took {elapsed_1:.1f}s (real API calls for every chapter)\n")

assert sorted(bible.processed_chapters) == list(range(target + 1)), \
    "FAILED: not all earlier chapters were caught up"
print("PASS: all earlier chapters processed before the target chapter.\n")

# --- Reader 2 requests an EARLIER section that's already been caught up ---
earlier = target - 1
print(f"Reader 2 requests section {earlier} (already processed by reader 1's catch-up).")
t0 = time.time()
bible2 = ensure_processed_through(BOOK_ID, chapters, earlier)
elapsed_2 = time.time() - t0
print(f" Took {elapsed_2:.1f}s (should be near-instant, no new API calls)")

assert elapsed_2 < 2, f"FAILED: reader 2 re-ran processing (took {elapsed_2:.1f}s), cache not used"
print("PASS: already-processed chapters were not reprocessed.")
