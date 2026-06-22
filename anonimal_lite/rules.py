"""Reglas propias del usuario sobre los spans detectados:

- `patterns`: **regex** que SIEMPRE ocultar, cada uno `{regex, placeholder?}`. El
  placeholder se usa como tipo del token (p. ej. `«LEGAJO_1»`). Motor seguro
  `re2` si está instalado; si no, `re` de stdlib con topes (ver más abajo).
- `always`: términos LITERALES que SIEMPRE ocultar (case-insensitive).
- `never`: términos que NUNCA ocultar (lista blanca, normalizada NFC+casefold).

Se envuelve un motor existente sin tocarlo (`RuledEngine`), así sirve igual para
texto y para archivos (formats.py usa cualquier objeto con `.detect`).

SEGURIDAD (ReDoS): los patrones los escribe el operador (BYOR), pero el texto
puede ser no confiable. Si `google-re2` está instalado se usa (inmune a
backtracking catastrófico). Si no, se cae a `re` de stdlib con límites de
cantidad/longitud de patrón como mitigación; preferí patrones anclados y simples.
"""
from __future__ import annotations

import re
import unicodedata

from .base import Span, finalize
from .labels import type_of
from .lite_engine import PRIORITY

# Motor para los patrones DEL USUARIO (texto no confiable -> riesgo ReDoS):
#   1) re2: lineal, inmune a backtracking catastrófico (ideal si está instalado).
#   2) regex: permite `timeout=` que corta el backtracking catastrófico.
# Si no hay NINGUNO, los patrones custom NO se ejecutan sobre `re` de stdlib (sería
# ReDoS) — se ignoran fail-safe. Así la lib sigue siendo stdlib-pura por defecto; el
# servicio Anonimal trae `regex` en requirements para habilitar la feature. Auditoría 2026-06.
try:
    import re2 as _user_rx  # type: ignore
    _USER_ENGINE = "re2"
except ImportError:
    try:
        import regex as _user_rx  # type: ignore
        _USER_ENGINE = "regex"
    except ImportError:
        _user_rx = None
        _USER_ENGINE = None

_USER_RX_TIMEOUT = 1.0      # s por patrón (solo motor `regex`): cota dura anti-ReDoS

_CUSTOM_PRIORITY = {**PRIORITY, "CUSTOM": 100}  # lo del usuario gana siempre
_MAX_PATTERNS = 50          # tope anti-abuso
_MAX_PATTERN_LEN = 200      # tope de longitud por patrón


def _key(s: str) -> str:
    """Normaliza para la lista blanca: NFC + casefold (insensible a mayúsculas y
    a la forma Unicode), así "José" matchea aunque venga "JOSÉ" o descompuesto."""
    return unicodedata.normalize("NFC", s).strip().casefold()


def _label_for(placeholder: str) -> str:
    """Tipo del span custom a partir del placeholder del usuario (o CUSTOM)."""
    t = (placeholder or "").strip()
    if not t:
        return "CUSTOM"
    # type_of sanea a [A-Z]+; conservamos eso como label para que el token salga
    # «<TIPO>_N» con el nombre que eligió el usuario.
    return type_of(t)


def _compile_patterns(patterns):
    if _user_rx is None:  # sin motor seguro no corremos regex de usuario (anti-ReDoS)
        return []
    compiled = []
    for p in (patterns or [])[:_MAX_PATTERNS]:
        if not isinstance(p, dict):
            continue
        rx = (p.get("regex") or "").strip()
        if not rx or len(rx) > _MAX_PATTERN_LEN:
            continue
        label = _label_for(p.get("placeholder") or p.get("label") or "")
        try:
            compiled.append((_user_rx.compile(rx), label))
        except Exception:  # nosec B112 - regex inválida del usuario: se ignora, no rompe
            continue
    return compiled


def _user_finditer(pat, text):
    """finditer del patrón de usuario con cota anti-ReDoS según el motor."""
    if _USER_ENGINE == "regex":
        # timeout duro: corta el backtracking catastrófico (re2 no lo necesita: es lineal).
        return list(pat.finditer(text, timeout=_USER_RX_TIMEOUT))
    return list(pat.finditer(text))


def merge(text: str, spans: list[Span], *, always=None, never=None, patterns=None) -> list[Span]:
    never_set = {_key(n) for n in (never or []) if n.strip()}
    kept = [s for s in spans if _key(s.text) not in never_set]
    for term in (always or []):
        t = term.strip()
        if not t:
            continue
        for m in re.finditer(re.escape(t), text, re.IGNORECASE):
            kept.append(Span("CUSTOM", m.start(), m.end(), m.group()))
    for rx, label in _compile_patterns(patterns):
        try:
            matches = _user_finditer(rx, text)
        except TimeoutError:
            continue  # patrón demasiado costoso: fail-safe, no cuelga el worker
        for m in matches:
            if m.end() > m.start():
                kept.append(Span(label, m.start(), m.end(), m.group()))
    return finalize(text, kept, _CUSTOM_PRIORITY)


class RuledEngine:
    """Envuelve un motor y le aplica las reglas del usuario en cada `detect`."""

    def __init__(self, engine, always: list[str] | None = None,
                 never: list[str] | None = None, patterns: list[dict] | None = None):
        self._engine = engine
        self.always = always or []
        self.never = never or []
        self.patterns = patterns or []

    @property
    def name(self) -> str:
        return getattr(self._engine, "name", "lite")

    def ready(self) -> bool:
        return self._engine.ready()

    def detect(self, text: str) -> list[Span]:
        return merge(text, self._engine.detect(text),
                     always=self.always, never=self.never, patterns=self.patterns)
