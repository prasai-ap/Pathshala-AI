"""PDF text extraction service."""

from dataclasses import dataclass

import fitz


class PDFExtractionError(ValueError):
    """Raised when uploaded PDF content cannot be read."""


@dataclass(frozen=True)
class PDFText:
    text: str
    page_count: int


def extract_pdf_text(pdf_bytes: bytes) -> PDFText:
    if not pdf_bytes:
        raise PDFExtractionError("Uploaded PDF is empty.")

    try:
        with fitz.open(stream=pdf_bytes, filetype="pdf") as document:
            if document.page_count == 0:
                raise PDFExtractionError("Uploaded PDF has no pages.")

            pages = [page.get_text("text").strip() for page in document]
            text = "\n\n".join(page_text for page_text in pages if page_text)

            if not text.strip():
                raise PDFExtractionError("No readable text found in the PDF.")

            return PDFText(text=text, page_count=document.page_count)
    except PDFExtractionError:
        raise
    except Exception as exc:
        raise PDFExtractionError("Invalid or unreadable PDF file.") from exc
