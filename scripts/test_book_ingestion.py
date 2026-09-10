"""
Self-test for book_ingestion.py: builds tiny sample PDF and EPUB files
in-memory (no real book needed), extracts text, and checks it round-trips.
Run: python scripts/test_book_ingestion.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from book_ingestion import ingest_book

SCRATCH = Path(__file__).parent.parent / "output" / "ingestion_test"
SCRATCH.mkdir(parents=True, exist_ok=True)

# --- Build a tiny sample PDF (real text layer) ---
from pypdf import PdfWriter
from reportlab.pdfgen import canvas

pdf_path = SCRATCH / "sample.pdf"
c = canvas.Canvas(str(pdf_path))
c.drawString(100, 750, "Chapter One: The Beginning")
c.drawString(100, 730, "This is a test sentence for ingestion.")
c.save()

result = ingest_book(str(pdf_path))
print("PDF extraction:")
print(" text:", repr(result.text[:80]))
print(" needs_ocr:", result.needs_ocr)
assert "Chapter One" in result.text, "PDF text extraction failed"
assert result.needs_ocr is False, "PDF incorrectly flagged as needing OCR"
print(" PASS\n")

# --- Build a tiny sample EPUB ---
from ebooklib import epub

book = epub.EpubBook()
book.set_identifier("test123")
book.set_title("Test Book")
book.set_language("en")

chapter = epub.EpubHtml(title="Chapter One", file_name="chap1.xhtml", lang="en")
chapter.content = "<h1>Chapter One</h1><p>This is a test sentence for ingestion.</p>"
book.add_item(chapter)
book.toc = (chapter,)
book.add_item(epub.EpubNcx())
book.add_item(epub.EpubNav())
book.spine = ["nav", chapter]

epub_path = SCRATCH / "sample.epub"
epub.write_epub(str(epub_path), book)

result = ingest_book(str(epub_path))
print("EPUB extraction:")
print(" text:", repr(result.text[:80]))
assert "Chapter One" in result.text, "EPUB text extraction failed"
assert "test sentence" in result.text, "EPUB text extraction incomplete"
print(" PASS")
