"""Registro de motores de Anonimal.

- `lite`  : siempre disponible (solo regex).
- `ml`    : OPF, solo si la libreria `opf` esta instalada.

`get_engine(name)` devuelve una instancia (singleton) o None si no esta
disponible. El motor ML arranca su carga en background la primera vez que se lo
pide, para no bloquear el server.
"""
from __future__ import annotations

from . import formats, modes
from .base import Span, apply_replacements, resolve_overlaps
from .lite_engine import LiteEngine

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


__all__ = [
    "LiteEngine",
    "Span",
    "apply_replacements",
    "formats",
    "get_engine",
    "lite_engine",
    "modes",
    "resolve_overlaps",
]
