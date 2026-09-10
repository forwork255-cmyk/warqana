"""
Phase 1 test: confirm style_guide.build_scene_prompt() produces a working
prompt end-to-end, including character-consistency injection.
Run: python scripts/test_style_guide_builder.py
"""
import os
import sys
import urllib.request
from pathlib import Path

import replicate
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))
from style_guide import build_scene_prompt, MANUSCRIPT_STYLE

load_dotenv()

if not os.environ.get("REPLICATE_API_TOKEN"):
    raise SystemExit("REPLICATE_API_TOKEN not found in .env")

# Fake "story bible" character description + fake extracted scene, standing
# in for what Phase 2's understanding pass will produce for real later.
FAKE_CHARACTER = (
    "Layla: a young woman with dark braided hair, wearing a deep blue "
    "embroidered robe with a gold sash"
)
FAKE_SCENE = (
    "Layla stands alone at night on a rooftop overlooking a moonlit river, "
    "gazing at the water, a sense of quiet longing."
)

prompt = build_scene_prompt(
    scene_description=FAKE_SCENE,
    characters=[FAKE_CHARACTER],
    style=MANUSCRIPT_STYLE,
)
print("Built prompt:\n", prompt, "\n")

OUTPUT_DIR = Path(__file__).parent.parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

output = replicate.run(
    "black-forest-labs/flux-dev",
    input={"prompt": prompt, "num_outputs": 1},
)

for i, item in enumerate(output):
    out_path = OUTPUT_DIR / f"builder_test_{i}.png"
    url = item.url if hasattr(item, "url") else str(item)
    urllib.request.urlretrieve(url, out_path)
    print(f"Saved: {out_path}")
