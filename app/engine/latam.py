"""Detectores de PII de LATAM (foco Argentina) que el modelo generico no cubre
bien: DNI, CUIT/CUIL, CBU. Donde es posible se valida el digito verificador para
bajar los falsos positivos.
"""
from __future__ import annotations

import re

from .base import Span

# CUIT/CUIL: XX-XXXXXXXX-X (separadores opcionales). Se valida modulo 11.
CUIT_RE = re.compile(r"(?<!\d)(\d{2})[ \-]?(\d{8})[ \-]?(\d)(?!\d)")
# CBU: 22 digitos exactos.
CBU_RE = re.compile(r"(?<!\d)\d{22}(?!\d)")
# DNI con puntos de miles: 12.345.678 (o 1.234.567).
DNI_DOTTED_RE = re.compile(r"(?<!\d)\d{1,2}\.\d{3}\.\d{3}(?!\d)")
# DNI por contexto: "DNI 12345678" / "documento: 12.345.678".
DNI_CTX_RE = re.compile(
    r"(?i)\b(?:dni|d\.n\.i\.?|documento)\b[\s:n°º\-]*((?:\d{1,2}\.?\d{3}\.?\d{3})|\d{7,8})"
)


def _cuit_ok(d11: str) -> bool:
    nums = [int(c) for c in d11]
    if len(nums) != 11:
        return False
    weights = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]
    total = sum(w * n for w, n in zip(weights, nums[:10], strict=True))
    chk = 11 - (total % 11)
    chk = 0 if chk == 11 else (9 if chk == 10 else chk)
    return chk == nums[10]


def detect(text: str) -> list[Span]:
    spans: list[Span] = []

    for m in CUIT_RE.finditer(text):
        raw = m.group(1) + m.group(2) + m.group(3)
        if _cuit_ok(raw):
            spans.append(Span("AR_CUIT", m.start(), m.end(), m.group()))
    for m in CBU_RE.finditer(text):
        spans.append(Span("AR_CBU", m.start(), m.end(), m.group()))
    for m in DNI_DOTTED_RE.finditer(text):
        spans.append(Span("AR_DNI", m.start(), m.end(), m.group()))
    for m in DNI_CTX_RE.finditer(text):
        # marcamos solo el numero (grupo 1), no la palabra "DNI"
        spans.append(Span("AR_DNI", m.start(1), m.end(1), m.group(1)))

    return spans
