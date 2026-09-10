"""
Phase 1 style test: generate one manuscript-style image via Flux (Replicate).
Run: python scripts/test_image_style_flux.py
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
    "A flat, non-perspectival Islamic manuscript painting in the style of "
    "13th-century Baghdad School illustration (Maqamat al-Hariri, Yahya "
    "al-Wasiti): a robed man standing in an Abbasid-era courtyard with "
    "arched mashrabiya lattice windows, bold black outlines, gold "
    "background, ornamental border with geometric star patterns and "
    "arabesque scrollwork, muqarnas architectural details, no modern "
    "elements, no Western fantasy style."
)

OUTPUT_DIR = Path(__file__).parent.parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

output = replicate.run(
    "black-forest-labs/flux-dev",
    input={"prompt": PROMPT, "num_outputs": 1},
)

for i, item in enumerate(output):
    out_path = OUTPUT_DIR / f"flux_test_{i}.png"
    url = item.url if hasattr(item, "url") else str(item)
    urllib.request.urlretrieve(url, out_path)
    print(f"Saved: {out_path}")
