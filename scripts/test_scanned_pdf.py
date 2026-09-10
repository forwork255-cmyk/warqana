"""
Self-test: confirm a scanned/image-only PDF (no real text layer) gets
correctly flagged as needs_ocr, instead of silently producing empty/garbage
text as if it were a normal book.
Run: python scripts/test_scanned_pdf.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from book_ingestion import ingest_book

from PIL import Image, ImageDraw
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

SCRATCH = Path(__file__).parent.parent / "output" / "ingestion_test"
SCRATCH.mkdir(parents=True, exist_ok=True)

# Build a fake "scanned page": an image with text drawn as pixels, not as
# a real PDF text layer -- this is what a phone-scanned book page looks
# like to a PDF text extractor: a picture, not selectable text.
img = Image.new("RGB", (600, 800), "white")
draw = ImageDraw.Draw(img)
draw.text((50, 50), "This text is a picture, not real PDF text.", fill="black")
img_path = SCRATCH / "scanned_page.png"
img.save(img_path)

pdf_path = SCRATCH / "scanned_sample.pdf"
c = canvas.Canvas(str(pdf_path), pagesize=(600, 800))
c.drawImage(ImageReader(str(img_path)), 0, 0, width=600, height=800)
c.save()

result = ingest_book(str(pdf_path))
print("Scanned PDF extraction:")
print(" extracted text:", repr(result.text))
print(" needs_ocr:", result.needs_ocr)

assert result.needs_ocr is True, "FAILED: scanned PDF was not flagged for OCR"
print(" PASS: correctly flagged as needing OCR, not silently mis-ingested")
