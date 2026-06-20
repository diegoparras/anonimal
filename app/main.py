"""Anonimal — API de anonimizacion de PII, local y self-hosted.

El motor corre en tu maquina: el dato nunca sale. Expone deteccion,
anonimizacion (5 modos), re-identificacion (reversibilidad) y anonimizacion de
archivos preservando el formato.

Modos: typed / anon / pseudo (reversible) / mask / hash  (ver engine/modes.py).
Motores: lite (regex, siempre) y ml (OPF, si esta instalado).

SEGURIDAD: pensado para correr LOCAL. Si lo expones, defini `ANONIMAL_TOKEN` y
poné un reverse proxy con TLS adelante. Sin token, la API queda abierta (asume
localhost).
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.requests import Request
from starlette.responses import Response

from .engine import formats, get_engine, lite_engine
from .engine.base import apply_replacements, normalize
from .engine.labels import placeholder_of
from .engine.modes import MODES, Anonymizer, deanonymize
from .engine.rules import RuledEngine

MODE_DEFAULT = os.getenv("ANONIMAL_MODE", "pseudo")
ENGINE_DEFAULT = os.getenv("ANONIMAL_ENGINE", "auto")   # auto | lite | ml
MAX_CHARS = int(os.getenv("ANONIMAL_MAX_CHARS", "500000"))
MAX_PDF_BYTES = int(os.getenv("ANONIMAL_MAX_PDF_BYTES", str(25 * 1024 * 1024)))
TOKEN = os.getenv("ANONIMAL_TOKEN")  # si esta seteado, se exige en cada request

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="Anonimal", version="0.1.0",
              description="Anonimizacion de PII local y self-hosted.")

_CSP = (
    "default-src 'self'; "
    "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
    "font-src 'self' https://cdn.jsdelivr.net data:; "
    "img-src 'self' data:; "
    "script-src 'self'; "
    "connect-src 'self'; "
    "base-uri 'none'; frame-ancestors 'none'"
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    resp: Response = await call_next(request)
    resp.headers.setdefault("Content-Security-Policy", _CSP)
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    resp.headers.setdefault("Referrer-Policy", "no-referrer")
    return resp


def require_token(
    authorization: str | None = Header(None),
    x_anonimal_token: str | None = Header(None),
) -> None:
    if not TOKEN:
        return
    supplied = x_anonimal_token
    if not supplied and authorization and authorization.lower().startswith("bearer "):
        supplied = authorization.split(" ", 1)[1]
    if supplied != TOKEN:
        raise HTTPException(status_code=401, detail="Token invalido o ausente.")


def _pick_engine(requested: str | None):
    """Devuelve (engine, nombre_usado). 'auto' usa ML si esta listo, si no lite.
    'ml' explicito da 503 si no esta disponible."""
    name = requested or ENGINE_DEFAULT
    if name in ("ml", "auto"):
        ml = get_engine("ml")
        if ml is not None and ml.ready():
            return ml, "ml"
        if name == "ml":
            detail = "Motor ML no disponible."
            if ml is not None and ml.error:
                detail = f"Motor ML no disponible: {ml.error}"
            raise HTTPException(status_code=503, detail=detail)
    return lite_engine(), "lite"


def _check_size(text: str) -> None:
    if len(text) > MAX_CHARS:
        raise HTTPException(status_code=413,
                            detail=f"El texto supera el limite de {MAX_CHARS} caracteres.")


def _check_mode(mode: str) -> str:
    if mode not in MODES:
        raise HTTPException(status_code=422,
                            detail=f"Modo invalido: {mode!r}. Validos: {', '.join(MODES)}.")
    return mode


def _with_rules(engine, rules: dict | None):
    """Envuelve el motor con las reglas del usuario, si las hay."""
    if not rules:
        return engine
    always = rules.get("always") or []
    never = rules.get("never") or []
    if not always and not never:
        return engine
    return RuledEngine(engine, always, never)


# --------- modelos ---------

class DetectReq(BaseModel):
    text: str
    engine: str | None = None
    rules: dict | None = None


class AnonReq(BaseModel):
    text: str
    mode: str | None = None
    engine: str | None = None
    rules: dict | None = None


class DeanonReq(BaseModel):
    text: str
    map: dict[str, str] = Field(default_factory=dict)


# --------- rutas ---------

@app.get("/health")
def health():
    ml = get_engine("ml")
    return {
        "status": "ok",
        "engine_default": ENGINE_DEFAULT,
        "mode_default": MODE_DEFAULT,
        "lite": True,
        "ml": {
            "available": ml is not None,
            "ready": bool(ml and ml.ready()),
            "error": (ml.error if ml is not None else None),
        },
    }


@app.post("/detect", dependencies=[Depends(require_token)])
def detect(req: DetectReq):
    _check_size(req.text)
    engine, used = _pick_engine(req.engine)
    engine = _with_rules(engine, req.rules)
    spans = engine.detect(req.text)
    return {"engine": used, "spans": [s.as_dict() for s in spans], "count": len(spans)}


def _legacy_detect_response(text: str, spans) -> dict:
    """Contrato LEGACY (compat con el Anonimal embebido): detecta y no decide.
    Lo dispara `/anonymize` cuando NO viene `mode` -> drop-in para Escriba/Fisherboy."""
    detected = [{"label": s.label, "start": s.start, "end": s.end, "text": s.text,
                 "placeholder": placeholder_of(s.label)} for s in spans]
    redacted = apply_replacements(text, [(s.start, s.end, placeholder_of(s.label)) for s in spans])
    summary: dict[str, int] = {}
    for s in spans:
        summary[s.label] = summary.get(s.label, 0) + 1
    return {"text": text, "detected_spans": detected,
            "redacted_text": redacted, "summary": summary}


@app.post("/anonymize", dependencies=[Depends(require_token)])
def anonymize(req: AnonReq):
    _check_size(req.text)
    engine, used = _pick_engine(req.engine)
    engine = _with_rules(engine, req.rules)
    if req.mode is None:
        # Sin `mode` -> contrato legacy (detect-only) para consumidores actuales.
        return _legacy_detect_response(req.text, engine.detect(req.text))
    mode = _check_mode(req.mode)
    text = normalize(req.text)
    anon = Anonymizer(mode)
    spans = engine.detect(text)
    output = anon.process(text, spans)
    return {
        "engine": used,
        "mode": mode,
        "output": output,
        "spans": [s.as_dict() for s in spans],   # para resaltar en la UI
        "map": anon.mapping,            # no vacio solo en modo pseudo
        "reversible": mode == "pseudo",
        "summary": anon.summary,
    }


@app.post("/deanonymize", dependencies=[Depends(require_token)])
def reidentify(req: DeanonReq):
    if not req.map:
        raise HTTPException(status_code=422, detail="Falta el mapa de reversion.")
    return {"output": deanonymize(req.text, req.map)}


@app.post("/anonymize_file", dependencies=[Depends(require_token)])
async def anonymize_file(file: UploadFile = File(...),
                         mode: str = Form(MODE_DEFAULT),
                         engine: str | None = Form(None),
                         rules_json: str = Form("")):
    raw = await file.read()
    try:
        content = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=415,
            detail="Solo archivos de texto UTF-8 (txt/md/csv/json/log/srt/html).",
        ) from None
    _check_size(content)
    mode = _check_mode(mode)
    rules = None
    if rules_json.strip():
        try:
            rules = json.loads(rules_json)
        except json.JSONDecodeError:
            raise HTTPException(status_code=422, detail="rules_json no es JSON valido.") from None
    eng, used = _pick_engine(engine)
    eng = _with_rules(eng, rules)
    anon = Anonymizer(mode)
    fmt, output = formats.anonymize_file(file.filename or "input.txt", content, eng, anon)
    return {
        "filename": file.filename,
        "format": fmt,
        "engine": used,
        "mode": mode,
        "content": output,
        "map": anon.mapping,
        "reversible": mode == "pseudo",
        "summary": anon.summary,
    }


@app.post("/redact_pdf", dependencies=[Depends(require_token)])
async def redact_pdf(file: UploadFile = File(...),
                     engine: str | None = Form(None),
                     rules_json: str = Form("")):
    from . import pdf as pdf_mod
    if not pdf_mod.is_available():
        raise HTTPException(status_code=503,
                            detail="Redaccion de PDF no disponible (falta PyMuPDF).")
    raw = await file.read()
    if len(raw) > MAX_PDF_BYTES:
        raise HTTPException(status_code=413,
                            detail=f"El PDF supera el limite de {MAX_PDF_BYTES} bytes.")
    rules = None
    if rules_json.strip():
        try:
            rules = json.loads(rules_json)
        except json.JSONDecodeError:
            raise HTTPException(status_code=422, detail="rules_json no es JSON valido.") from None
    eng, _used = _pick_engine(engine)
    eng = _with_rules(eng, rules)
    try:
        out, count = pdf_mod.redact_pdf_bytes(raw, eng)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from None
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"No se pudo procesar el PDF: {e}") from None
    name = (file.filename or "documento.pdf").rsplit("/", 1)[-1]
    return Response(
        content=out,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="redactado_{name}"',
            "X-Redactions": str(count),
        },
    )


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
