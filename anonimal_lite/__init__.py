"""anonimal_lite — el motor de anonimización **liviano** de Anonimal, como librería.

Stdlib puro (sin FastAPI ni torch): detección por regex (común + LATAM), los 5
modos de reemplazo, reversibilidad, reglas propias y anonimización de formatos
(csv/json/…). Es el **fallback standalone** que cada satélite del ecosistema
instala para anonimizar sin depender del servicio Anonimal.

    from anonimal_lite import LiteEngine, Anonymizer, deanonymize
    eng = LiteEngine()
    out = Anonymizer("pseudo").process(text, eng.detect(text))

El anonimato **completo (ML/OPF)** vive en el servicio Anonimal (vía HTTP); esta
librería es solo el piso básico que garantiza que nadie quede sin anonimizar.
"""
from __future__ import annotations

from . import common, formats, latam
from .base import (
    Span,
    apply_replacements,
    finalize,
    normalize,
    propagate,
    resolve_overlaps,
)
from .labels import (
    NUMERIC_TYPES,
    PLACEHOLDER_TO_LABEL,
    placeholder_of,
    type_of,
)
from .lite_engine import LiteEngine
from .modes import GENERIC_TOKEN, MODES, Anonymizer, deanonymize
from .rules import RuledEngine, merge

__version__ = "0.3.0"

__all__ = [
    "GENERIC_TOKEN",
    "MODES",
    "NUMERIC_TYPES",
    "PLACEHOLDER_TO_LABEL",
    "Anonymizer",
    "LiteEngine",
    "RuledEngine",
    "Span",
    "apply_replacements",
    "common",
    "deanonymize",
    "finalize",
    "formats",
    "latam",
    "merge",
    "normalize",
    "placeholder_of",
    "propagate",
    "resolve_overlaps",
    "type_of",
]
