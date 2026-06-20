# -*- coding: utf-8 -*-
"""Tipos y utilidades compartidas por los motores de Anonimal.

Un motor (`Engine`) solo DETECTA: recibe texto y devuelve `Span`s (etiqueta +
offsets). El reemplazo (los 5 modos, la reversibilidad) lo decide `modes.py`.
Este contrato "detecta, no decide" es el mismo que el microservicio original.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Span:
    """Un dato personal detectado en el texto."""
    label: str   # categoria: EMAIL, PERSON, AR_DNI, AR_CUIT, ...
    start: int   # offset inicial (inclusive)
    end: int     # offset final (exclusivo)
    text: str    # el texto detectado

    def as_dict(self) -> dict:
        return {"label": self.label, "start": self.start, "end": self.end, "text": self.text}


def resolve_overlaps(spans: list[Span], priority: dict[str, int] | None = None) -> list[Span]:
    """Quita solapamientos: gana el span mas largo; a igual largo, el de mayor
    prioridad de etiqueta; a igual prioridad, el que empieza antes. Devuelve la
    lista final ordenada por posicion."""
    priority = priority or {}

    def rank(s: Span):
        return (-(s.end - s.start), -priority.get(s.label, 0), s.start)

    chosen: list[Span] = []
    taken: list[tuple[int, int]] = []
    for s in sorted(spans, key=rank):
        if s.end <= s.start:
            continue
        if any(not (s.end <= a or s.start >= b) for a, b in taken):
            continue
        chosen.append(s)
        taken.append((s.start, s.end))
    chosen.sort(key=lambda s: s.start)
    return chosen


def apply_replacements(text: str, repls: list[tuple[int, int, str]]) -> str:
    """Aplica reemplazos (start, end, nuevo) de derecha a izquierda para no
    correr los offsets."""
    out = text
    for start, end, rep in sorted(repls, key=lambda r: r[0], reverse=True):
        out = out[:start] + rep + out[end:]
    return out
