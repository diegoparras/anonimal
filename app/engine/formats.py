# -*- coding: utf-8 -*-
"""Anonimizacion que PRESERVA EL FORMATO de archivos que ya son texto.

Un CSV vuelve CSV con las columnas intactas y solo los datos PII enmascarados;
un JSON vuelve JSON valido (se tocan los valores string, nunca las claves). El
resto (txt/md/log/srt/html) se trata como texto plano: como solo reemplazamos
las subcadenas PII, la estructura se mantiene sola.

Todas las funciones reciben un unico `Anonymizer` por archivo, asi la
consistencia (mismo valor -> mismo reemplazo) y el mapa de reversion valen para
todo el documento.
"""
from __future__ import annotations

import csv
import io
import json

from .modes import Anonymizer


def _anon(text: str, engine, anonymizer: Anonymizer) -> str:
    if not text or not text.strip():
        return text
    return anonymizer.process(text, engine.detect(text))


def anonymize_text(content: str, engine, anonymizer: Anonymizer) -> str:
    return _anon(content, engine, anonymizer)


def anonymize_csv(content: str, engine, anonymizer: Anonymizer) -> str:
    reader = csv.reader(io.StringIO(content))
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    for row in reader:
        writer.writerow([_anon(cell, engine, anonymizer) for cell in row])
    return out.getvalue()


def anonymize_json(content: str, engine, anonymizer: Anonymizer) -> str:
    data = json.loads(content)

    def walk(node):
        if isinstance(node, str):
            return _anon(node, engine, anonymizer)
        if isinstance(node, list):
            return [walk(x) for x in node]
        if isinstance(node, dict):
            return {k: walk(v) for k, v in node.items()}
        return node

    return json.dumps(walk(data), ensure_ascii=False, indent=2)


_HANDLERS = {
    "txt": anonymize_text, "md": anonymize_text, "log": anonymize_text,
    "srt": anonymize_text, "html": anonymize_text, "htm": anonymize_text,
    "csv": anonymize_csv,
    "json": anonymize_json,
}

SUPPORTED = tuple(_HANDLERS.keys())


def detect_format(filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return ext if ext in _HANDLERS else "txt"


def anonymize_file(filename: str, content: str, engine, anonymizer: Anonymizer) -> tuple[str, str]:
    """Devuelve (formato_detectado, contenido_anonimizado)."""
    fmt = detect_format(filename)
    return fmt, _HANDLERS[fmt](content, engine, anonymizer)
