"""
Self-test for chapter_detection.py against realistic heading styles,
including Arabic word-based ordinals (not digits) -- a common real pattern
this needs to handle, not just "Chapter 1".
Run: python scripts/test_chapter_detection.py
"""
import io
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, str(Path(__file__).parent.parent))
from chapter_detection import detect_chapters as split_into_chapters

# Case 1: English, numeric heading
english_text = """Chapter 1

This is the first chapter's content. It goes on for a while.

Chapter 2

This is the second chapter's content, quite different from the first.
"""

# Case 2: Arabic, WORD-based ordinal heading (no digits) -- the realistic
# case, since many Arabic novels write "الفصل الأول" not "الفصل 1".
arabic_text = """الفصل الأول

هذا نص الفصل الأول. يستمر لفترة من الوقت ويحكي قصة الشخصية الرئيسية.

الفصل الثاني

هذا نص الفصل الثاني، مختلف تماما عن الفصل الأول من حيث الأحداث.
"""

print("=== English numeric headings ===")
chapters = split_into_chapters(english_text)
for ch in chapters:
    print(f" Chapter {ch.index}: title={ch.title!r} text={ch.text[:40]!r}")
print(f" Detected {len(chapters)} chapters (expected 2)\n")

print("=== Arabic word-based ordinal headings ===")
chapters = split_into_chapters(arabic_text)
for ch in chapters:
    print(f" Chapter {ch.index}: title={ch.title!r} text={ch.text[:40]!r}")
print(f" Detected {len(chapters)} chapters (expected 2)")
