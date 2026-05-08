from __future__ import annotations

from pathlib import Path

import pdfplumber


def extract_pdf_text(path: Path) -> str:
    """Extract plain text from a text-based PDF.

    Returns an empty string if the file contains no extractable text
    (image-only PDF). Raises OSError / pdfplumber exceptions for corrupt files.
    """
    pages: list[str] = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                pages.append(text)
    return "\n\n".join(pages)
