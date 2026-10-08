import os
import shutil

try:
    import fitz
except ImportError:
    try:
        import pymupdf as fitz
    except ImportError as exc:
        raise ImportError(
            "PyMuPDF is not installed. Run: pip install pymupdf"
        ) from exc

try:
    import pytesseract
except ImportError as exc:
    raise ImportError(
        "pytesseract is not installed. Run: pip install pytesseract"
    ) from exc

from PIL import Image


def extract_pdf_text(file_path):
    if not file_path:
        print("file_path is required.")
        return ""

    if not os.path.exists(file_path):
        print(f"PDF file not found: {file_path}")
        return ""

    text_parts = []
    document = None

    try:
        document = fitz.open(file_path)

        for page in document:
            # First try normal PDF text extraction.
            page_text = page.get_text("text").strip()
            if page_text:
                text_parts.append(page_text)
                continue

            # If there is no text layer, render the page and use OCR.
            if shutil.which("tesseract") is None:
                print(
                    "Tesseract is not installed or not on PATH. "
                    "Install Tesseract OCR to extract text from scanned PDFs."
                )
                continue

            pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            image = Image.frombytes(
                "RGB",
                [pixmap.width, pixmap.height],
                pixmap.samples,
            )

            ocr_text = pytesseract.image_to_string(image, lang="eng").strip()
            if ocr_text:
                text_parts.append(ocr_text)

        return "\n\n".join(text_parts)

    except Exception as error:
        print(f"PDF extraction error: {error}")
        return ""
    finally:
        if document is not None:
            document.close()