"""Tipos y utilidades compartidas por los motores de Anonimal.

Un motor (`Engine`) solo DETECTA: recibe texto y devuelve `Span`s (etiqueta +
offsets). El reemplazo (los 5 modos, la reversibilidad) lo decide `modes.py`.
Este contrato "detecta, no decide" es el mismo que el microservicio original.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

_DEHYPHEN_RE = re.compile(r"-[ \t]*\n[ \t]*")


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


def normalize(text: str) -> str:
    """Une cortes de línea con guion de PDF ("27-\\n3178" -> "27-3178") para que
    un salto de línea no parta un CUIT, un email o un identificador."""
    return _DEHYPHEN_RE.sub("-", text)


def propagate(text: str, spans: list[Span]) -> list[Span]:
    """Si un valor ya fue marcado como PII, lo marca en TODAS sus apariciones.
    Sube el recall (un nombre detectado en un lugar y no en otro). Guard de
    longitud (>=4) para no propagar fragmentos triviales."""
    extra: list[Span] = []
    seen: set[str] = set()
    for s in spans:
        frag = s.text
        if len(frag.strip()) < 4 or frag in seen:
            continue
        seen.add(frag)
        i = text.find(frag)
        while i >= 0:
            extra.append(Span(s.label, i, i + len(frag), frag))
            i = text.find(frag, i + len(frag))
    return spans + extra


def finalize(text: str, spans: list[Span], priority: dict[str, int] | None = None) -> list[Span]:
    """Propaga y resuelve solapamientos. Punto único de cierre del pipeline de
    detección (lo usan los motores y las reglas)."""
    return resolve_overlaps(propagate(text, spans), priority)
