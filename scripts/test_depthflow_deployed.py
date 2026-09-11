"""
First real test of the deployed DepthFlow model on Replicate: feed it one
of our already-generated scene images and see the actual parallax video.

Uses manual create + poll (not replicate.run()'s blocking wait) since the
first invocation needs to download depth-estimation model weights, which
can take longer than the client's default read timeout.
Run: python scripts/test_depthflow_deployed.py
"""
import os
import time
from pathlib import Path

import replicate
from dotenv import load_dotenv

load_dotenv()

if not os.environ.get("REPLICATE_API_TOKEN"):
    raise SystemExit("REPLICATE_API_TOKEN not found in .env")

MODEL_VERSION = "forwork255-cmyk/warqana-depthflow:e829832edfeece018f1c9cf4c3f03ec59cf49e63b8f5cf3591ec8fed5e6b9d12"
INPUT_IMAGE = Path(__file__).parent.parent / "output" / "scenes" / "test_drawing_pipeline_ch3_scene0.png"
OUTPUT_DIR = Path(__file__).parent.parent / "output" / "videos"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

print(f"Input: {INPUT_IMAGE}")

client = replicate.Client(api_token=os.environ["REPLICATE_API_TOKEN"], timeout=30)

with open(INPUT_IMAGE, "rb") as f:
    prediction = client.predictions.create(
        version=MODEL_VERSION.split(":")[1],
        input={"image": f, "duration": 5.0},
    )

print(f"Prediction created: {prediction.id} (status: {prediction.status})")

MAX_WAIT = 900  # 15 minutes -- generous for a cold-start first call
t0 = time.time()
last_status = None

while prediction.status not in ("succeeded", "failed", "canceled"):
    if time.time() - t0 > MAX_WAIT:
        print(f"Timed out after {MAX_WAIT}s waiting. Last status: {prediction.status}")
        raise SystemExit(1)
    if prediction.status != last_status:
        print(f"[{time.time()-t0:.0f}s] status: {prediction.status}")
        last_status = prediction.status
    time.sleep(5)
    prediction.reload()

elapsed = time.time() - t0
print(f"\nFinal status: {prediction.status} (took {elapsed:.0f}s)")

if prediction.status == "succeeded":
    output_url = prediction.output
    print(f"Output: {output_url}")
    import urllib.request
    out_path = OUTPUT_DIR / "test_scene0.mp4"
    urllib.request.urlretrieve(output_url, out_path)
    print(f"Saved: {out_path}")
else:
    print(f"Error/logs: {prediction.error}\n{prediction.logs}")
