"""
The "drawing" pass: generate one image per scene, using the style guide
and story bible for consistency. See CLAUDE.md: Two-tier processing per
chapter, Character consistency.

Only the exact chapter requested gets drawn -- scenes come from
bible.chapter_scenes, populated by the understanding pass (directly, or
via catchup.py for skipped chapters), never generated here.
"""
import os
import time
import urllib.request
from pathlib import Path

import replicate
from dotenv import load_dotenv
from replicate.exceptions import ReplicateError

from story_bible import StoryBible
from style_guide import DEFAULT_STYLE, build_scene_prompt
from understanding_pass import Scene

load_dotenv()

OUTPUT_DIR = Path(__file__).parent / "output" / "scenes"


def _character_descriptions(scene: Scene, bible: StoryBible) -> list[str]:
    descriptions = []
    for name in scene.characters_present:
        desc = bible.description_for(name)
        if desc:
            descriptions.append(f"{name}: {desc}")
    return descriptions


def _run_with_retry(prompt: str, max_attempts: int = 4):
    """
    Retries on Replicate rate limits (429) with backoff -- the free tier's
    throttle explicitly tells us how long to wait ("resets in ~7s"), so
    this is worth handling rather than crashing on the first busy moment.
    """
    for attempt in range(1, max_attempts + 1):
        try:
            return replicate.run(
                "black-forest-labs/flux-dev",
                input={"prompt": prompt, "num_outputs": 1},
            )
        except ReplicateError as e:
            is_rate_limit = getattr(e, "status", None) == 429 or "429" in str(e)
            if not is_rate_limit or attempt == max_attempts:
                raise
            wait = 10 * attempt
            print(f"[drawing_pass] rate limited, retrying in {wait}s (attempt {attempt}/{max_attempts})")
            time.sleep(wait)


def generate_scene_image(
    book_id: str,
    chapter_index: int,
    scene_index: int,
    scene: Scene,
    bible: StoryBible,
    style: str = DEFAULT_STYLE,
) -> Path:
    if not os.environ.get("REPLICATE_API_TOKEN"):
        raise SystemExit("REPLICATE_API_TOKEN not found in .env")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / f"{book_id}_ch{chapter_index}_scene{scene_index}.png"
    if out_path.exists():
        return out_path  # already generated -- don't pay for it twice

    characters = _character_descriptions(scene, bible)
    prompt = build_scene_prompt(
        scene_description=scene.description, characters=characters, style=style
    )

    output = _run_with_retry(prompt)
    item = output[0]
    url = item.url if hasattr(item, "url") else str(item)
    urllib.request.urlretrieve(url, out_path)
    return out_path


def generate_chapter_scenes(
    book_id: str, chapter_index: int, bible: StoryBible, style: str = DEFAULT_STYLE
) -> list[Path]:
    """
    Draws every scene for one chapter. Requires that chapter's scenes to
    already be cached in the story bible (i.e. the understanding pass has
    run for it, directly or via catch-up) -- raises clearly if not, rather
    than silently generating nothing.
    """
    if chapter_index not in bible.chapter_scenes:
        raise RuntimeError(
            f"Chapter {chapter_index} has no cached scenes -- run the "
            f"understanding pass (or catchup.ensure_processed_through) for "
            f"it first."
        )

    paths = []
    for i, scene in enumerate(bible.chapter_scenes[chapter_index]):
        path = generate_scene_image(book_id, chapter_index, i, scene, bible, style)
        print(f"[drawing_pass] scene {i+1}/{len(bible.chapter_scenes[chapter_index])} saved: {path}")
        paths.append(path)
    return paths
