"""Redacción visual de PDF (PyMuPDF): el PII desaparece del texto extraíble y la
metadata se borra. SKIP si fitz no está instalado."""
import importlib.util

from anonimal_lite.lite_engine import LiteEngine
from app.pdf import redact_pdf_bytes

HAVE_FITZ = importlib.util.find_spec("fitz") is not None


def _make_pdf(text: str) -> bytes:
    import fitz
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 100), text, fontsize=12)
    doc.set_metadata({"author": "Juan Perez", "title": "secreto"})
    data = doc.tobytes()
    doc.close()
    return data


def test_redact_pdf_quita_pii_y_metadata():
    if not HAVE_FITZ:
        return "SKIP: PyMuPDF no instalado"
    import fitz
    pdf = _make_pdf("Contacto juan@acme.com y CUIT 20-12345678-6")
    out, n = redact_pdf_bytes(pdf, LiteEngine())
    assert n >= 1
    doc = fitz.open(stream=out, filetype="pdf")
    text = "".join(p.get_text() for p in doc)
    meta = doc.metadata
    doc.close()
    assert "juan@acme.com" not in text
    assert "20-12345678-6" not in text
    assert not (meta.get("author") or meta.get("title"))
