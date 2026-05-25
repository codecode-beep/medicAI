import logging
from io import BytesIO

import pdfplumber

logger = logging.getLogger("medintel")


def extract_text_from_pdf(content: bytes) -> str:
    text_parts: list[str] = []
    try:
        with pdfplumber.open(BytesIO(content)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
    except Exception as e:
        logger.error("PDF extraction failed: %s", e)
        return ""
    return "\n\n".join(text_parts)
