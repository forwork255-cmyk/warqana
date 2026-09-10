"""
Book upload -> raw text extraction.

Only handles getting the full text out of a PDF or EPUB. Chapter/section
splitting is a separate concern (Phase 2's understanding pass), not this
module's job.

Scanned (image-only) PDFs are flagged via needs_ocr rather than processed —
Arabic OCR accuracy isn't trusted yet (see CLAUDE.md, Phase 9 in ROADMAP.md).
"""
from dataclasses import dataclass

from pypdf import PdfReader
from ebooklib import epub, ITEM_DOCUMENT
from bs4 import BeautifulSoup


@dataclass
class IngestResult:
    text: str
    source_type: str  # "pdf" or "epub"
    needs_ocr: bool


def extract_pdf(file_path: str) -> IngestResult:
    reader = PdfReader(file_path)
    pages_text = [page.extract_text() or "" for page in reader.pages]
    full_text = "\n".join(pages_text).strip()

    # A text-based PDF yields real characters per page; a scanned PDF
    # yields empty/near-empty extraction across most pages.
    non_empty_pages = sum(1 for t in pages_text if t.strip())
    needs_ocr = len(reader.pages) > 0 and non_empty_pages / len(reader.pages) < 0.5

    return IngestResult(text=full_text, source_type="pdf", needs_ocr=needs_ocr)


def extract_epub(file_path: str) -> IngestResult:
    book = epub.read_epub(file_path)
    chunks = []
    for item in book.get_items_of_type(ITEM_DOCUMENT):
        soup = BeautifulSoup(item.get_content(), "html.parser")
        chunks.append(soup.get_text(separator="\n").strip())
    full_text = "\n\n".join(c for c in chunks if c)
    return IngestResult(text=full_text, source_type="epub", needs_ocr=False)


def ingest_book(file_path: str) -> IngestResult:
    if file_path.lower().endswith(".pdf"):
        return extract_pdf(file_path)
    elif file_path.lower().endswith(".epub"):
        return extract_epub(file_path)
    else:
        raise ValueError(f"Unsupported file type: {file_path}")
