"""Novedades por version: salen del CHANGELOG.md (una sola fuente) y se muestran en el log de
arranque (deploy en EasyPanel), en la UI al entrar despues de una actualizacion y en el Release.

Funciones planas sin fixtures: corren con pytest y con tests/run_tests.py (stdlib)."""
import contextlib
import io
import re
import tempfile
import tomllib
from pathlib import Path

from fastapi.testclient import TestClient

import app.novedades as nov
from app.main import app

RAIZ = Path(__file__).resolve().parent.parent

MUESTRA = """# Changelog

Formato basado en Keep a Changelog.

## [0.3.0] - 2026-11-21

### Nuevo
- **Novedades** en la UI: se ven al entrar
  despues de una actualizacion (`GET /api/novedades`).

### Corregido
- Un arreglo corto.

## [0.2.1] - 2026-11-20

### Corregido
- Otro arreglo.

## [No publicado]

### Nuevo
- Esto no es una version.

## [0.2.0] — Algo grande

- Item sin seccion.
"""


def test_parsea_versiones_fechas_secciones_e_items_multilinea():
    v = nov.parsear(MUESTRA)
    assert [x["version"] for x in v] == ["0.3.0", "0.2.1", "0.2.0"]
    assert v[0]["fecha"] == "2026-11-21" and v[2]["fecha"] is None
    assert [s["titulo"] for s in v[0]["secciones"]] == ["Nuevo", "Corregido"]
    assert v[0]["secciones"][0]["items"] == [
        "**Novedades** en la UI: se ven al entrar despues de una actualizacion (`GET /api/novedades`)."
    ]
    assert nov.lineas_log(v[2]) == ["Item sin seccion."], "items sin ### (formato viejo del CHANGELOG)"
    assert nov.notas_markdown(v[2]) == "- Item sin seccion.\n"


def test_desde_la_ultima_vista_hasta_la_actual():
    v = nov.parsear(MUESTRA)
    assert [x["version"] for x in nov.desde(v, "0.2.0", "0.3.0")] == ["0.3.0", "0.2.1"]
    assert nov.desde(v, "0.3.0", "0.3.0") == [], "ya vista: nada que mostrar"
    assert [x["version"] for x in nov.desde(v, None, "0.3.0")] == ["0.3.0"], "primera vez: solo la actual"
    assert [x["version"] for x in nov.desde(v, "0.2.0", "0.2.1")] == ["0.2.1"], "nunca posteriores a la que corre"
    assert nov.desde(v, "0.10.0", "0.3.0") == [], "compara como version, no como texto"
    assert nov.comparar("1.0.0", "basura") > 0


def test_texto_plano_para_el_log_y_markdown_para_el_release():
    v = nov.parsear(MUESTRA)[0]
    assert nov.lineas_log(v) == [
        "Nuevo: Novedades en la UI: se ven al entrar despues de una actualizacion (GET /api/novedades).",
        "Corregido: Un arreglo corto.",
    ]
    md = nov.notas_markdown(v)
    assert re.match(r"^### Nuevo\n- \*\*Novedades\*\* en la UI", md)
    assert "### Corregido\n- Un arreglo corto." in md


def test_cartel_de_arranque_cortado_al_ancho():
    v = nov.parsear(MUESTRA)
    lineas = nov.cartel_arranque("0.3.0", v, 60)
    assert all(len(x) <= 60 for x in lineas), "ningun renglon pasa el ancho"
    assert re.fullmatch(r"=+", lineas[0])
    assert lineas[1] == "ANONIMAL v0.3.0  (2026-11-21)"
    assert lineas[2] == "Que cambia en esta version:"
    assert lineas[3] == "- Nuevo: Novedades en la UI: se ven al entrar despues de una"
    assert re.match(r"^ {4}actualizacion", lineas[4]), "la continuacion queda sangrada"
    assert re.fullmatch(r"=+", lineas[-1])
    assert all("**" not in x and "`" not in x for x in lineas), "sin markdown"
    sin = nov.cartel_arranque("9.9.9", v, 60)
    assert sin[1] == "ANONIMAL v9.9.9"
    assert sin[2] == "Sin notas para esta version en el CHANGELOG."


def test_sin_changelog_ni_version_no_rompe():
    with tempfile.TemporaryDirectory() as d:
        falta = Path(d) / "no-existe.md"
        assert nov.todas(falta) == []
        assert nov.version_de(Path(d) / "pyproject.toml") is None
        assert "Sin notas para esta version en el CHANGELOG." in nov.cartel_arranque("1.2.3", nov.todas(falta))


def test_cli_cartel_notas_y_version():
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        assert nov._main([]) == 0
    primeras = out.getvalue().splitlines()
    assert primeras[1].startswith(f"[anonimal] ANONIMAL v{nov.version_instalada()}")
    assert all(x.startswith("[anonimal] ") for x in primeras)
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        assert nov._main(["--version"]) == 0
    assert out.getvalue() == nov.version_instalada()
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        assert nov._main(["notas"]) == 0
    assert out.getvalue().startswith("### ")


def test_endpoint_novedades():
    client = TestClient(app)
    d = client.get("/novedades").json()
    assert d["version"] == nov.version_instalada()
    assert [v["version"] for v in d["versiones"]] == [d["version"]]
    assert client.get(f"/novedades?desde={d['version']}").json()["versiones"] == [], "ya vista"
    assert len(client.get("/novedades?desde=<x>").json()["versiones"]) == 1, "desde invalido se ignora"
    assert client.get("/novedades?todas=1").json()["versiones"][0]["version"] == d["version"]
    # La UI recibe la version real (no la fija del HTML).
    assert f'content="{d["version"]}"' in client.get("/").text


def test_el_changelog_real_tiene_la_seccion_de_la_version_actual():
    with (RAIZ / "pyproject.toml").open("rb") as f:
        version = tomllib.load(f)["project"]["version"]
    assert nov.version_instalada() == version
    v = nov.parsear((RAIZ / "CHANGELOG.md").read_text(encoding="utf-8"))
    actual = next((x for x in v if x["version"] == version), None)
    assert actual, f'falta "## [{version}]" en CHANGELOG.md'
    assert any(s["items"] for s in actual["secciones"]), f"la seccion {version} del CHANGELOG esta vacia"
    assert v[0]["version"] == version, "la version de pyproject.toml es la primera del CHANGELOG"
    cartel = nov.cartel_arranque(version, v)
    assert all(len(x) <= 80 for x in cartel)
    assert "Sin notas" not in "\n".join(cartel)
