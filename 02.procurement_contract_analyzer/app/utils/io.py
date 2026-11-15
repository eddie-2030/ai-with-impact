from io import BytesIO
from pathlib import Path
from typing import Optional
from zipfile import ZipFile

from markdown_it import MarkdownIt
from pdfminer.high_level import extract_text as pdf_extract_text
from docx import Document

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_DOCX_EXPANDED_BYTES = 50 * 1024 * 1024
MAX_DOCX_ENTRIES = 2_000
SUPPORTED_UPLOAD_TYPES = {'.pdf', '.docx', '.md', '.txt'}


class InvalidDocument(ValueError):
    """The upload cannot be read as a supported contract document."""


class UnsupportedDocument(InvalidDocument):
    """The filename has no supported document extension."""


class DocumentTooLarge(InvalidDocument):
    """The upload exceeds a file or archive limit."""


def _docx_text(source) -> str:
    return '\n'.join(paragraph.text for paragraph in Document(source).paragraphs)


def read_upload_text(content: bytes, filename: Optional[str]) -> str:
    """Validate and extract an upload without writing to a shared path."""
    extension = Path(filename or '').suffix.lower()
    if len(content) > MAX_UPLOAD_BYTES:
        raise DocumentTooLarge('Upload exceeds the 10 MiB file limit.')
    if extension not in SUPPORTED_UPLOAD_TYPES:
        raise UnsupportedDocument('Upload a PDF, DOCX, Markdown, or text file.')

    try:
        if extension == '.pdf':
            if not content.startswith(b'%PDF-') or not content.rstrip().endswith(b'%%EOF'):
                raise InvalidDocument('The upload is not a complete PDF.')
            text = pdf_extract_text(BytesIO(content))
        elif extension == '.docx':
            if not content.startswith(b'PK\x03\x04'):
                raise InvalidDocument('The upload is not a DOCX archive.')
            with ZipFile(BytesIO(content)) as archive:
                entries = archive.infolist()
                if (len(entries) > MAX_DOCX_ENTRIES
                        or sum(entry.file_size for entry in entries) > MAX_DOCX_EXPANDED_BYTES):
                    raise DocumentTooLarge('DOCX exceeds the archive expansion limit.')
            text = _docx_text(BytesIO(content))
        else:
            text = content.decode('utf-8-sig')
            if any(ord(char) < 32 and char not in '\t\r\n' for char in text):
                raise InvalidDocument('Text uploads must contain UTF-8 text.')
    except InvalidDocument:
        raise
    except Exception as exc:
        raise InvalidDocument('Could not read the uploaded document.') from exc

    if not text.strip():
        raise InvalidDocument('The document does not contain readable text.')
    return text


def read_text_any(path_or_bytes, filename: Optional[str] = None) -> str:
    """Read a trusted local file or validate and extract an uploaded document."""
    if isinstance(path_or_bytes, (bytes, bytearray)):
        return read_upload_text(path_or_bytes, filename)
    path = Path(path_or_bytes)
    extension = path.suffix.lower()
    if extension == '.pdf':
        return pdf_extract_text(str(path))
    if extension == '.docx':
        return _docx_text(str(path))
    return path.read_text(encoding='utf-8', errors='ignore')


def markdown_to_text(md: str) -> str:
    # Cheap MD → text: strip code fences, then rely on parser tokens
    md = md.replace('```', '')
    parser = MarkdownIt()
    tokens = parser.parse(md)
    lines = []
    for t in tokens:
        if t.content:
            lines.append(t.content)
    return '\n'.join(lines)
