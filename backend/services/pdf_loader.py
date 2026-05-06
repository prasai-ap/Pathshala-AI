"""PDF text extraction service."""

import base64
from dataclasses import dataclass
import logging

import requests

import fitz

from backend.services.config import get_config


LOGGER = logging.getLogger(__name__)
MIN_TEXT_CHARACTERS_FOR_DIRECT_EXTRACTION = 300


class PDFExtractionError(ValueError):
    """Raised when uploaded PDF content cannot be read."""


@dataclass(frozen=True)
class PDFText:
    text: str
    page_count: int
    extraction_method: str = "pymupdf"


def extract_pdf_text(pdf_bytes: bytes) -> PDFText:
    if not pdf_bytes:
        raise PDFExtractionError("Uploaded PDF is empty.")

    try:
        with fitz.open(stream=pdf_bytes, filetype="pdf") as document:
            if document.page_count == 0:
                raise PDFExtractionError("Uploaded PDF has no pages.")

            pages = [page.get_text("text").strip() for page in document]
            text = "\n\n".join(page_text for page_text in pages if page_text)

            if len(text.strip()) >= MIN_TEXT_CHARACTERS_FOR_DIRECT_EXTRACTION:
                return PDFText(
                    text=text,
                    page_count=document.page_count,
                    extraction_method="pymupdf",
                )

            ocr_text = extract_text_with_gemini_ocr(document)

            if ocr_text:
                combined_text = "\n\n".join(part for part in [text, ocr_text] if part.strip())
                return PDFText(
                    text=combined_text,
                    page_count=document.page_count,
                    extraction_method="gemini-ocr",
                )

            if text.strip():
                return PDFText(
                    text=text,
                    page_count=document.page_count,
                    extraction_method="pymupdf-low-text",
                )

            raise PDFExtractionError(
                "No readable text found in the PDF. If this is a scanned textbook, "
                "set OCR_PROVIDER=gemini and GEMINI_API_KEY in .env."
            )
    except PDFExtractionError:
        raise
    except Exception as exc:
        raise PDFExtractionError("Invalid or unreadable PDF file.") from exc


def extract_text_with_gemini_ocr(document: fitz.Document) -> str:
    config = get_config()

    if config.ocr_provider != "gemini" or not config.gemini_api_key:
        return ""

    page_texts = []
    page_limit = document.page_count

    if config.ocr_max_pages > 0:
        page_limit = min(document.page_count, config.ocr_max_pages)

    for page_index in range(page_limit):
        try:
            page = document.load_page(page_index)
            png_bytes = render_page_to_png(page)
            page_text = ocr_page_with_gemini(
                png_bytes=png_bytes,
                page_number=page_index + 1,
            )
        except requests.RequestException as exc:
            LOGGER.warning("Gemini OCR failed on page %s: %s", page_index + 1, exc)
            continue
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            LOGGER.warning("Gemini OCR returned invalid page %s response: %s", page_index + 1, exc)
            continue

        if page_text:
            page_texts.append(page_text)

    return "\n\n".join(page_texts).strip()


def render_page_to_png(page: fitz.Page) -> bytes:
    pixmap = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False)
    return pixmap.tobytes("png")


def ocr_page_with_gemini(png_bytes: bytes, page_number: int) -> str:
    config = get_config()
    endpoint = (
        "https://generativelanguage.googleapis.com/v1beta/"
        f"models/{config.gemini_model}:generateContent"
    )
    image_data = base64.b64encode(png_bytes).decode("ascii")
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": (
                            "Extract all readable textbook text from this page. The text may "
                            "be in Nepali Devanagari or English. Return plain text only. "
                            "Preserve headings and important lesson content. Do not summarize."
                        )
                    },
                    {
                        "inline_data": {
                            "mime_type": "image/png",
                            "data": image_data,
                        }
                    },
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0,
            "maxOutputTokens": 1800,
        },
    }
    response = requests.post(
        endpoint,
        json=payload,
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": config.gemini_api_key,
        },
        timeout=45,
    )
    response.raise_for_status()
    data = response.json()
    text = data["candidates"][0]["content"]["parts"][0]["text"].strip()

    if not text or "cannot" in text.lower() and "extract" in text.lower():
        return ""

    return f"Page {page_number}\n{text}"
