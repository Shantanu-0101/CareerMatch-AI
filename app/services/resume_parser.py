"""Resume file validation, text extraction and section / skill detection."""
import os
import re
import uuid
import zipfile

from docx import Document
from pypdf import PdfReader
from werkzeug.utils import secure_filename

from ..data.skills import SECTION_HEADINGS, SKILLS, SPECIAL_C_LANGUAGE


class ResumeParseError(Exception):
    pass


ALLOWED = {"pdf", "docx"}


def validate_and_save(file_storage, upload_folder):
    """Validate an uploaded file (extension + real file signature) and store it under a random name.
    Returns (original_name, stored_name, ext)."""
    if not file_storage or not file_storage.filename:
        raise ResumeParseError("Please choose a file to upload.")
    original = secure_filename(file_storage.filename) or "resume"
    ext = original.rsplit(".", 1)[-1].lower() if "." in original else ""
    if ext not in ALLOWED:
        raise ResumeParseError("Only PDF and DOCX files are allowed.")

    head = file_storage.stream.read(8)
    file_storage.stream.seek(0)
    if ext == "pdf" and not head.startswith(b"%PDF-"):
        raise ResumeParseError("This file is not a valid PDF.")
    if ext == "docx" and not head.startswith(b"PK\x03\x04"):
        raise ResumeParseError("This file is not a valid DOCX document.")

    stored = f"{uuid.uuid4().hex}.{ext}"
    path = os.path.join(upload_folder, stored)
    file_storage.save(path)

    if ext == "docx":
        try:
            with zipfile.ZipFile(path) as z:
                if "word/document.xml" not in z.namelist():
                    raise ResumeParseError("This file is not a valid DOCX document.")
        except zipfile.BadZipFile:
            os.remove(path)
            raise ResumeParseError("This file is not a valid DOCX document.")
        except ResumeParseError:
            os.remove(path)
            raise
    return original, stored, ext


def extract_text(path, ext):
    try:
        if ext == "pdf":
            with open(path, "rb") as fh:  # close the handle so Windows can delete the file later
                reader = PdfReader(fh)
                text = "\n".join((page.extract_text() or "") for page in reader.pages[:10])
        else:
            doc = Document(path)
            parts = [p.text for p in doc.paragraphs]
            for table in doc.tables:
                for row in table.rows:
                    parts.append(" | ".join(cell.text for cell in row.cells))
            text = "\n".join(parts)
    except Exception as e:  # corrupted / encrypted files
        raise ResumeParseError("Could not read the document. It may be corrupted or password protected.") from e

    text = re.sub(r"[ \t ]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n", text).strip()
    if len(text) < 50:
        raise ResumeParseError("No readable text was found. Scanned/image-only PDFs are not supported - "
                               "please upload a text-based PDF or DOCX.")
    return text


# ---------------------------------------------------------------------- analysis helpers
def _norm_heading(line):
    return re.sub(r"[^a-z& ]", "", line.lower()).strip()


def split_sections(text):
    """Return {section_key: content} by detecting heading lines. Also handles 'Skills: Python, Java'."""
    sections = {}
    current = "header"
    sections[current] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        found = None
        rest = ""
        if len(line) <= 45:
            norm = _norm_heading(line)
            for key, aliases in SECTION_HEADINGS.items():
                if norm in aliases:
                    found = key
                    break
        if not found and ":" in line[:40]:
            head, _, rest = line.partition(":")
            norm = _norm_heading(head)
            for key, aliases in SECTION_HEADINGS.items():
                if norm in aliases:
                    found = key
                    break
        if found:
            current = found
            sections.setdefault(current, [])
            if rest.strip():
                sections[current].append(rest.strip())
        else:
            sections.setdefault(current, []).append(line)
    return {k: "\n".join(v) for k, v in sections.items()}


def _skill_patterns():
    pats = {}
    for name, aliases in SKILLS.items():
        terms = aliases or [name]
        alt = "|".join(re.escape(t) for t in terms)
        pats[name] = re.compile(r"(?<![A-Za-z0-9+#])(?:" + alt + r")(?![A-Za-z0-9+#])", re.IGNORECASE)
    return pats


_PATTERNS = _skill_patterns()
_C_PATTERN = re.compile(r"(?<![A-Za-z0-9+#/])C(?![A-Za-z0-9+#])")


def detect_skills(text):
    """Skills that literally appear in the text (no guessing)."""
    found = [name for name, pat in _PATTERNS.items() if pat.search(text)]
    # Plain "C" only counts inside a skills-like context to avoid false positives.
    for line in text.splitlines():
        if re.search(r"skill|language|technolog", line, re.IGNORECASE) or "," in line:
            if _C_PATTERN.search(line) and SPECIAL_C_LANGUAGE not in found:
                found.append(SPECIAL_C_LANGUAGE)
                break
    return found


EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE_RE = re.compile(r"(?:\+?\d{1,3}[\s-]?)?(?:\d[\s-]?){10}")


def personal_info(text, sections):
    email = EMAIL_RE.search(text)
    phone = PHONE_RE.search(text)
    linkedin = re.search(r"linkedin\.com/[\w/-]+", text, re.IGNORECASE)
    github = re.search(r"github\.com/[\w-]+", text, re.IGNORECASE)
    name = ""
    for line in sections.get("header", "").splitlines()[:3]:
        if 2 <= len(line.split()) <= 4 and re.fullmatch(r"[A-Za-z .'-]+", line):
            name = line.strip().title()
            break
    return {
        "name": name,
        "email": email.group(0) if email else "",
        "phone": phone.group(0).strip() if phone else "",
        "linkedin": linkedin.group(0) if linkedin else "",
        "github": github.group(0) if github else "",
    }
