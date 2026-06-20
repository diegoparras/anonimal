"""Smoke test: arranca la app en un servidor REAL y la prueba de verdad.

- Local: levanta uvicorn en un puerto y prueba contra el (verifica que la app
  arranca, no solo el TestClient en proceso).
- CI / contenedor: si esta seteada SMOKE_URL, prueba contra esa URL (la imagen
  ya corriendo) y no levanta nada.

Sale 0 si /health responde y un /anonymize real anonimiza. Sirve para el gate
de pre-deploy: atrapa errores de empaquetado/arranque que los unit tests no ven.
"""
import os
import subprocess
import sys
import time

import httpx

PORT = int(os.getenv("SMOKE_PORT", "8099"))


def _wait_health(base: str, timeout: float = 40.0) -> dict:
    deadline = time.monotonic() + timeout
    last = ""
    while time.monotonic() < deadline:
        try:
            r = httpx.get(f"{base}/health", timeout=2)
            if r.status_code == 200:
                return r.json()
            last = f"{r.status_code} {r.text}"
        except Exception as e:
            last = repr(e)
        time.sleep(0.5)
    raise SystemExit(f"smoke: /health no respondio a tiempo ({last})")


def main() -> int:
    base = os.getenv("SMOKE_URL")
    proc = None
    if not base:
        base = f"http://127.0.0.1:{PORT}"
        proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app.main:app",
             "--host", "127.0.0.1", "--port", str(PORT), "--log-level", "warning"],
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        )
    try:
        health = _wait_health(base)
        assert health.get("status") == "ok", f"health raro: {health}"

        r = httpx.post(f"{base}/anonymize",
                       json={"text": "escribile a juan@acme.com", "mode": "pseudo",
                             "engine": "lite"},
                       timeout=10)
        assert r.status_code == 200, f"/anonymize {r.status_code}: {r.text}"
        body = r.json()
        assert "juan@acme.com" not in body["output"], f"se filtro PII: {body}"
        assert body["map"], "el modo pseudo deberia devolver mapa de reversion"
        print(f"smoke OK -> {body['output']}")
        return 0
    finally:
        if proc is not None:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except Exception:
                proc.kill()


if __name__ == "__main__":
    sys.exit(main())
