"""
Catch-up mechanism: if a reader jumps to a chapter whose earlier chapters
were never processed, run the cheap understanding pass on those skipped
chapters first (text only), so the story bible has an accurate running
record before any images get drawn. See CLAUDE.md: Catch-up mechanism for
skipped chapters.

The first reader to reach a given chapter absorbs this delay; the result
(story_bible.processed_chapters) is cached for everyone after.
"""
from chapter_detection import Chapter
from story_bible import StoryBible, load_story_bible, save_story_bible, merge_chapter_result
from understanding_pass import extract_understanding


def ensure_processed_through(
    book_id: str, chapters: list[Chapter], target_index: int
) -> StoryBible:
    """
    Runs the understanding pass on every chapter from 0 through
    target_index that hasn't been processed yet, in order -- so character/
    location consistency is correct by the time target_index is reached,
    regardless of what a reader skipped.
    """
    bible = load_story_bible(book_id)

    for chapter in chapters[: target_index + 1]:
        if chapter.index in bible.processed_chapters:
            continue  # already cached from a previous reader/run
        result = extract_understanding(chapter.text)
        bible = merge_chapter_result(bible, result, chapter.index)
        bible.processed_chapters.append(chapter.index)
        save_story_bible(bible)  # persist after each chapter, not just at the end

    return bible
