"""Selección de motor del SERVICIO (no de la librería).

- `lite`: siempre disponible (regex), viene de `anonimal_lite`.
- `ml`: OPF, solo si la librería `opf` está instalada (imagen full).

La librería `anonimal_lite` no conoce el motor ML a propósito: el ML es del
servidor. Acá se combinan.
"""
from __future__ import annotations

from anonimal_lite import LiteEngine

_lite = LiteEngine()
_ml = None
_ml_tried = False


def get_engine(name: str):
    global _ml, _ml_tried
    if name == "lite":
        return _lite
    if name == "ml":
        if not _ml_tried:
            _ml_tried = True
            from . import opf_engine
            if opf_engine.is_available():
                _ml = opf_engine.OpfEngine()
                _ml.start_background_load()
        return _ml
    return None


def lite_engine() -> LiteEngine:
    return _lite
