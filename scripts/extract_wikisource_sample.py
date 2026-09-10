"""
Extract clean article text from the downloaded Sindbad the Sailor Wikisource
page, for use as a real public-domain test sample.
Run: python scripts/extract_wikisource_sample.py
"""
from pathlib import Path
from bs4 import BeautifulSoup

RAW = Path(__file__).parent.parent / "output" / "ingestion_test" / "sindbad_raw.html"
OUT = Path(__file__).parent.parent / "output" / "ingestion_test" / "sindbad_sample.txt"

with open(RAW, encoding="utf-8") as f:
    soup = BeautifulSoup(f.read(), "html.parser")

content = soup.find("div", class_="mw-parser-output")
# Drop nav/edit/metadata elements Wikisource adds around the real text.
for tag in content.find_all(["table", "sup", "span"]):
    tag.decompose()

text = content.get_text(separator="\n")
lines = [l.strip() for l in text.splitlines() if l.strip()]
clean_text = "\n".join(lines)

OUT.write_text(clean_text, encoding="utf-8")
print(f"Saved {len(clean_text)} chars to {OUT}")
print("---first 500 chars---")
print(clean_text[:500])
