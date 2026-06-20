"""Invariante de privacidad: ningun valor original de PII debe sobrevivir en la
salida, en NINGUN modo. Es la red de seguridad del producto: que Anonimal nunca
'deje pasar' un dato que detecto.

El motor lite ve PII estructurada (mail, telefono, tarjeta, DNI, CUIT, CBU, IP);
nombres/direcciones libres son del motor ML y no se prueban aca.
"""
from anonimal_lite.lite_engine import LiteEngine
from anonimal_lite.modes import MODES, Anonymizer, deanonymize

ENG = LiteEngine()

PII = [
    "juan.perez@acme.com",
    "20-12345678-6",                  # CUIT valido
    "0170099220000067797370",         # CBU (22 digitos)
    "4111 1111 1111 1111",            # tarjeta (Luhn ok)
    "+54 11 4123-4567",               # telefono
]
TEXT = (
    "Contacto: juan.perez@acme.com, CUIT 20-12345678-6, "
    "CBU 0170099220000067797370, tarjeta 4111 1111 1111 1111, "
    "tel +54 11 4123-4567."
)


def test_todos_los_valores_son_detectados():
    # Si algo no se detecta, despues se filtraria: lo exigimos explicito.
    spans_text = {s.text for s in ENG.detect(TEXT)}
    for value in PII:
        assert value in spans_text, f"no se detecto la PII: {value!r}"


def test_ningun_valor_original_sobrevive_en_ningun_modo():
    for mode in MODES:
        out = Anonymizer(mode).process(TEXT, ENG.detect(TEXT))
        for value in PII:
            assert value not in out, f"modo {mode}: quedo PII original {value!r}"


def test_pseudo_roundtrip_recupera_exacto():
    anon = Anonymizer("pseudo")
    out = anon.process(TEXT, ENG.detect(TEXT))
    assert deanonymize(out, anon.mapping) == TEXT
