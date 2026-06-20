"""Reglas propias del usuario sobre los spans detectados:

- `always`: términos que SIEMPRE ocultar (p. ej. el nombre clave de un proyecto),
  aunque el motor no los marque. Se agregan como spans `CUSTOM` (literal,
  case-insensitive).
- `never`: términos que NUNCA ocultar (p. ej. una marca pública). Se quitan de los
  spans detectados.

Se envuelve un motor existente sin tocarlo (`RuledEngine`), así sirve igual para
texto y para archivos (formats.py usa cualquier objeto con `.detect`).
"""
from __future__ import annotations

import re

from .base import Span, resolve_overlaps
from .lite_engine import PRIORITY

_CUSTOM_PRIORITY = {**PRIORITY, "CUSTOM": 100}  # lo del usuario gana siempre


def merge(text: str, spans: list[Span], always: list[str], never: list[str]) -> list[Span]:
    never_set = {n.strip().lower() for n in never if n.strip()}
    kept = [s for s in spans if s.text.lower() not in never_set]
    for term in always:
        t = term.strip()
        if not t:
            continue
        for m in re.finditer(re.escape(t), text, re.IGNORECASE):
            kept.append(Span("CUSTOM", m.start(), m.end(), m.group()))
    return resolve_overlaps(kept, _CUSTOM_PRIORITY)


class RuledEngine:
    """Envuelve un motor y le aplica las reglas del usuario en cada `detect`."""

    def __init__(self, engine, always: list[str] | None = None,
                 never: list[str] | None = None):
        self._engine = engine
        self.always = always or []
        self.never = never or []

    @property
    def name(self) -> str:
        return getattr(self._engine, "name", "lite")

    def ready(self) -> bool:
        return self._engine.ready()

    def detect(self, text: str) -> list[Span]:
        return merge(text, self._engine.detect(text), self.always, self.never)
