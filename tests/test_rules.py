"""Reglas propias del usuario (RuledEngine): 'always' agrega, 'never' excluye."""
from anonimal_lite.lite_engine import LiteEngine
from anonimal_lite.modes import Anonymizer
from anonimal_lite.rules import RuledEngine

BASE = LiteEngine()


def test_always_agrega_y_never_excluye():
    eng = RuledEngine(BASE, always=["Proyecto Fenix"], never=["ana@x.com"])
    text = "Proyecto Fenix con juan@acme.com y ana@x.com"
    pairs = {(s.label, s.text) for s in eng.detect(text)}
    assert ("CUSTOM", "Proyecto Fenix") in pairs       # always agrega
    assert ("EMAIL", "juan@acme.com") in pairs         # deteccion normal sigue
    assert ("EMAIL", "ana@x.com") not in pairs          # never excluye


def test_custom_se_anonimiza_en_la_salida():
    eng = RuledEngine(BASE, always=["Fenix"])
    text = "El proyecto Fenix arranca"
    out = Anonymizer("pseudo").process(text, eng.detect(text))
    assert "Fenix" not in out and "«DATO_1»" in out  # CUSTOM -> tipo DATO


def test_sin_reglas_no_cambia_la_deteccion():
    eng = RuledEngine(BASE, always=[], never=[])
    text = "mail juan@acme.com"
    assert [s.text for s in eng.detect(text)] == [s.text for s in BASE.detect(text)]


def test_regex_pattern_oculta_con_su_tipo():
    eng = RuledEngine(BASE, patterns=[{"regex": r"LEG-\d{4}", "placeholder": "ID"}])
    text = "empleado LEG-1234 en el sistema"
    out = Anonymizer("pseudo").process(text, eng.detect(text))
    assert "LEG-1234" not in out and "«ID_1»" in out   # placeholder -> tipo del token


def test_regex_invalido_se_ignora():
    # Una regex rota no debe romper la corrida (se saltea ese patrón).
    eng = RuledEngine(BASE, patterns=[{"regex": "([a-z", "placeholder": "X"}])
    spans = eng.detect("texto normal sin pii")
    assert isinstance(spans, list)


def test_regex_redos_no_cuelga():
    """ReDoS: un patrón catastrófico del usuario no debe colgar el worker (auditoría 2026-06).

    El motor seguro (re2 lineal, o `regex` con timeout) acota el backtracking; el
    patrón se saltea fail-safe en vez de explotar."""
    import time
    eng = RuledEngine(BASE, patterns=[{"regex": r"(a|a)+$", "placeholder": "X"}])
    evil = "a" * 60 + "!"
    t = time.time()
    spans = eng.detect(evil)            # no debe colgar
    assert isinstance(spans, list)
    assert time.time() - t < 5.0        # acotado (timeout 1s/patrón + margen)
