"""
Run the understanding pass on a real detected section from the Sindbad
excerpt, to confirm character/location/scene extraction works on real text.
Run: python scripts/test_understanding_pass.py
"""
import io
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, str(Path(__file__).parent.parent))
from chapter_detection import detect_chapters
from understanding_pass import extract_understanding

EXCERPT = Path(__file__).parent.parent / "output" / "ingestion_test" / "sindbad_excerpt.txt"
text = EXCERPT.read_text(encoding="utf-8")

chapters = detect_chapters(text)
# Section 2 = "The First Tale of Sindbad... First Voyage" -- real story content.
target = chapters[2]
print(f"Running understanding pass on: {target.title!r} ({len(target.text)} chars)\n")

result = extract_understanding(target.text)

print("=== Characters ===")
for c in result.characters:
    print(f" - {c.name}: {c.description}")

print("\n=== Locations ===")
for l in result.locations:
    print(f" - {l.name}: {l.description}")

print(f"\n=== Scenes ({len(result.scenes)}) ===")
for i, s in enumerate(result.scenes):
    print(f" {i+1}. [{s.location}] {s.description}")
    print(f"    Characters: {s.characters_present}")
