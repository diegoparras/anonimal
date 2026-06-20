"""Los 5 modos de reemplazo + la reversibilidad. Salida alineada con Escriba
(paridad para que pueda delegar sin cambiar comportamiento).

Modos:
  typed   -> placeholder legible por tipo:          [EMAIL]
  anon    -> un único token genérico:               <<ANOM_DATA>>
  pseudo  -> seudónimo estable y tipado:            «PERSONA_1»  (REVERSIBLE: mapa)
  mask    -> enmascarado parcial type-aware:        j•••@acme.com / ••••••78-6
  hash    -> seudónimo estable por HMAC (one-way):  «EMAIL_a1b2c3d4e5f6...»

Consistencia: el mismo valor original siempre recibe el mismo reemplazo dentro
de una corrida (un `Anonymizer` por documento). Solo `pseudo` es reversible:
expone `mapping` (token -> original) para re-identificar con `deanonymize`.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import os
import re
import secrets

from .base import Span, apply_replacements
from .labels import NUMERIC_TYPES, type_of

log = logging.getLogger("anonimal.modes")

GENERIC_TOKEN = "<<ANOM_DATA>>"  # nosec B105 - token de redacción público, no credencial
MODES = ("typed", "anon", "pseudo", "mask", "hash")

# Clave del hash estable. Con ANON_HASH_KEY seteada, el MISMO dato produce el
# MISMO seudónimo entre corridas y documentos (linkage). Sin ella, se genera una
# clave aleatoria por proceso (no estable entre reinicios) para no ser reversible
# por rainbow table sobre el espacio de DNI/CUIT/CBU.
_HASH_KEY_ENV = os.getenv("ANON_HASH_KEY", "") or ""
if _HASH_KEY_ENV:
    _HASH_KEY = _HASH_KEY_ENV.encode("utf-8")
else:
    _HASH_KEY = secrets.token_bytes(32)
    log.warning("ANON_HASH_KEY no seteada: el modo 'hash' no será estable entre "
                "reinicios. Seteala con un secreto para seudónimos estables.")

_TOKEN_RE = re.compile(r"«[A-Z]+_[0-9A-Za-z]+»")


def _mask_value(frag: str, typ: str) -> str:
    """Enmascarado PARCIAL type-aware: deja una pista mínima sin exponer el dato
    (dominio del email, últimos 4 de un ID, iniciales de nombres)."""
    s = frag.strip()
    if not s:
        return frag
    if typ == "EMAIL" and "@" in s:
        local, _, dom = s.partition("@")
        return f"{local[:1] or '•'}•••@{dom}"
    if typ == "URL":
        return "•••"
    digits = re.sub(r"\D", "", s)
    if typ in NUMERIC_TYPES or len(digits) >= 6:
        reveal = max(0, min(4, len(s) - 1))
        last = s[-reveal:] if reveal else ""
        head = re.sub(r"[0-9A-Za-z]", "•", s[:len(s) - reveal])
        return (head + last) if head else ("••••" + last)
    return " ".join((w[0] + "•" * max(1, len(w) - 1)) if w else w for w in s.split())


def _hash_token(frag: str, typ: str) -> str:
    h = hmac.new(_HASH_KEY, frag.strip().lower().encode("utf-8"), hashlib.sha256).hexdigest()[:16]
    return f"«{typ}_{h}»"


class Anonymizer:
    """Acumula estado para un documento (consistencia + mapa de reversión)."""

    def __init__(self, mode: str = "pseudo", *, generic_token: str = GENERIC_TOKEN):
        if mode not in MODES:
            raise ValueError(f"modo inválido: {mode!r}; usar uno de {MODES}")
        self.mode = mode
        self.generic = generic_token
        self._token_for: dict[str, str] = {}   # original -> token
        self._counters: dict[str, int] = {}    # tipo -> n
        self.summary: dict[str, int] = {}      # label -> ocurrencias

    def _make_token(self, label: str, text: str) -> str:
        typ = type_of(label)
        if self.mode == "anon":
            return self.generic
        if self.mode == "typed":
            return f"[{typ}]"
        if self.mode == "mask":
            return _mask_value(text, typ)
        if self.mode == "hash":
            return _hash_token(text, typ)
        # pseudo
        n = self._counters.get(typ, 0) + 1
        self._counters[typ] = n
        return f"«{typ}_{n}»"

    def token_for(self, label: str, text: str) -> str:
        if text not in self._token_for:
            self._token_for[text] = self._make_token(label, text)
        return self._token_for[text]

    def process(self, text: str, spans: list[Span]) -> str:
        repls = []
        for s in spans:
            tok = self.token_for(s.label, s.text)
            self.summary[s.label] = self.summary.get(s.label, 0) + 1
            repls.append((s.start, s.end, tok))
        return apply_replacements(text, repls)

    @property
    def mapping(self) -> dict[str, str]:
        """Token -> original. Solo en modo pseudo (tokens únicos = reversible)."""
        if self.mode != "pseudo":
            return {}
        return {tok: original for original, tok in self._token_for.items()}


def deanonymize(text: str, mapping: dict[str, str]) -> str:
    """Re-identifica: reemplaza cada token «TIPO_N» por su original. Un único pase
    sobre el patrón de token evita reprocesar lo ya reemplazado."""
    if not mapping:
        return text
    return _TOKEN_RE.sub(lambda m: mapping.get(m.group(0), m.group(0)), text)
