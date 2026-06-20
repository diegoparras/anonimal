"""Pruebas de calidad y seguridad: corren las herramientas estandar y exigen
salida limpia.

- ruff           -> codigo redundante / muerto / buggy (no estilo cosmetico)
- vulture        -> dead code (cruzando todo el proyecto)
- bandit         -> auditoria de seguridad estatica (SAST)
- pip-audit      -> vulnerabilidades conocidas en dependencias (OSV/CVE)
- detect-secrets -> que no se filtre ningun secreto al repo

Si una herramienta no esta instalada, la prueba se saltea (SKIP) en vez de
fallar. En CI se instalan todas (requirements-dev.txt) y corren de verdad.
"""
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# Marcadores de error de red: si pip-audit no puede consultar OSV, salteamos.
NET_MARKERS = ("ConnectionError", "Temporary failure", "Failed to resolve",
               "Max retries", "getaddrinfo", "Connection refused", "timed out")


def _have(mod: str) -> bool:
    return importlib.util.find_spec(mod) is not None


def _run(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-m", *args], cwd=ROOT,
                          capture_output=True, text=True)


def test_ruff_sin_codigo_redundante():
    if not _have("ruff"):
        return "SKIP: ruff no instalado (pip install -r requirements-dev.txt)"
    r = _run(["ruff", "check", "."])
    assert r.returncode == 0, f"ruff encontro problemas:\n{r.stdout}\n{r.stderr}"


def test_vulture_sin_dead_code():
    if not _have("vulture"):
        return "SKIP: vulture no instalado"
    r = _run(["vulture"])
    assert r.returncode == 0, f"vulture encontro codigo muerto:\n{r.stdout}\n{r.stderr}"


def test_bandit_sin_hallazgos_de_seguridad():
    if not _have("bandit"):
        return "SKIP: bandit no instalado"
    r = _run(["bandit", "-c", "pyproject.toml", "-r", "app", "anonimal_lite", "-q"])
    assert r.returncode == 0, f"bandit encontro problemas:\n{r.stdout}\n{r.stderr}"


def test_pip_audit_sin_vulnerabilidades():
    if not _have("pip_audit"):
        return "SKIP: pip-audit no instalado"
    r = _run(["pip_audit", "-r", "requirements.txt"])
    if r.returncode != 0:
        blob = r.stdout + r.stderr
        if any(m in blob for m in NET_MARKERS):
            return "SKIP: pip-audit sin red (no se pudo consultar la base OSV)"
        raise AssertionError(f"pip-audit encontro vulnerabilidades:\n{blob}")


def test_mypy_sin_errores_de_tipos():
    if not _have("mypy"):
        return "SKIP: mypy no instalado"
    r = _run(["mypy"])  # usa files=[app, anonimal_lite] del pyproject
    assert r.returncode == 0, f"mypy encontro errores:\n{r.stdout}\n{r.stderr}"


def test_smoke_arranca_y_anonimiza():
    # Levanta uvicorn real y prueba /health + /anonymize (ver scripts/smoke.py).
    if not (_have("uvicorn") and _have("httpx")):
        return "SKIP: uvicorn/httpx no instalados"
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "smoke.py")],
                       cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, f"smoke fallo:\n{r.stdout}\n{r.stderr}"


def test_detect_secrets_sin_secretos():
    if not _have("detect_secrets"):
        return "SKIP: detect-secrets no instalado"
    r = _run(["detect_secrets", "scan",
              "--exclude-files", r"\.venv/",
              "--exclude-files", "brand/",
              "--exclude-files", r"\.secrets\.baseline"])
    assert r.returncode == 0, f"detect-secrets fallo:\n{r.stderr}"
    results = json.loads(r.stdout).get("results", {})
    assert not results, f"detect-secrets encontro posibles secretos: {list(results)}"
