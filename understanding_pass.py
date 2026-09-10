"""
The "understanding" pass: cheap, text-only Claude call that reads one
chapter and extracts characters, locations, and the 3-10 moments that
carry real visual weight -- see CLAUDE.md, Two-tier processing per chapter.

No image generation happens here. Output feeds the story bible (Phase 2
continued) and later the drawing pass (Phase 3).
"""
from dataclasses import dataclass, field

from claude_client import call_tool

UNDERSTANDING_TOOL = {
    "name": "report_chapter_understanding",
    "description": (
        "Report the characters, locations, and visually significant "
        "moments found in this chapter."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "characters": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Exactly as written in the text, never translated.",
                        },
                        "description": {
                            "type": "string",
                            "description": (
                                "Physical appearance if the text describes it. "
                                "If not described, generate a plausible one from "
                                "context (setting, era, culture) -- avoid "
                                "stereotype defaults."
                            ),
                        },
                    },
                    "required": ["name", "description"],
                },
            },
            "locations": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "description": {"type": "string"},
                    },
                    "required": ["name", "description"],
                },
            },
            "scenes": {
                "type": "array",
                "minItems": 3,
                "maxItems": 10,
                "description": (
                    "The moments in this chapter that carry real visual "
                    "weight -- not a summary of every event, only what's "
                    "worth illustrating."
                ),
                "items": {
                    "type": "object",
                    "properties": {
                        "description": {
                            "type": "string",
                            "description": "Setting, action, and mood of this specific moment.",
                        },
                        "characters_present": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "location": {"type": "string"},
                    },
                    "required": ["description", "characters_present", "location"],
                },
            },
        },
        "required": ["characters", "locations", "scenes"],
    },
}

INSTRUCTIONS = (
    "Read this chapter and extract: (1) every named character with a "
    "physical description -- exactly as named in the text, never "
    "translated; if the text doesn't describe appearance, invent a "
    "plausible one from context, avoiding stereotypes; (2) every distinct "
    "location; (3) the 3-10 moments that actually carry real visual "
    "weight -- not a full summary, only what's worth illustrating. A short "
    "chapter should yield fewer scenes, a long one more."
)


@dataclass
class Scene:
    description: str
    characters_present: list[str]
    location: str


@dataclass
class Character:
    name: str
    description: str


@dataclass
class Location:
    name: str
    description: str


@dataclass
class UnderstandingResult:
    characters: list[Character] = field(default_factory=list)
    locations: list[Location] = field(default_factory=list)
    scenes: list[Scene] = field(default_factory=list)


def extract_understanding(chapter_text: str) -> UnderstandingResult:
    data = call_tool(
        label="understanding_pass",
        prompt=INSTRUCTIONS + "\n\n" + chapter_text,
        tool=UNDERSTANDING_TOOL,
    )

    return UnderstandingResult(
        characters=[Character(**c) for c in data["characters"]],
        locations=[Location(**l) for l in data["locations"]],
        scenes=[Scene(**s) for s in data["scenes"]],
    )
