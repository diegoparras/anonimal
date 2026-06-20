"""Redacción visual de PDF: tacha los datos personales con una caja opaca
(redacción REAL, no un dibujo encima) y borra la metadata.

Usa PyMuPDF (fitz). El motor detecta el PII en el texto de cada página; acá solo
ubicamos esas cadenas en la página y las tapamos. `apply_redactions()` elimina
de verdad el texto subyacente, no solo lo oculta.

PyMuPDF es opcional: si no está instalado, `redact_pdf_bytes` levanta
RuntimeError y la API responde 503.
"""
from __future__ import annotations

import contextlib


def is_available() -> bool:
    import importlib.util
    return importlib.util.find_spec("fitz") is not None


def redact_pdf_bytes(data: bytes, engine) -> tuple[bytes, int]:
    """Devuelve (pdf_redactado, cantidad_de_tachados)."""
    try:
        import fitz
    except ImportError as e:  # pragma: no cover
        raise RuntimeError("PyMuPDF (fitz) no está instalado.") from e

    doc = fitz.open(stream=data, filetype="pdf")
    try:
        total = 0
        for page in doc:
            spans = engine.detect(page.get_text())
            values = {s.text for s in spans if s.text.strip()}
            for value in values:
                for rect in page.search_for(value):
                    page.add_redact_annot(rect, fill=(0, 0, 0))
                    total += 1
            if total:
                page.apply_redactions()
        # borrar metadata (DocInfo + XMP)
        doc.set_metadata({})
        with contextlib.suppress(Exception):
            doc.del_xml_metadata()
        out = doc.tobytes(deflate=True, garbage=4)
        return out, total
    finally:
        doc.close()
