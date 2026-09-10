"""
Process two real sections from the Sindbad excerpt in sequence, and confirm
the story bible: (1) accumulates new characters/locations, (2) does NOT
overwrite an already-established character's description on a later
chapter, even if that chapter's extraction phrases it differently.
Run: python scripts/test_story_bible.py
"""
import io
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, str(Path(__file__).parent.parent))
from chapter_detection import detect_chapters
from understanding_pass import extract_understanding
from story_bible import load_story_bible, save_story_bible, merge_chapter_result

EXCERPT = Path(__file__).parent.parent / "output" / "ingestion_test" / "sindbad_excerpt.txt"
text = EXCERPT.read_text(encoding="utf-8")
chapters = detect_chapters(text)

print("Detected sections this run:")
for ch in chapters:
    print(f"  {ch.index}: {ch.title!r}")
print()

BOOK_ID = "test_sindbad"
bible = load_story_bible(BOOK_ID)
bible.characters.clear()  # fresh run for a clean test
bible.locations.clear()

# Process ALL detected sections in order, so we're guaranteed to hit real
# recurring characters (e.g. Sindbad the Sailor appears in nearly every
# section here) rather than guessing indices from a prior run's split.
first_seen_descriptions = {}

for ch in chapters:
    print(f"Processing section {ch.index}: {ch.title!r}")
    result = extract_understanding(ch.text)
    before_chars = set(bible.characters.keys())
    bible = merge_chapter_result(bible, result, ch.index)
    new_chars = set(bible.characters.keys()) - before_chars
    repeated = [c.name for c in result.characters if c.name in before_chars]
    print(f"  New characters: {sorted(new_chars) or 'none'}")
    print(f"  Recurring characters (should reuse existing description): {repeated or 'none'}")
    for name in repeated:
        if name not in first_seen_descriptions:
            first_seen_descriptions[name] = bible.characters[name]

save_story_bible(bible)

print("\n=== Consistency check ===")
for name, first_desc in first_seen_descriptions.items():
    still_matches = bible.characters[name] == first_desc
    print(f" {name}: description unchanged after re-appearing? {still_matches}")

print(f"\n=== Final story bible for {BOOK_ID} ===")
print(f"Characters ({len(bible.characters)}):")
for name, desc in bible.characters.items():
    print(f" - {name}: {desc[:80]}...")
print(f"\nLocations ({len(bible.locations)}):")
for name, desc in bible.locations.items():
    print(f" - {name}: {desc[:80]}...")
