"""
Phase 1 style test: generate one manuscript-style image via Imagen.
Run: python scripts/test_image_style.py
"""
import os
from io import BytesIO
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from PIL import Image

load_dotenv()

API_KEY = os.environ.get("GOOGLE_API_KEY")
if not API_KEY:
    raise SystemExit("GOOGLE_API_KEY not found in .env")

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

client = genai.Client(api_key=API_KEY)

response = client.models.generate_content(
    model="gemini-2.5-flash-image",
    contents=PROMPT,
)

saved = False
for part in response.candidates[0].content.parts:
    if getattr(part, "inline_data", None) is not None:
        image = Image.open(BytesIO(part.inline_data.data))
        out_path = OUTPUT_DIR / "imagen_test_0.png"
        image.save(str(out_path))
        print(f"Saved: {out_path}")
        saved = True

if not saved:
    print("No image returned. Full response:")
    print(response)
