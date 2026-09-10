"""
Split a book's raw text into chapters/sections by structural signal, using
a single Claude call over the full text.

Why not regex/keyword matching: tested and confirmed it fails on real
Arabic word-based ordinal headings ("الفصل الأول" has no digit), and per
CLAUDE.md this must also handle books that use an entirely different
structural word (e.g. "Seasons") -- that's a semantic judgment, not a
pattern a regex can enumerate in advance.

Known limitation, not solved here: very long books may exceed the model's
context window in one call. Not hit by realistic novel-length text yet;
revisit if it becomes a real problem.
"""
from dataclasses import dataclass

from claude_client import call_tool

CHAPTER_HEADING_TOOL = {
    "name": "report_chapter_headings",
    "description": (
        "Report the exact chapter/section heading lines found in the book "
        "text, in reading order."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "headings": {
                "type": "array",
                "items": {"type": "string"},
                "description": (
                    "Each heading exactly as it appears in the source text "
                    "(verbatim, including numbering/ordinal words), in "
                    "reading order. Empty list if there are no clear "
                    "section breaks."
                ),
            }
        },
        "required": ["headings"],
    },
}

DETECTION_INSTRUCTIONS = (
    "Identify every chapter or major section heading in this book text, by "
    "structural signal (a short title-like line marking the start of a new "
    "section) -- not by any specific keyword. The book may use 'Chapter', a "
    "bare number, an Arabic word-based ordinal like 'الفصل الأول', or an "
    "entirely different structural word. Return each heading exactly as it "
    "appears in the text, verbatim, in reading order."
)


@dataclass
class Chapter:
    index: int
    title: str
    text: str


def _split_by_headings(full_text: str, headings: list[str]) -> list[Chapter]:
    positions = []
    for heading in headings:
        pos = full_text.find(heading)
        if pos != -1:
            positions.append((pos, heading))
    positions.sort(key=lambda p: p[0])

    if not positions:
        return [Chapter(index=0, title="", text=full_text.strip())]

    chapters = []
    for i, (pos, title) in enumerate(positions):
        start = pos + len(title)
        end = positions[i + 1][0] if i + 1 < len(positions) else len(full_text)
        body = full_text[start:end].strip()
        if body:
            chapters.append(Chapter(index=len(chapters), title=title, text=body))

    return chapters if chapters else [Chapter(index=0, title="", text=full_text.strip())]


def detect_chapters(full_text: str) -> list[Chapter]:
    data = call_tool(
        label="chapter_detection",
        prompt=DETECTION_INSTRUCTIONS + "\n\n" + full_text,
        tool=CHAPTER_HEADING_TOOL,
    )
    return _split_by_headings(full_text, data["headings"])
