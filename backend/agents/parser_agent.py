"""
Agent 1: Document Parser
Extracts raw text from PDF, CSV, XLSX, DOCX, HTML, TXT files.
"""
from __future__ import annotations
import os
import mimetypes
from pathlib import Path


def parse_file(file_path: str) -> dict:
    """
    Route file to appropriate extractor.
    Returns: {doc_id, source_file, raw_text, page_count, extraction_confidence, file_type, file_size_kb}
    """
    path = Path(file_path)
    ext = path.suffix.lower()
    size_kb = path.stat().st_size / 1024

    result = {
        "source_file": path.name,
        "file_type": ext.lstrip("."),
        "file_size_kb": round(size_kb, 1),
        "raw_text": "",
        "page_count": 1,
        "extraction_confidence": 0.0,
    }

    try:
        if ext == ".pdf":
            result.update(_parse_pdf(file_path))
        elif ext in (".csv",):
            result.update(_parse_csv(file_path))
        elif ext in (".xlsx", ".xls"):
            result.update(_parse_excel(file_path))
        elif ext in (".docx",):
            result.update(_parse_docx(file_path))
        elif ext in (".html", ".htm"):
            result.update(_parse_html(file_path))
        elif ext == ".txt":
            result.update(_parse_txt(file_path))
        else:
            result.update(_parse_txt(file_path))  # fallback
    except Exception as e:
        result["error"] = str(e)
        result["extraction_confidence"] = 0.0

    return result


def _parse_pdf(path: str) -> dict:
    """Try pdfplumber first, fall back to PyMuPDF for scanned docs."""
    try:
        import pdfplumber
        with pdfplumber.open(path) as pdf:
            pages = []
            for page in pdf.pages:
                text = page.extract_text() or ""
                pages.append(text)
            raw = "\n\n".join(pages)
            if len(raw.strip()) < 100:
                raise ValueError("Low text yield — trying PyMuPDF")
            return {
                "raw_text": raw,
                "page_count": len(pdf.pages),
                "extraction_confidence": min(1.0, len(raw) / 1000),
            }
    except Exception:
        pass

    # Fallback: PyMuPDF
    import fitz
    doc = fitz.open(path)
    pages = [page.get_text() for page in doc]
    raw = "\n\n".join(pages)
    return {
        "raw_text": raw,
        "page_count": len(pages),
        "extraction_confidence": min(0.9, len(raw) / 1000),
    }


def _parse_csv(path: str) -> dict:
    import pandas as pd
    df = pd.read_csv(path, dtype=str, encoding="utf-8", errors="replace")
    raw = df.to_string(index=False)
    return {"raw_text": raw, "extraction_confidence": 0.85}


def _parse_excel(path: str) -> dict:
    import pandas as pd
    sheets = pd.read_excel(path, sheet_name=None, dtype=str)
    parts = [f"=== Sheet: {name} ===\n{df.to_string(index=False)}" for name, df in sheets.items()]
    return {"raw_text": "\n\n".join(parts), "extraction_confidence": 0.85}


def _parse_docx(path: str) -> dict:
    from docx import Document
    doc = Document(path)
    paras = [p.text for p in doc.paragraphs if p.text.strip()]
    return {"raw_text": "\n".join(paras), "extraction_confidence": 0.9}


def _parse_html(path: str) -> dict:
    from bs4 import BeautifulSoup
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        soup = BeautifulSoup(f.read(), "lxml")
    raw = soup.get_text(separator="\n")
    return {"raw_text": raw, "extraction_confidence": 0.8}


def _parse_txt(path: str) -> dict:
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        raw = f.read()
    return {"raw_text": raw, "extraction_confidence": 0.95}
