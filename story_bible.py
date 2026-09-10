"""
Persistent per-book record of characters and locations, accumulated across
chapters as they're processed. See CLAUDE.md: Character consistency, and
the story_bibles/{book_id} Firestore schema entry.

Storage here is a local JSON file, standing in for the real Firestore
document until the app has a live database connected -- the data shape
matches what will actually live in Firestore (characters/locations as
name -> description maps).
"""
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from understanding_pass import Scene, UnderstandingResult
from name_resolution import resolve_character_matches

STORY_BIBLE_DIR = Path(__file__).parent / "story_bibles"


@dataclass
class StoryBible:
    book_id: str
    characters: dict[str, str] = field(default_factory=dict)  # canonical name -> description
    locations: dict[str, str] = field(default_factory=dict)
    aliases: dict[str, str] = field(default_factory=dict)  # alias name -> canonical name
    processed_chapters: list[int] = field(default_factory=list)  # which chapters' understanding pass is done
    chapter_scenes: dict[int, list[Scene]] = field(default_factory=dict)  # chapter index -> its scenes, cached
    # so the drawing pass never has to re-run the (paid) understanding pass just to get scenes back.

    def resolve_name(self, name: str) -> str:
        """Canonical name for lookup -- e.g. when a scene names a character."""
        return self.aliases.get(name, name)

    def description_for(self, name: str) -> str | None:
        return self.characters.get(self.resolve_name(name))


def _path(book_id: str) -> Path:
    STORY_BIBLE_DIR.mkdir(exist_ok=True)
    return STORY_BIBLE_DIR / f"{book_id}.json"


def load_story_bible(book_id: str) -> StoryBible:
    path = _path(book_id)
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        chapter_scenes = {
            int(idx): [Scene(**s) for s in scenes]
            for idx, scenes in data.get("chapter_scenes", {}).items()
        }
        return StoryBible(
            book_id=book_id,
            characters=data.get("characters", {}),
            locations=data.get("locations", {}),
            aliases=data.get("aliases", {}),
            processed_chapters=data.get("processed_chapters", []),
            chapter_scenes=chapter_scenes,
        )
    return StoryBible(book_id=book_id)


def save_story_bible(bible: StoryBible) -> None:
    path = _path(bible.book_id)
    path.write_text(
        json.dumps(
            {
                "characters": bible.characters,
                "locations": bible.locations,
                "aliases": bible.aliases,
                "processed_chapters": bible.processed_chapters,
                "chapter_scenes": {
                    idx: [asdict(s) for s in scenes]
                    for idx, scenes in bible.chapter_scenes.items()
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def merge_chapter_result(
    bible: StoryBible, result: UnderstandingResult, chapter_index: int
) -> StoryBible:
    """
    Adds newly-seen characters/locations. Existing entries are never
    overwritten -- once a character's appearance is established (from text
    or fallback), every later scene reuses the same description.

    Before adding a "new" character, checks whether they're actually an
    already-known character under a different name (transliteration
    variant, title vs bare name, etc.) -- if so, records an alias instead
    of a duplicate entry.

    Also caches this chapter's scenes, so the drawing pass can read them
    later without re-running the understanding pass.
    """
    unmatched = [c for c in result.characters if c.name not in bible.characters
                 and c.name not in bible.aliases]

    if unmatched:
        matches = resolve_character_matches(
            new_characters=[(c.name, c.description) for c in unmatched],
            existing_characters=bible.characters,
        )
        for c in unmatched:
            canonical = matches.get(c.name)
            if canonical and canonical in bible.characters:
                bible.aliases[c.name] = canonical
            else:
                bible.characters[c.name] = c.description

    for l in result.locations:
        if l.name not in bible.locations:
            bible.locations[l.name] = l.description

    bible.chapter_scenes[chapter_index] = result.scenes
    return bible
