"""Motor ML: envuelve OpenAI Privacy Filter (OPF, Apache-2.0). Preciso para
nombres, direcciones y PII libre que el regex no puede ver. Pesado (~2.8 GB de
checkpoint, ~5 GB en RAM) y atado a CPU.

Carga perezosa y en background, igual que el microservicio original: el server
arranca al instante; la primera deteccion espera (o cae al lite) hasta que el
modelo este caliente. Inferencia serializada (un forward pass a la vez) para
proteger la RAM.
"""
from __future__ import annotations

import logging
import os
import threading

from anonimal_lite.base import Span, finalize
from anonimal_lite.labels import PLACEHOLDER_TO_LABEL

log = logging.getLogger("anonimal.opf")


def _maybe_quantize(opf) -> None:
    """Cuantización dinámica int8 de las capas Linear del modelo OPF: en CPU baja
    la RAM (los pesos Linear pasan de fp32 a int8) y suele acelerar la inferencia.
    Apagable con ANONIMAL_QUANTIZE=0. Si algo falla, sigue con el modelo fp32 (el
    arranque NUNCA se rompe por esto). El modelo vive en opf._runtime.model."""
    if os.getenv("ANONIMAL_QUANTIZE", "1").strip().lower() in ("0", "false", "no"):
        return
    try:
        import torch
        try:
            from torch.ao.quantization import quantize_dynamic
        except Exception:
            from torch.quantization import quantize_dynamic
        runtime = getattr(opf, "_runtime", None)
        model = getattr(runtime, "model", None)
        if runtime is None or not isinstance(model, torch.nn.Module):
            log.warning("Cuantización omitida: no encontré opf._runtime.model (torch.nn.Module).")
            return
        runtime.model = quantize_dynamic(model, {torch.nn.Linear}, dtype=torch.qint8)
        log.info("OPF: modelo cuantizado a int8 (capas Linear).")
    except Exception as e:  # nunca romper el arranque por la cuantización
        log.warning("Cuantización int8 no aplicada (sigo en fp32): %s", e)


class OpfEngine:
    name = "ml"

    def __init__(self, device: str | None = None):
        self.device = device or os.getenv("OPF_DEVICE", "cpu")
        self._opf = None
        self._error: str | None = None
        self._lock = threading.Lock()           # un redact() a la vez
        self._load_lock = threading.Lock()

    def start_background_load(self) -> None:
        threading.Thread(target=self._ensure_loaded, daemon=True).start()

    def _ensure_loaded(self) -> None:
        if self._opf is not None or self._error is not None:
            return
        with self._load_lock:
            if self._opf is not None or self._error is not None:
                return
            try:
                from opf import OPF
                if not os.getenv("OPF_CHECKPOINT"):
                    from opf._common.checkpoint_download import ensure_default_checkpoint
                    ensure_default_checkpoint()
                opf = OPF(device=self.device, output_mode="typed")
                _maybe_quantize(opf)            # int8 (Linear) para bajar la RAM en CPU
                opf.redact("warm-up")           # primer forward pass (ya cuantizado)
                self._opf = opf
            except Exception as e:
                self._error = str(e)

    def ready(self) -> bool:
        return self._opf is not None

    @property
    def error(self) -> str | None:
        return self._error

    def detect(self, text: str) -> list[Span]:
        self._ensure_loaded()
        if self._opf is None:
            raise RuntimeError(self._error or "El modelo OPF aun no esta listo.")
        with self._lock:
            result = self._opf.redact(text).to_dict()
        spans: list[Span] = []
        for s in result.get("detected_spans", []):
            start, end = int(s["start"]), int(s["end"])
            ph = s.get("placeholder", "")
            label = PLACEHOLDER_TO_LABEL.get(ph) or str(s.get("label", "PII")).upper()
            spans.append(Span(label, start, end, s.get("text", text[start:end])))
        return finalize(text, spans)


def is_available() -> bool:
    """True si la libreria `opf` esta instalada (sin cargar el modelo)."""
    import importlib.util
    return importlib.util.find_spec("opf") is not None
