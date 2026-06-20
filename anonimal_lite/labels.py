"""Taxonomía de etiquetas del ecosistema.

Cada `label` que producen los motores se mapea a:
  - un **tipo** legible para los tokens de reemplazo («PERSONA_1», «ID_2»…),
    alineado con el que ya usa Escriba (paridad de salida).
  - un **placeholder** estilo OPF (`<PRIVATE_PERSON>`…), que es lo que esperan
    los consumidores actuales (Escriba/Fisherboy) en el contrato legacy.
"""
from __future__ import annotations

# label -> (tipo, placeholder)
_LABELS: dict[str, tuple[str, str]] = {
    "EMAIL":       ("EMAIL", "<PRIVATE_EMAIL>"),
    "PHONE":       ("TEL", "<PRIVATE_PHONE>"),
    "PERSON":      ("PERSONA", "<PRIVATE_PERSON>"),
    "ADDRESS":     ("DOMICILIO", "<PRIVATE_ADDRESS>"),
    "AR_DNI":      ("ID", "<ACCOUNT_NUMBER>"),
    "AR_CUIT":     ("ID", "<ACCOUNT_NUMBER>"),
    "AR_CBU":      ("ID", "<ACCOUNT_NUMBER>"),
    "CREDIT_CARD": ("ID", "<ACCOUNT_NUMBER>"),
    "ACCOUNT":     ("ID", "<ACCOUNT_NUMBER>"),
    "URL":         ("URL", "<PRIVATE_URL>"),
    "DATE":        ("FECHA", "<PRIVATE_DATE>"),
    "SECRET":      ("SECRETO", "<SECRET>"),
    "IPV4":        ("IP", "<REDACTED>"),
    "CUSTOM":      ("DATO", "<REDACTED>"),
}
_DEFAULT = ("DATO", "<REDACTED>")

# placeholder OPF -> label propia (para mapear la salida del motor ML).
PLACEHOLDER_TO_LABEL: dict[str, str] = {
    "<PRIVATE_PERSON>": "PERSON",
    "<PRIVATE_ADDRESS>": "ADDRESS",
    "<PRIVATE_EMAIL>": "EMAIL",
    "<PRIVATE_PHONE>": "PHONE",
    "<ACCOUNT_NUMBER>": "ACCOUNT",
    "<PRIVATE_DATE>": "DATE",
    "<PRIVATE_URL>": "URL",
    "<SECRET>": "SECRET",
    "<REDACTED>": "CUSTOM",
}

# tipos que se enmascaran como número (conservan los últimos dígitos).
NUMERIC_TYPES = frozenset({"ID", "TEL", "IP"})


def type_of(label: str) -> str:
    return _LABELS.get(label, _DEFAULT)[0]


def placeholder_of(label: str) -> str:
    return _LABELS.get(label, _DEFAULT)[1]
