import fitz  # PyMuPDF
import docx
import os


def _read_pdf(path: str) -> str:
    text = ""
    with fitz.open(path) as doc:
        for page in doc:
            text += page.get_text()
    return text


def _read_docx(path: str) -> str:
    d = docx.Document(path)
    return "\n".join(p.text for p in d.paragraphs)


def _read_txt(path: str) -> str:
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        return f.read()


def extract_text_from_file(file_path: str) -> str:
    """
    Extracts text from .pdf, .docx, or .txt. Returns empty string for unsupported types.
    """
    _, ext = os.path.splitext(file_path.lower())
    if ext == '.pdf':
        return _read_pdf(file_path)
    elif ext == '.docx':
        return _read_docx(file_path)
    elif ext == '.txt':
        return _read_txt(file_path)
    else:
        return ""
