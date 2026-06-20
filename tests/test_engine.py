"""Tests del motor (stdlib, sin modelo ML). Corren con pytest o con el runner
propio `python -m tests.run_tests`."""
import csv
import io
import json

from anonimal_lite import formats
from anonimal_lite.lite_engine import LiteEngine
from anonimal_lite.modes import Anonymizer, deanonymize

ENG = LiteEngine()


def _labels(text):
    return [s.label for s in ENG.detect(text)]


def test_email_detection():
    spans = ENG.detect("escribime a juan.perez@acme.com.ar dale")
    assert any(s.label == "EMAIL" and s.text == "juan.perez@acme.com.ar" for s in spans)


def test_cuit_valid_detected_invalid_ignored():
    assert "AR_CUIT" in _labels("CUIT 20-12345678-6 listo")        # digito verificador ok
    assert "AR_CUIT" not in _labels("nro 20-12345678-0")            # digito verificador mal


def test_cbu_22_digits():
    assert "AR_CBU" in _labels("CBU 0170099220000067797370 para transferir")


def test_dni_dotted_and_context():
    assert "AR_DNI" in _labels("mi DNI es 12.345.678")
    assert "AR_DNI" in _labels("documento 30123456")


def test_credit_card_luhn():
    assert "CREDIT_CARD" in _labels("tarjeta 4111 1111 1111 1111")   # Luhn ok
    assert "CREDIT_CARD" not in _labels("nro 4111 1111 1111 1112")   # Luhn mal


def test_pseudo_consistency_and_roundtrip():
    text = "mail juan@acme.com y otra vez juan@acme.com, ademas ana@x.com"
    anon = Anonymizer("pseudo")
    out = anon.process(text, ENG.detect(text))
    assert out.count("EMAIL_1") == 2 and "EMAIL_2" in out          # mismo valor, mismo token
    assert "juan@acme.com" not in out
    assert deanonymize(out, anon.mapping) == text                  # reversible


def test_typed_anon_mask_hash():
    text = "contacto juan@acme.com"
    assert "[EMAIL]" in Anonymizer("typed").process(text, ENG.detect(text))
    assert "<<ANOM_DATA>>" in Anonymizer("anon").process(text, ENG.detect(text))
    masked = Anonymizer("mask").process(text, ENG.detect(text))
    assert "j•••@acme.com" in masked and "juan@acme.com" not in masked  # mask type-aware
    a = Anonymizer("hash").process(text, ENG.detect(text))
    b = Anonymizer("hash").process(text, ENG.detect(text))
    assert a == b and "juan@acme.com" not in a                     # determinista (HMAC), no reversible
    assert Anonymizer("hash").mapping == {}                        # hash no expone mapa


def test_mask_keeps_last_digits():
    masked = Anonymizer("mask").process("tarjeta 4111 1111 1111 1111", ENG.detect("tarjeta 4111 1111 1111 1111"))
    assert masked.rstrip().endswith("1111") and "•" in masked


def test_deanonymize_longest_token_first():
    mapping = {"«EMAIL_1»": "a@b.com", "«EMAIL_12»": "c@d.com"}
    assert deanonymize("«EMAIL_12» y «EMAIL_1»", mapping) == "c@d.com y a@b.com"


def test_csv_preserves_columns():
    src = "nombre,email\nJuan Perez,juan@acme.com\nAna,ana@x.com\n"
    out = formats.anonymize_csv(src, ENG, Anonymizer("pseudo"))
    rows = list(csv.reader(io.StringIO(out)))
    assert rows[0] == ["nombre", "email"]            # header intacto
    assert len(rows) == 3 and all(len(r) == 2 for r in rows)
    assert "juan@acme.com" not in out and "EMAIL_1" in out


def test_json_preserves_structure():
    src = json.dumps({"user": {"email": "a@b.com"}, "items": [1, 2, 3]})
    out = formats.anonymize_json(src, ENG, Anonymizer("pseudo"))
    data = json.loads(out)                            # sigue siendo JSON valido
    assert data["items"] == [1, 2, 3]                 # numeros intactos
    assert "email" in data["user"]                    # clave intacta
    assert data["user"]["email"] != "a@b.com"         # valor anonimizado


def test_cbu_not_split_into_phone():
    spans = ENG.detect("CBU 0170099220000067797370")
    cbu = [s for s in spans if s.label == "AR_CBU"]
    assert len(cbu) == 1
    # nada se solapa con el CBU
    assert not any(s.label != "AR_CBU" and not (s.end <= cbu[0].start or s.start >= cbu[0].end)
                   for s in spans)


def test_propagacion_marca_todas_las_apariciones():
    from anonimal_lite.base import Span, finalize
    out = finalize("Juan y Juan", [Span("PERSON", 0, 4, "Juan")])
    assert sorted((s.start, s.end) for s in out) == [(0, 4), (7, 11)]


def test_normalize_une_guion_de_pdf():
    from anonimal_lite.base import normalize
    assert normalize("CUIT 20-\n12345678-6") == "CUIT 20-12345678-6"
