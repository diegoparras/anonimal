# -*- coding: utf-8 -*-
"""Detectores de PII comunes (no atados a un pais) por regex.

Precision sobre recall: preferimos no marcar de mas. Los telefonos son el caso
mas ruidoso, por eso quedan con prioridad baja (ver lite_engine.PRIORITY) y los
identificadores especificos (CBU/CUIT/tarjeta) les ganan en caso de solape.
"""
from __future__ import annotations

import re

from .base import Span

EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")
URL_RE = re.compile(r"\b(?:https?://|www\.)[^\s<>()\[\]{}\"']+", re.I)
IPV4_RE = re.compile(
    r"\b(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)\b"
)
# Telefono: al menos un separador o un prefijo +; 7+ digitos en total.
PHONE_RE = re.compile(
    r"(?<![\w.])(?:\+?\d{1,3}[ .\-]?)?(?:\(\d{1,4}\)[ .\-]?)?\d{2,4}(?:[ .\-]\d{2,4}){1,4}(?![\w])"
)
# Tarjeta: 13-19 digitos con espacios/guiones opcionales (se valida con Luhn).
CC_RE = re.compile(r"(?<!\d)(?:\d[ \-]?){13,19}(?!\d)")

SECRET_RES = [
    re.compile(r"\b(?:sk|pk|rk)-[A-Za-z0-9]{16,}\b"),       # OpenAI/Stripe-like
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),                      # AWS access key id
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),           # GitHub token
    re.compile(r"\bxox[baprs]-[A-Za-z0-9\-]{10,}\b"),        # Slack token
]


def _luhn_ok(s: str) -> bool:
    digits = [int(c) for c in s if c.isdigit()]
    if len(digits) < 13:
        return False
    total = 0
    for i, d in enumerate(reversed(digits)):
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def detect(text: str) -> list[Span]:
    spans: list[Span] = []

    for m in EMAIL_RE.finditer(text):
        spans.append(Span("EMAIL", m.start(), m.end(), m.group()))
    for m in URL_RE.finditer(text):
        spans.append(Span("URL", m.start(), m.end(), m.group()))
    for m in IPV4_RE.finditer(text):
        spans.append(Span("IPV4", m.start(), m.end(), m.group()))
    for rx in SECRET_RES:
        for m in rx.finditer(text):
            spans.append(Span("SECRET", m.start(), m.end(), m.group()))
    for m in CC_RE.finditer(text):
        if _luhn_ok(m.group()):
            spans.append(Span("CREDIT_CARD", m.start(), m.end(), m.group()))
    for m in PHONE_RE.finditer(text):
        # un telefono "de verdad" tiene 7+ digitos
        if sum(c.isdigit() for c in m.group()) >= 7:
            spans.append(Span("PHONE", m.start(), m.end(), m.group()))

    return spans
