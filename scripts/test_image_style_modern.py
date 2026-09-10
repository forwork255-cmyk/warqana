"""
Phase 1 style test: same scene, modern/contemporary illustration style,
to confirm the pipeline can switch styles per reader/book.
Run: python scripts/test_image_style_modern.py
"""
import os
import urllib.request
from pathlib import Path

import replicate
from dotenv import load_dotenv

load_dotenv()

if not os.environ.get("REPLICATE_API_TOKEN"):
    raise SystemExit("REPLICATE_API_TOKEN not found in .env")

PROMPT = (
    "A modern realistic cinematic illustration, contemporary character "
    "design: a man in modern clothing standing in a courtyard with "
    "contemporary architecture, natural lighting, soft realistic color "
    "grading, detailed digital painting style, no manuscript or "
    "historical ornamentation, no gold background."
)

OUTPUT_DIR = Path(__file__).parent.parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

output = replicate.run(
    "black-forest-labs/flux-dev",
    input={"prompt": PROMPT, "num_outputs": 1},
)

for i, item in enumerate(output):
    out_path = OUTPUT_DIR / f"modern_test_{i}.png"
    url = item.url if hasattr(item, "url") else str(item)
    urllib.request.urlretrieve(url, out_path)
    print(f"Saved: {out_path}")
