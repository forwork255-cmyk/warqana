"""
Resolve newly-extracted character names against the existing story bible,
so the same person isn't recorded twice under different names -- foreign
transliteration variants (جون vs چون) or just inconsistent naming within
the text itself (السندباد vs السندباد البحري). See CLAUDE.md:
Foreign/code-switched names.

Semantic matching (not exact-string matching), for the same reason chapter
detection needed it: name variation can't be enumerated by pattern rules.
"""
from claude_client import call_tool

MATCH_TOOL = {
    "name": "report_name_matches",
    "description": (
        "For each new character, report whether they are the same person "
        "as an already-known character, or genuinely new."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "matches": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "new_name": {"type": "string"},
                        "matches_existing": {
                            "type": ["string", "null"],
                            "description": (
                                "The exact name of the already-known character "
                                "this is the same person as, or null if genuinely "
                                "new (not previously seen)."
                            ),
                        },
                    },
                    "required": ["new_name", "matches_existing"],
                },
            }
        },
        "required": ["matches"],
    },
}

INSTRUCTIONS = (
    "Below is a list of newly-extracted characters (name + description), "
    "and a list of already-known characters from earlier chapters (name + "
    "description). For each new character, decide: are they the same "
    "person as one of the already-known characters -- just named or "
    "described differently (a transliteration variant, a title vs a bare "
    "name, a nickname) -- or are they genuinely a new person? Match on "
    "identity, not just string similarity: two characters with similar "
    "names but different roles/descriptions are NOT the same person."
)


def resolve_character_matches(
    new_characters: list[tuple[str, str]],  # (name, description)
    existing_characters: dict[str, str],  # name -> description
) -> dict[str, str | None]:
    """Returns new_name -> canonical existing name, or None if genuinely new."""
    if not existing_characters:
        return {name: None for name, _ in new_characters}

    new_list = "\n".join(f"- {name}: {desc}" for name, desc in new_characters)
    existing_list = "\n".join(f"- {name}: {desc}" for name, desc in existing_characters.items())

    data = call_tool(
        label="name_resolution",
        prompt=(
            f"{INSTRUCTIONS}\n\nNew characters:\n{new_list}\n\n"
            f"Already-known characters:\n{existing_list}"
        ),
        tool=MATCH_TOOL,
        max_tokens=2048,
    )
    return {m["new_name"]: m["matches_existing"] for m in data["matches"]}
