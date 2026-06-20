# -*- coding: utf-8 -*-
"""Smoke tests de la API (FastAPI TestClient). Sin modelo ML: usa el motor lite."""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok" and body["lite"] is True


def test_detect():
    r = client.post("/detect", json={"text": "mail juan@acme.com"})
    assert r.status_code == 200
    assert any(s["label"] == "EMAIL" for s in r.json()["spans"])


def test_anonymize_pseudo_and_roundtrip():
    text = "mail juan@acme.com de nuevo juan@acme.com"
    r = client.post("/anonymize", json={"text": text, "mode": "pseudo"})
    assert r.status_code == 200
    body = r.json()
    assert body["reversible"] is True and body["map"]
    assert "juan@acme.com" not in body["output"]
    back = client.post("/deanonymize", json={"text": body["output"], "map": body["map"]})
    assert back.status_code == 200 and back.json()["output"] == text


def test_anonymize_invalid_mode():
    r = client.post("/anonymize", json={"text": "x", "mode": "nope"})
    assert r.status_code == 422


def test_anonymize_file_csv():
    src = b"nombre,email\nJuan,juan@acme.com\n"
    r = client.post("/anonymize_file",
                    files={"file": ("data.csv", src, "text/csv")},
                    data={"mode": "pseudo"})
    assert r.status_code == 200
    body = r.json()
    assert body["format"] == "csv" and "juan@acme.com" not in body["content"]
    assert body["content"].startswith("nombre,email")


def test_engine_ml_unavailable_is_503():
    # en este entorno OPF no esta instalado -> pedir 'ml' explicito da 503
    r = client.post("/detect", json={"text": "x", "engine": "ml"})
    assert r.status_code == 503
