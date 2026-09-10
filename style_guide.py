"""
Reusable prompt-building for scene image generation.

Each generated image combines three things:
1. A style block (fixed per book/reader choice — e.g. manuscript or modern)
2. Scene-specific content (extracted from the actual chapter text — setting,
   action, mood; not hardcoded)
3. Character descriptions (from the story bible, for visual consistency)

Per CLAUDE.md: manuscript style is the default, but a reader can request a
different style instead — that's why style is a parameter, not baked in.
"""

MANUSCRIPT_STYLE = (
    "Flat, non-perspectival Islamic manuscript painting in the style of "
    "13th-century Baghdad School illustration (Maqamat al-Hariri, Yahya "
    "al-Wasiti): bold black outlines, gold background, ornamental border "
    "with geometric star patterns and arabesque scrollwork, muqarnas "
    "architectural details where relevant. No modern elements, no Western "
    "fantasy style, no photorealism."
)

MODERN_STYLE = (
    "Modern realistic cinematic illustration, contemporary character "
    "design, natural lighting, soft realistic color grading, detailed "
    "digital painting style. No manuscript or historical ornamentation, "
    "no gold background."
)

DEFAULT_STYLE = MANUSCRIPT_STYLE


def build_scene_prompt(scene_description: str, characters: list[str] | None = None,
                        style: str = DEFAULT_STYLE) -> str:
    """
    scene_description: what's happening in this specific scene (setting,
        action, mood) — comes from the understanding pass, not hardcoded.
    characters: character appearance descriptions from the story bible, for
        anyone appearing in this scene.
    style: a style block (MANUSCRIPT_STYLE, MODERN_STYLE, or free-text if a
        reader requested something else entirely).
    """
    parts = [style, scene_description]
    if characters:
        parts.append("Characters in this scene: " + "; ".join(characters))
    return " ".join(parts)
