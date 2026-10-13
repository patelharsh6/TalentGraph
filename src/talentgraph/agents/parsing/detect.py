"""Step 2.2: file type detection by magic bytes, plus size and page limits (plan §6.1 step 1).

The file name and the client's content type are never trusted: `%PDF` is a PDF, a ZIP holding
`word/document.xml` is a DOCX, and anything else that decodes as text is TXT. Known binary
formats (images, other archives, legacy .doc) are rejected with `UnsupportedFileType`.
"""

import io
import zipfile

from talentgraph.core.errors import FileTooLarge, UnsupportedFileType
from talentgraph.core.schemas.resume import FileKind

# Leading bytes of formats people commonly upload by mistake.
_BINARY_SIGNATURES: dict[bytes, str] = {
    b"\x89PNG\r\n\x1a\n": "PNG image",
    b"\xff\xd8\xff": "JPEG image",
    b"GIF87a": "GIF image",
    b"GIF89a": "GIF image",
    b"II*\x00": "TIFF image",
    b"MM\x00*": "TIFF image",
    b"RIFF": "RIFF container (e.g. WebP)",
    b"\xd0\xcf\x11\xe0": "legacy Office file (.doc); save it as .docx or PDF",
    b"{\\rtf": "RTF document",
    b"\x1f\x8b": "gzip archive",
    b"7z\xbc\xaf": "7z archive",
    b"Rar!": "RAR archive",
}


def check_size(data: bytes, max_mb: int) -> None:
    if len(data) > max_mb * 1024 * 1024:
        raise FileTooLarge(f"The file is {len(data) / 1_048_576:.1f} MB; the limit is {max_mb} MB.")


def detect_file_type(data: bytes) -> FileKind:
    if not data.strip():
        raise UnsupportedFileType("The file is empty.")
    head = data[:1024]
    if head.lstrip(b"\x00\t\r\n ").startswith(b"%PDF"):
        return "pdf"
    if data.startswith(b"PK\x03\x04"):
        return _zip_kind(data)
    for signature, label in _BINARY_SIGNATURES.items():
        if data.startswith(signature):
            raise UnsupportedFileType(f"Detected a {label}. Upload a PDF, DOCX or TXT resume.")
    if _looks_like_text(data):
        return "txt"
    raise UnsupportedFileType("Unrecognized binary file. Upload a PDF, DOCX or TXT resume.")


def _zip_kind(data: bytes) -> FileKind:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            names = set(zf.namelist())
    except zipfile.BadZipFile as exc:
        raise UnsupportedFileType("The file looks like a ZIP archive but is corrupt.") from exc
    if "word/document.xml" in names:
        return "docx"
    raise UnsupportedFileType("ZIP archives other than DOCX are not supported.")


def _looks_like_text(data: bytes) -> bool:
    """UTF-8/UTF-16 with a BOM, or mostly printable bytes with no NULs."""
    if data.startswith((b"\xef\xbb\xbf", b"\xff\xfe", b"\xfe\xff")):
        return True
    sample = data[:4096]
    if b"\x00" in sample:
        return False
    printable = sum(1 for byte in sample if byte >= 0x20 or byte in b"\t\r\n\f")
    return printable / len(sample) > 0.95
