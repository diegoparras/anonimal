"""Reglas propias del usuario (RuledEngine): 'always' agrega, 'never' excluye."""
from app.engine.lite_engine import LiteEngine
from app.engine.modes import Anonymizer
from app.engine.rules import RuledEngine

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
