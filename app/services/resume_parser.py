
import pdfplumber
from docx import Document


def extract_resume_text(file_path):
    """Extract readable text from a PDF or DOCX resume."""

    extension = file_path.rsplit(".", 1)[-1].lower()
    extracted_text = ""

    if extension == "pdf":
        with pdfplumber.open(file_path) as pdf:
            pages = []

            for page in pdf.pages:
                pages.append(page.extract_text() or "")

            extracted_text = "\n".join(pages)

    elif extension == "docx":
        document = Document(file_path)

        paragraphs = [
            paragraph.text
            for paragraph in document.paragraphs
            if paragraph.text.strip()
        ]

        extracted_text = "\n".join(paragraphs)

    else:
        raise ValueError("Only PDF and DOCX files are supported.")

    if not extracted_text.strip():
        raise ValueError(
            "No readable text found. The resume may be scanned "
            "or image-based and may require OCR."
        )

    return extracted_text
