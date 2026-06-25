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

import hashlib
import hmac
import json
import os
import time
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse, Response

from anonimal_lite import formats
from anonimal_lite.base import apply_replacements, normalize
from anonimal_lite.labels import placeholder_of
from anonimal_lite.modes import MODES, Anonymizer, deanonymize
from anonimal_lite.rules import RuledEngine

from .engines import get_engine, lite_engine

MODE_DEFAULT = os.getenv("ANONIMAL_MODE", "pseudo")
ENGINE_DEFAULT = os.getenv("ANONIMAL_ENGINE", "auto")   # auto | lite | ml
MAX_CHARS = int(os.getenv("ANONIMAL_MAX_CHARS", "500000"))
MAX_PDF_BYTES = int(os.getenv("ANONIMAL_MAX_PDF_BYTES", str(25 * 1024 * 1024)))
TOKEN = os.getenv("ANONIMAL_TOKEN")  # token de SERVICIO (Escriba/Fisherboy por red interna)

# Login de NAVEGADOR (para exponerlo en la web). Independiente del token de servicio:
# Escriba sigue llamando con el token; las personas entran con usuario/clave.
AUTH_ENABLED = os.getenv("ANONIMAL_AUTH_ENABLED", "false").lower() == "true"
AUTH_MODE = os.getenv("ANONIMAL_AUTH_MODE", "local").lower()  # local | federado (Lockatus SSO)
AUTH_USER = os.getenv("ANONIMAL_USER", "")
AUTH_PASSWORD = os.getenv("ANONIMAL_PASSWORD", "")
SESSION_SECRET = os.getenv("ANONIMAL_SESSION_SECRET", "")
COOKIE_SECURE = os.getenv("ANONIMAL_COOKIE_SECURE", "true").lower() == "true"
SESSION_TTL = int(os.getenv("ANONIMAL_SESSION_TTL_HOURS", "12")) * 3600
COOKIE_NAME = "anonimal_auth"
OIDC_COOKIE = "anonimal_oidc"  # cookie de transacción (verifier/state/nonce) en modo federado
# Federación opcional con Lockatus (el hub de identidad de la suite). Default local → sin cambios.
LK_ISSUER = os.getenv("LOCKATUS_ISSUER", "").rstrip("/")
LK_CLIENT = os.getenv("LOCKATUS_CLIENT_ID", "anonimal")
LK_REDIRECT = os.getenv("LOCKATUS_REDIRECT_URI", "")
if AUTH_ENABLED and AUTH_MODE == "federado" and not (SESSION_SECRET and LK_ISSUER and LK_REDIRECT):
    raise RuntimeError("ANONIMAL_AUTH_MODE=federado requiere ANONIMAL_SESSION_SECRET, LOCKATUS_ISSUER y LOCKATUS_REDIRECT_URI.")
if AUTH_ENABLED and AUTH_MODE != "federado" and not (AUTH_USER and AUTH_PASSWORD and SESSION_SECRET):
    raise RuntimeError(
        "ANONIMAL_AUTH_ENABLED=true requiere ANONIMAL_USER, ANONIMAL_PASSWORD y ANONIMAL_SESSION_SECRET."
    )
_lk = None
if AUTH_ENABLED and AUTH_MODE == "federado":
    from .lockatus_client import Lockatus
    _lk = Lockatus(LK_ISSUER, LK_CLIENT, LK_REDIRECT, SESSION_SECRET)
_login_fails: dict[str, dict] = {}   # rate-limit de login por IP (en memoria)

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


@app.middleware("http")
async def auth_gate(request: Request, call_next):
    # Solo la UI (página + estáticos) exige sesión de navegador. /login, /logout,
    # /health y la API quedan fuera: la API se gatea con require_auth (token O sesión).
    if AUTH_ENABLED:
        path = request.url.path
        if (path == "/" or path.startswith("/static")) and not _cookie_valid(request.cookies.get(COOKIE_NAME)):
            return RedirectResponse("/login", status_code=302)
    return await call_next(request)


def _sign(value: str) -> str:
    sig = hmac.new(SESSION_SECRET.encode(), value.encode(), hashlib.sha256).hexdigest()
    return f"{value}.{sig}"


def _make_cookie() -> str:
    return _sign(str(int(time.time()) + SESSION_TTL))


def _cookie_valid(raw: str | None) -> bool:
    if not raw or "." not in raw:
        return False
    value, _, sig = raw.rpartition(".")
    expected = hmac.new(SESSION_SECRET.encode(), value.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, expected):
        return False
    try:
        return int(value) > int(time.time())
    except ValueError:
        return False


def _password_ok(supplied: str) -> bool:
    def h(s: str) -> bytes:
        return hashlib.sha256((s or "").encode()).digest()
    return hmac.compare_digest(h(supplied), h(AUTH_PASSWORD))


def _token_supplied(request: Request) -> str | None:
    tok = request.headers.get("x-anonimal-token")
    if not tok:
        authz = request.headers.get("authorization", "")
        if authz.lower().startswith("bearer "):
            tok = authz.split(" ", 1)[1]
    return tok


def require_auth(request: Request) -> None:
    """Gate de la API: pasa con el TOKEN de servicio (Escriba) O con sesión de
    navegador (login). Sin token ni auth configurados → abierto (modo local)."""
    if TOKEN:
        tok = _token_supplied(request)
        if tok and hmac.compare_digest(tok, TOKEN):
            return
    if AUTH_ENABLED:
        if _cookie_valid(request.cookies.get(COOKIE_NAME)):
            return
        raise HTTPException(status_code=401, detail="No autenticado.")
    if TOKEN:
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
    patterns = rules.get("patterns") or []
    if not always and not never and not patterns:
        return engine
    return RuledEngine(engine, always, never, patterns)


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
        "hosted": AUTH_ENABLED,   # instancia pública con login → la UI muestra la nota de privacidad
        "engine_default": ENGINE_DEFAULT,
        "mode_default": MODE_DEFAULT,
        "lite": True,
        "ml": {
            "available": ml is not None,
            "ready": bool(ml and ml.ready()),
            "error": (ml.error if ml is not None else None),
        },
    }


@app.post("/detect", dependencies=[Depends(require_auth)])
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


@app.post("/anonymize", dependencies=[Depends(require_auth)])
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


@app.post("/deanonymize", dependencies=[Depends(require_auth)])
def reidentify(req: DeanonReq):
    if not req.map:
        raise HTTPException(status_code=422, detail="Falta el mapa de reversion.")
    return {"output": deanonymize(req.text, req.map)}


@app.post("/anonymize_file", dependencies=[Depends(require_auth)])
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


@app.post("/redact_pdf", dependencies=[Depends(require_auth)])
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


_FAVI = (
    "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E"
    "%3Crect width='64' height='64' rx='15' fill='%234a4e7c'/%3E"
    "%3Cpath d='M12 26C12 22 16 21 20 21L44 21C48 21 52 22 52 26C52 32 50 40 42 40C36 40 34 35 32 35C30 35 28 40 22 40C14 40 12 32 12 26Z' fill='%23fff'/%3E"
    "%3Cellipse cx='23' cy='29' rx='4' ry='3.1' fill='%234a4e7c'/%3E"
    "%3Cellipse cx='41' cy='29' rx='4' ry='3.1' fill='%234a4e7c'/%3E%3C/svg%3E"
)


def _login_page(err: str = "") -> str:
    msg = f'<p class="err">{err}</p>' if err else ""
    return (
        '<!doctype html><html lang="es"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        "<title>Anonimal — Ingresar</title>"
        f'<link rel="icon" href="{_FAVI}"><style>'
        ":root{--bg:#f5f6fa;--card:#fff;--ink:#1a1c2b;--muted:#6b7080;--line:rgba(20,22,40,.12);--accent:#4a4e7c}"
        "@media(prefers-color-scheme:dark){:root{--bg:#0c0d14;--card:#14161f;--ink:#e9eaf2;--muted:#9498ad;--line:rgba(255,255,255,.12);--accent:#8a8fd0}}"
        "*{box-sizing:border-box}body{margin:0;min-height:100vh;display:grid;place-items:center;background:var(--bg);"
        "color:var(--ink);font:15px/1.5 'Inter',system-ui,-apple-system,'Segoe UI',sans-serif}"
        ".card{width:min(380px,92vw);background:var(--card);border:1px solid var(--line);border-radius:18px;"
        "padding:34px 30px;box-shadow:0 30px 80px -30px rgba(0,0,0,.4)}"
        ".logo{display:flex;align-items:center;justify-content:center;gap:10px;font-weight:700;font-size:21px;letter-spacing:-.02em}"
        ".logo svg{width:30px;height:30px}.sub{text-align:center;color:var(--muted);font-size:13px;margin:4px 0 22px}"
        "form{display:flex;flex-direction:column;gap:11px}"
        "input{font:inherit;padding:11px 13px;border-radius:10px;border:1px solid var(--line);background:var(--bg);color:var(--ink)}"
        "input:focus{outline:none;border-color:var(--accent);box-shadow:0 0 0 3px color-mix(in srgb,var(--accent) 22%,transparent)}"
        "button{font:inherit;font-weight:600;margin-top:4px;padding:11px;border:0;border-radius:10px;background:var(--accent);color:#fff;cursor:pointer}"
        ".err{background:color-mix(in srgb,#cf222e 12%,transparent);color:#cf222e;font-size:13px;padding:8px 11px;border-radius:9px;margin:0 0 12px;text-align:center}"
        "</style></head><body><div class=\"card\">"
        '<div class="logo"><svg viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg">'
        '<rect width="64" height="64" rx="15" fill="#4a4e7c"/>'
        '<path d="M12 26 C12 22 16 21 20 21 L44 21 C48 21 52 22 52 26 C52 32 50 40 42 40 C36 40 34 35 32 35 C30 35 28 40 22 40 C14 40 12 32 12 26 Z" fill="#fff"/>'
        '<ellipse cx="23" cy="29" rx="4" ry="3.1" fill="#4a4e7c" transform="rotate(-12 23 29)"/>'
        '<ellipse cx="41" cy="29" rx="4" ry="3.1" fill="#4a4e7c" transform="rotate(12 41 29)"/>'
        "</svg>Anonimal</div>"
        '<p class="sub">Anonimizador de PII</p>'
        f"{msg}"
        '<form method="post" action="/login">'
        '<input name="user" placeholder="Usuario" autocomplete="username" autofocus>'
        '<input name="password" type="password" placeholder="Contraseña" autocomplete="current-password">'
        "<button type=\"submit\">Entrar</button>"
        "</form></div></body></html>"
    )


def _logged_out_page() -> str:
    # Pantalla "sesión cerrada" del modo federado: mismo card, con botón al SSO (sin auto-rebote).
    return (
        '<!doctype html><html lang="es"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        "<title>Anonimal — Sesión cerrada</title>"
        f'<link rel="icon" href="{_FAVI}"><style>'
        ":root{--bg:#f5f6fa;--card:#fff;--ink:#1a1c2b;--muted:#6b7080;--line:rgba(20,22,40,.12);--accent:#4a4e7c}"
        "@media(prefers-color-scheme:dark){:root{--bg:#0c0d14;--card:#14161f;--ink:#e9eaf2;--muted:#9498ad;--line:rgba(255,255,255,.12);--accent:#8a8fd0}}"
        "*{box-sizing:border-box}body{margin:0;min-height:100vh;display:grid;place-items:center;background:var(--bg);"
        "color:var(--ink);font:15px/1.5 'Inter',system-ui,-apple-system,'Segoe UI',sans-serif}"
        ".card{width:min(380px,92vw);background:var(--card);border:1px solid var(--line);border-radius:18px;"
        "padding:34px 30px;box-shadow:0 30px 80px -30px rgba(0,0,0,.4);text-align:center}"
        ".logo{display:flex;align-items:center;justify-content:center;gap:10px;font-weight:700;font-size:21px;letter-spacing:-.02em}"
        ".logo svg{width:30px;height:30px}.sub{color:var(--muted);font-size:13px;margin:6px 0 22px}"
        "a.btn{display:inline-block;text-decoration:none;font:inherit;font-weight:600;padding:11px 18px;border-radius:10px;background:var(--accent);color:#fff}"
        "</style></head><body><div class=\"card\">"
        '<div class="logo"><svg viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg">'
        '<rect width="64" height="64" rx="15" fill="#4a4e7c"/>'
        '<path d="M12 26 C12 22 16 21 20 21 L44 21 C48 21 52 22 52 26 C52 32 50 40 42 40 C36 40 34 35 32 35 C30 35 28 40 22 40 C14 40 12 32 12 26 Z" fill="#fff"/>'
        '<ellipse cx="23" cy="29" rx="4" ry="3.1" fill="#4a4e7c" transform="rotate(-12 23 29)"/>'
        '<ellipse cx="41" cy="29" rx="4" ry="3.1" fill="#4a4e7c" transform="rotate(12 41 29)"/>'
        "</svg>Anonimal</div>"
        '<p class="sub">Cerraste la sesión.</p>'
        '<a class="btn" href="/login">Entrar con Lockatus</a>'
        "</div></body></html>"
    )


@app.get("/login", include_in_schema=False)
def login_get(request: Request, e: str = "", out: str = ""):
    if not AUTH_ENABLED or _cookie_valid(request.cookies.get(COOKIE_NAME)):
        return RedirectResponse("/", status_code=302)
    if AUTH_MODE == "federado":
        # Tras "Salir" (out=1) NO rebotamos al SSO: el hub sigue con sesión y reentraría solo.
        # Mostramos una pantalla "sesión cerrada" con botón para volver a entrar a propósito.
        if out:
            return HTMLResponse(_logged_out_page())
        lk = _lk
        if lk is None:  # en federado siempre está; el guard satisface el tipo y es fail-safe
            return HTMLResponse(_login_page("Federación mal configurada."), status_code=500)
        verifier, challenge = lk.pkce()
        state, nonce = lk.random_id(), lk.random_id()
        tx = lk.sign({"verifier": verifier, "state": state, "nonce": nonce, "exp": (time.time() + 600) * 1000})
        resp = RedirectResponse(lk.authorize_url(state, nonce, challenge), status_code=302)
        resp.set_cookie(OIDC_COOKIE, tx, httponly=True, secure=COOKIE_SECURE, samesite="lax", max_age=600)
        return resp
    errs = {"1": "Usuario o contraseña incorrectos.", "2": "Demasiados intentos. Esperá un minuto."}
    return HTMLResponse(_login_page(errs.get(e, "")))


# Vuelta de Lockatus (modo federado): canjea el código, verifica los tokens y siembra la MISMA
# cookie de sesión que el login propio → el resto del gate de Anonimal no cambia.
@app.get("/callback", include_in_schema=False)
def lk_callback(request: Request):
    if not AUTH_ENABLED or AUTH_MODE != "federado":
        return RedirectResponse("/", status_code=302)
    lk = _lk
    if lk is None:  # en federado siempre está; el guard satisface el tipo y es fail-safe
        return RedirectResponse("/", status_code=302)
    if request.query_params.get("error"):
        return HTMLResponse(f"Acceso denegado por Lockatus: {request.query_params['error']}", status_code=403)
    tx = lk.unsign(request.cookies.get(OIDC_COOKIE, ""))
    code, state = request.query_params.get("code"), request.query_params.get("state")
    if not tx or not code or state != tx["state"]:
        return RedirectResponse("/login", status_code=302)
    try:
        tok = lk.exchange(code, tx["verifier"])
        lk.verify_jwt(tok["id_token"], audience=LK_CLIENT, nonce=tx["nonce"])
        lk.verify_jwt(tok["access_token"], audience=LK_CLIENT)
    except Exception:
        return RedirectResponse("/login?e=1", status_code=302)
    resp = RedirectResponse("/", status_code=302)
    resp.delete_cookie(OIDC_COOKIE)
    resp.set_cookie(COOKIE_NAME, _make_cookie(), httponly=True, secure=COOKIE_SECURE, samesite="lax", max_age=SESSION_TTL)
    return resp


@app.post("/login", include_in_schema=False)
def login_post(request: Request, user: str = Form(""), password: str = Form("")):
    if not AUTH_ENABLED:
        return RedirectResponse("/", status_code=302)
    ip = request.client.host if request.client else "?"
    now = time.time()
    f = _login_fails.get(ip)
    if f and f["n"] >= 8 and now - f["t"] < 60:
        return RedirectResponse("/login?e=2", status_code=302)
    if user == AUTH_USER and _password_ok(password):
        _login_fails.pop(ip, None)
        resp = RedirectResponse("/", status_code=302)
        resp.set_cookie(COOKIE_NAME, _make_cookie(), httponly=True,
                        secure=COOKIE_SECURE, samesite="lax", max_age=SESSION_TTL)
        return resp
    _login_fails[ip] = {"n": (f["n"] + 1 if f and now - f["t"] < 60 else 1), "t": now}
    return RedirectResponse("/login?e=1", status_code=302)


@app.get("/logout", include_in_schema=False)
def logout():
    # En federado salimos a la pantalla "sesión cerrada" (out=1) para no re-loguear solo.
    target = "/login?out=1" if AUTH_MODE == "federado" else "/login"
    resp = RedirectResponse(target, status_code=302)
    # delete_cookie debe repetir path/secure/samesite del set, si no algunos navegadores no la borran.
    resp.delete_cookie(COOKIE_NAME, path="/", secure=COOKIE_SECURE, httponly=True, samesite="lax")
    resp.delete_cookie(OIDC_COOKIE, path="/", secure=COOKIE_SECURE, httponly=True, samesite="lax")
    return resp


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
