"""PDF text extraction service."""

import base64
from dataclasses import dataclass
import logging
from threading import Lock
import time

import requests

import fitz

from backend.services.config import get_config


LOGGER = logging.getLogger(__name__)
MIN_TEXT_CHARACTERS_FOR_DIRECT_EXTRACTION = 300
OCR_PAGE_DELAY_SECONDS = 6
OCR_RETRY_DELAYS_SECONDS = [20, 60, 120]
OCR_LOCK = Lock()


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

            if (
                len(text.strip()) >= MIN_TEXT_CHARACTERS_FOR_DIRECT_EXTRACTION
                and not is_garbled_pdf_text(text)
            ):
                return PDFText(
                    text=text,
                    page_count=document.page_count,
                    extraction_method="pymupdf",
                )

            ocr_text = extract_text_with_gemini_ocr(document)

            if ocr_text:
                combined_text = (
                    ocr_text
                    if is_garbled_pdf_text(text)
                    else "\n\n".join(part for part in [text, ocr_text] if part.strip())
                )
                return PDFText(
                    text=combined_text,
                    page_count=document.page_count,
                    extraction_method="gemini-ocr",
                )

            if is_garbled_pdf_text(text):
                raise PDFExtractionError(
                    "The PDF text layer is not readable Unicode Nepali. This often "
                    "happens with custom-font Nepali PDFs. Enable OCR_PROVIDER=gemini "
                    "with GEMINI_API_KEY, or upload a Unicode text PDF."
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

    with OCR_LOCK:
        LOGGER.info("Starting Gemini OCR for %s page(s). This can take several minutes.", page_limit)

        for page_index in range(page_limit):
            page_number = page_index + 1

            try:
                page = document.load_page(page_index)
                png_bytes = render_page_to_png(page)
                page_text = ocr_page_with_retries(
                    png_bytes=png_bytes,
                    page_number=page_number,
                )
            except requests.RequestException as exc:
                LOGGER.warning("Gemini OCR failed on page %s after retries: %s", page_number, exc)
                continue
            except (KeyError, IndexError, TypeError, ValueError) as exc:
                LOGGER.warning("Gemini OCR returned invalid page %s response: %s", page_number, exc)
                continue

            if page_text:
                page_texts.append(page_text)
                LOGGER.info("Gemini OCR completed page %s/%s", page_number, page_limit)

            time.sleep(OCR_PAGE_DELAY_SECONDS)

    return "\n\n".join(page_texts).strip()


def ocr_page_with_retries(png_bytes: bytes, page_number: int) -> str:
    last_error: requests.RequestException | None = None

    for attempt_index, delay_seconds in enumerate([0, *OCR_RETRY_DELAYS_SECONDS], start=1):
        if delay_seconds:
            LOGGER.info(
                "Waiting %s seconds before Gemini OCR retry %s for page %s.",
                delay_seconds,
                attempt_index - 1,
                page_number,
            )
            time.sleep(delay_seconds)

        try:
            return ocr_page_with_gemini(
                png_bytes=png_bytes,
                page_number=page_number,
            )
        except requests.HTTPError as exc:
            last_error = exc
            status_code = exc.response.status_code if exc.response is not None else None

            if status_code == 429:
                retry_after = retry_after_seconds(exc.response)
                if retry_after:
                    LOGGER.warning(
                        "Gemini OCR rate limit on page %s. Waiting Retry-After=%s seconds.",
                        page_number,
                        retry_after,
                    )
                    time.sleep(retry_after)
                else:
                    LOGGER.warning(
                        "Gemini OCR rate limit on page %s. Will retry with backoff.",
                        page_number,
                    )
                continue

            if status_code in {500, 502, 503, 504}:
                LOGGER.warning(
                    "Gemini OCR temporary service error on page %s: %s",
                    page_number,
                    exc,
                )
                continue

            raise

    if last_error:
        raise last_error

    return ""


def retry_after_seconds(response: requests.Response | None) -> int:
    if response is None:
        return 0

    raw_value = response.headers.get("Retry-After", "").strip()

    if not raw_value:
        return 0

    try:
        return max(int(raw_value), 0)
    except ValueError:
        return 0


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
                            "Preserve the original language and script exactly as much as "
                            "possible. Do not translate Nepali text into English. Preserve "
                            "headings and important lesson content. Do not summarize."
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


def is_garbled_pdf_text(text: str) -> bool:
    cleaned = "".join(character for character in text if not character.isspace())

    if len(cleaned) < MIN_TEXT_CHARACTERS_FOR_DIRECT_EXTRACTION:
        return False

    devanagari_count = sum(1 for character in cleaned if "\u0900" <= character <= "\u097f")
    ascii_letter_count = sum(1 for character in cleaned if character.isascii() and character.isalpha())
    suspicious_symbol_count = sum(1 for character in cleaned if character in "/\\|;:{}[]'\"`~")
    suspicious_markers = ["kf7", "lj", "cfwf", "tsnf", ";sf", "PsF", "ofsf"]
    marker_hits = sum(1 for marker in suspicious_markers if marker in text)

    devanagari_ratio = devanagari_count / len(cleaned)
    symbol_ratio = suspicious_symbol_count / len(cleaned)
    ascii_ratio = ascii_letter_count / len(cleaned)

    return (
        devanagari_ratio < 0.05
        and ascii_ratio > 0.35
        and (symbol_ratio > 0.12 or marker_hits >= 2)
    )
