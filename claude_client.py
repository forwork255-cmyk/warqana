"""
Shared helper for structured-output Claude calls used across this project
(chapter_detection, understanding_pass, name_resolution). Every one of
those was previously calling the SDK directly with no error handling and
no cost visibility -- this centralizes both instead of fixing them three
separate times.

- Retries: the Anthropic SDK already retries transient network/5xx/429
  errors internally; this sets an explicit max_retries and wraps failures
  in a clear error instead of a raw SDK exception.
- Cost visibility: logs input/output token counts per call, matching the
  Arabic Research Assistant's per-stage usage logging (see CLAUDE.md --
  "estimate cost before a live test").
"""
import os

from anthropic import Anthropic, APIError
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.environ.get("ANTHROPIC_API_KEY")

_client: Anthropic | None = None


def _get_client() -> Anthropic:
    global _client
    if not API_KEY:
        raise SystemExit("ANTHROPIC_API_KEY not found in .env")
    if _client is None:
        _client = Anthropic(api_key=API_KEY, max_retries=3)
    return _client


def call_tool(
    *,
    label: str,
    prompt: str,
    tool: dict,
    model: str = "claude-sonnet-5",
    max_tokens: int = 4096,
) -> dict:
    """
    Calls Claude with a single forced tool (structured output). Logs token
    usage. Raises a clear RuntimeError on failure or a missing tool-use
    response, instead of crashing on the first API hiccup or an opaque
    StopIteration.
    """
    client = _get_client()
    tool_name = tool["name"]

    try:
        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            tools=[tool],
            tool_choice={"type": "tool", "name": tool_name},
            messages=[{"role": "user", "content": prompt}],
        )
    except APIError as e:
        raise RuntimeError(f"[{label}] Claude API call failed after retries: {e}") from e

    usage = response.usage
    print(f"[usage] {label}: input={usage.input_tokens} output={usage.output_tokens} tokens")

    tool_use = next((b for b in response.content if b.type == "tool_use"), None)
    if tool_use is None:
        raise RuntimeError(
            f"[{label}] Claude did not return the expected '{tool_name}' tool call "
            f"(stop_reason={response.stop_reason})."
        )

    return tool_use.input
