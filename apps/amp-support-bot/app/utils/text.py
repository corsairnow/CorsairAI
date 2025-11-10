import re, hashlib
from typing import List, Dict
import fitz
from docx import Document
import os

HEADER_RE = re.compile(r'^(#{1,6})\s+(.*)', re.M)

def slugify(text: str) -> str:
    """
    Keep the folder name as the KB id with minimal, predictable normalization:
    - lowercase
    - trim spaces
    - replace INTERNAL spaces with '-' (spaces aren’t great for paths)
    - DO NOT change underscores or hyphens
    - validate only [a-z0-9-_], raise if others present
    """
    t = (text or "").strip().lower().replace(" ", "-")
    if not re.fullmatch(r"[a-z0-9\-_]+", t):
        raise ValueError(f"Invalid KB folder name '{text}'. Use only letters/numbers, '-' or '_'.")
    return t

def slugify_filename(filename: str) -> str:
    """
    Slugify the base filename (without extension)
    """
    base_name = os.path.splitext(os.path.basename(filename))[0]  # remove path and extension
    return slugify(base_name)

def read_markdown(path: str) -> str:
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        return f.read()

def normalize_markdown(md: str) -> str:
    md = md.replace('\r\n', '\n').replace('\r', '\n')
    md = md.lstrip('\ufeff')
    md = re.sub(r'\n{3,}', '\n\n', md)
    return md.strip()

def split_heading_aware(md: str, max_chars: int, overlap: int) -> List[Dict]:
    matches = list(HEADER_RE.finditer(md))
    pairs = []
    if matches:
        for idx, m in enumerate(matches):
            start = m.end()
            end = matches[idx+1].start() if idx+1 < len(matches) else len(md)
            heading = (m.group(2) or "").strip()
            body = md[start:end].strip()
            if body:
                pairs.append((heading or "section", body))
    else:
        text = md.strip()
        if text:
            pairs = [("document", text)]

    chunks: List[Dict] = []
    for heading, body in pairs:
        if len(body) <= max_chars:
            chunks.append({"title": heading, "text": body})
            continue
        start = 0
        while start < len(body):
            end = min(len(body), start + max_chars)
            chunk = body[start:end].strip()
            if chunk:
                chunks.append({"title": heading, "text": chunk})
            if end >= len(body): break
            start = max(0, end - overlap)
    return chunks

def file_digest(path: str) -> str:
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(8192), b''):
            h.update(b)
    return h.hexdigest()

def read_pdf(file_path: str) -> str:
    """Extract text from PDF using PyMuPDF."""
    text = ""
    with fitz.open(file_path) as pdf:
        for page in pdf:
            text += page.get_text("text") + "\n"
    return text.strip()

def read_docx(file_path: str) -> str:
    """Extract text from DOCX using python-docx."""
    doc = Document(file_path)
    return "\n".join([p.text for p in doc.paragraphs if p.text.strip()])













