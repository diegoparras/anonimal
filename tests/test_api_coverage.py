"""Cobertura de la capa de servicio (app/main.py): token, login de navegador,
logout, redacción de PDF y caminos de error. Sin modelo ML (motor lite)."""
import pytest
from fastapi.testclient import TestClient

import app.main as main

client = TestClient(main.app)
COOKIE = main.COOKIE_NAME


@pytest.fixture(autouse=True)
def _isolate():
    # El TestClient comparte el jar de cookies entre tests: un login exitoso dejaría
    # la sesión y contaminaría los siguientes. Aislamos cada test.
    client.cookies.clear()
    main._login_fails.clear()
    yield
    client.cookies.clear()


# --------- token de servicio (require_auth) ---------
def test_api_token_required(monkeypatch):
    monkeypatch.setattr(main, "TOKEN", "s3cr3t")
    assert client.post("/detect", json={"text": "x"}).status_code == 401          # sin token
    r = client.post("/detect", json={"text": "mail a@b.com"},
                    headers={"X-Anonimal-Token": "s3cr3t"})
    assert r.status_code == 200
    r2 = client.post("/detect", json={"text": "x"},
                     headers={"Authorization": "Bearer s3cr3t"})                   # Bearer
    assert r2.status_code == 200
    assert client.post("/detect", json={"text": "x"},
                       headers={"X-Anonimal-Token": "mal"}).status_code == 401


# --------- login de navegador (AUTH_ENABLED) ---------
@pytest.fixture
def hosted(monkeypatch):
    monkeypatch.setattr(main, "AUTH_ENABLED", True)
    monkeypatch.setattr(main, "AUTH_USER", "u")
    monkeypatch.setattr(main, "AUTH_PASSWORD", "p")
    monkeypatch.setattr(main, "SESSION_SECRET", "testsecret")
    monkeypatch.setattr(main, "COOKIE_SECURE", False)
    main._login_fails.clear()
    yield


def _cookie():
    return {"Cookie": f"{COOKIE}={main._make_cookie()}"}


def test_login_get_renders(hosted):
    r = client.get("/login")
    assert r.status_code == 200 and "Anonimal" in r.text and 'action="/login"' in r.text


def test_login_get_redirects_if_authed(hosted):
    r = client.get("/login", headers=_cookie(), follow_redirects=False)
    assert r.status_code == 302 and r.headers["location"] == "/"


def test_login_wrong_then_ok(hosted):
    bad = client.post("/login", data={"user": "u", "password": "mal"}, follow_redirects=False)
    assert bad.status_code == 302 and "/login?e=1" in bad.headers["location"]
    ok = client.post("/login", data={"user": "u", "password": "p"}, follow_redirects=False)
    assert ok.status_code == 302 and ok.headers["location"] == "/"
    assert COOKIE in ok.headers.get("set-cookie", "")


def test_login_rate_limited(hosted):
    for _ in range(8):
        client.post("/login", data={"user": "u", "password": "x"}, follow_redirects=False)
    r = client.post("/login", data={"user": "u", "password": "x"}, follow_redirects=False)
    assert "/login?e=2" in r.headers["location"]
    # la página de login muestra el aviso e=2
    assert "Demasiados" in client.get("/login?e=2").text


def test_ui_redirects_without_cookie(hosted):
    r = client.get("/", follow_redirects=False)
    assert r.status_code == 302 and r.headers["location"] == "/login"


def test_ui_ok_with_valid_cookie(hosted):
    r = client.get("/", headers=_cookie(), follow_redirects=False)
    assert r.status_code == 200


def test_api_requires_session_when_hosted(hosted):
    assert client.post("/detect", json={"text": "x"}).status_code == 401   # sin cookie ni token
    r = client.post("/detect", json={"text": "mail a@b.com"}, headers=_cookie())
    assert r.status_code == 200


def test_logout_clears_cookie(hosted):
    r = client.get("/logout", follow_redirects=False)
    assert r.status_code == 302 and r.headers["location"] == "/login"


# --------- caminos de error ---------
def test_check_size_413(monkeypatch):
    monkeypatch.setattr(main, "MAX_CHARS", 10)
    assert client.post("/detect", json={"text": "x" * 11}).status_code == 413


def test_deanonymize_sin_mapa():
    assert client.post("/deanonymize", json={"text": "x", "map": {}}).status_code == 422


def test_anonymize_file_rules_json_invalido():
    r = client.post("/anonymize_file",
                    files={"file": ("a.txt", b"hola juan@x.com", "text/plain")},
                    data={"mode": "anon", "rules_json": "{no-json"})
    assert r.status_code == 422


def test_anonymize_file_no_utf8():
    r = client.post("/anonymize_file",
                    files={"file": ("a.bin", b"\xff\xfe\x00\x01", "application/octet-stream")},
                    data={"mode": "anon"})
    assert r.status_code == 415


def test_anonymize_con_reglas_custom():
    r = client.post("/anonymize", json={
        "text": "empleado LEG-1234 en el sistema", "mode": "anon",
        "rules": {"patterns": [{"regex": r"LEG-\d{4}", "placeholder": "ID"}]},
    })
    assert r.status_code == 200 and "LEG-1234" not in r.json()["output"]


# --------- redacción de PDF ---------
def _tiny_pdf_with_email():
    fitz = pytest.importorskip("fitz")
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Contacto: juan@acme.com")
    data = doc.tobytes()
    doc.close()
    return data


def test_redact_pdf_ok():
    pdf = _tiny_pdf_with_email()
    r = client.post("/redact_pdf", files={"file": ("doc.pdf", pdf, "application/pdf")})
    assert r.status_code == 200
    assert "application/pdf" in r.headers.get("content-type", "")


def test_redact_pdf_503_si_no_hay_pymupdf(monkeypatch):
    from app import pdf as pdf_mod
    monkeypatch.setattr(pdf_mod, "is_available", lambda: False)
    r = client.post("/redact_pdf", files={"file": ("doc.pdf", b"%PDF-1.4", "application/pdf")})
    assert r.status_code == 503


def test_redact_pdf_413_por_tamano(monkeypatch):
    monkeypatch.setattr(main, "MAX_PDF_BYTES", 4)
    r = client.post("/redact_pdf", files={"file": ("doc.pdf", b"%PDF-1.4 demasiado", "application/pdf")})
    assert r.status_code == 413
