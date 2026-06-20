"""Motor "lite": solo regex, sin modelo de ML. Liviano (megabytes), instalable
en cualquier lado, offline. Menos preciso que el motor ML para nombres/direcciones
(no los detecta), pero solido para datos estructurados (mail, telefono, tarjeta,
DNI, CUIT, CBU, secrets).
"""
from __future__ import annotations

from . import common, latam
from .base import Span, finalize

# A mayor numero, mas prioridad cuando dos detecciones se solapan.
PRIORITY = {
    "AR_CBU": 60,
    "AR_CUIT": 55,
    "SECRET": 50,  # nosec B105 - peso de prioridad de deteccion, no una credencial
    "AR_DNI": 45,
    "CREDIT_CARD": 40,
    "EMAIL": 35,
    "IPV4": 25,
    "URL": 20,
    "PHONE": 10,
}


class LiteEngine:
    name = "lite"

    def ready(self) -> bool:
        return True

    def detect(self, text: str) -> list[Span]:
        spans = common.detect(text) + latam.detect(text)
        return finalize(text, spans, PRIORITY)
