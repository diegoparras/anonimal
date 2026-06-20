"""Los 5 modos de reemplazo + la reversibilidad.

Modos:
  typed   -> placeholder por categoria:           [EMAIL]
  anon    -> un unico token generico para todo:    «REDACTADO»
  pseudo  -> seudonimo estable y numerado:         EMAIL_1   (REVERSIBLE: guarda mapa)
  mask    -> enmascara conservando estructura:     j***@***.com / ****-****-****-1234
  hash    -> hash determinista (one-way):          EMAIL_a1b2c3d4e5

Consistencia: el mismo valor original siempre recibe el mismo reemplazo dentro
de una corrida (un `Anonymizer` por documento). Solo `pseudo` es reversible:
expone `mapping` (token -> original) para re-identificar con `deanonymize`.
"""
from __future__ import annotations

import hashlib

from .base import Span, apply_replacements

GENERIC_TOKEN = "«REDACTADO»"  # nosec B105 - token de redaccion publico, no una credencial
# Categorias numericas: se enmascaran conservando los ultimos digitos.
_NUMERIC = {"PHONE", "CREDIT_CARD", "AR_CUIT", "AR_CBU", "AR_DNI", "IPV4"}
MODES = ("typed", "anon", "pseudo", "mask", "hash")


def _mask_number(text: str, keep: int = 4) -> str:
    digits = [c for c in text if c.isdigit()]
    keep_from = max(0, len(digits) - keep)
    out, di = [], 0
    for c in text:
        if c.isdigit():
            out.append(c if di >= keep_from else "*")
            di += 1
        else:
            out.append(c)
    return "".join(out)


def _mask_email(text: str) -> str:
    local, _, domain = text.partition("@")
    tld = domain.rsplit(".", 1)[-1] if "." in domain else domain
    head = local[:1] if local else ""
    return f"{head}***@***.{tld}"


def _mask(label: str, text: str) -> str:
    if label == "EMAIL" and "@" in text:
        return _mask_email(text)
    if label in _NUMERIC:
        return _mask_number(text)
    return (text[:1] + "*" * max(1, len(text) - 1)) if text else "*"


def _hash(label: str, text: str, salt: str) -> str:
    h = hashlib.sha256(f"{salt}:{label}:{text}".encode()).hexdigest()[:10]
    return f"{label}_{h}"


class Anonymizer:
    """Acumula estado para un documento (consistencia + mapa de reversion)."""

    def __init__(self, mode: str = "pseudo", *, generic_token: str = GENERIC_TOKEN,
                 salt: str = ""):
        if mode not in MODES:
            raise ValueError(f"modo invalido: {mode!r}; usar uno de {MODES}")
        self.mode = mode
        self.generic = generic_token
        self.salt = salt
        self._value_map: dict[tuple[str, str], str] = {}   # (label, original) -> token
        self._counters: dict[str, int] = {}                # label -> n
        self.summary: dict[str, int] = {}                  # label -> ocurrencias

    def _make_token(self, label: str, text: str) -> str:
        if self.mode == "anon":
            return self.generic
        if self.mode == "typed":
            return f"[{label}]"
        if self.mode == "mask":
            return _mask(label, text)
        if self.mode == "hash":
            return _hash(label, text, self.salt)
        # pseudo
        n = self._counters.get(label, 0) + 1
        self._counters[label] = n
        return f"{label}_{n}"

    def token_for(self, label: str, text: str) -> str:
        key = (label, text)
        if key not in self._value_map:
            self._value_map[key] = self._make_token(label, text)
        return self._value_map[key]

    def process(self, text: str, spans: list[Span]) -> str:
        repls = []
        for s in spans:
            tok = self.token_for(s.label, s.text)
            self.summary[s.label] = self.summary.get(s.label, 0) + 1
            repls.append((s.start, s.end, tok))
        return apply_replacements(text, repls)

    @property
    def mapping(self) -> dict[str, str]:
        """Token -> original. Solo en modo pseudo (tokens unicos = reversible)."""
        if self.mode != "pseudo":
            return {}
        return {tok: original for (_label, original), tok in self._value_map.items()}


def deanonymize(text: str, mapping: dict[str, str]) -> str:
    """Re-identifica: reemplaza cada token por su original. Reemplaza primero los
    tokens mas largos para evitar que EMAIL_1 pise a EMAIL_12."""
    for tok in sorted(mapping, key=len, reverse=True):
        text = text.replace(tok, mapping[tok])
    return text
