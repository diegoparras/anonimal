# ============================================================================
#  Anonimal — imagen FULL (motor ML: OpenAI Privacy Filter).
#  El checkpoint se HORNEA en la imagen (capa estable) -> cero descarga en
#  runtime, listo en cada boot. Imagen pesada (~6-7 GB) y CPU-bound.
#  Para una imagen liviana sin modelo, ver Dockerfile.lite.
# ============================================================================
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    OPF_DEVICE=cpu \
    ANONIMAL_ENGINE=auto \
    # RAM: cap de arenas de glibc (torch en CPU fragmenta el heap y dispara el RSS)
    # + threads acotados. Bajan el RSS sin tocar el modelo. Overridables en el panel.
    MALLOC_ARENA_MAX=2 \
    OMP_NUM_THREADS=4 \
    # Cuantización int8 del modelo OPF al cargar (ver opf_engine). Apagable con =0.
    ANONIMAL_QUANTIZE=1

WORKDIR /app

# git: para instalar OPF desde su repo.  curl: para el HEALTHCHECK.
RUN apt-get update && apt-get install -y --no-install-recommends git curl \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# torch CPU-only PRIMERO: OPF corre en CPU; asi evitamos ~2,5 GB de CUDA inutil.
# Instalando OPF despues, ve torch ya satisfecho y no baja la variante CUDA.
RUN pip install --upgrade pip setuptools wheel \
 && pip install --index-url https://download.pytorch.org/whl/cpu torch \
 && pip install -r requirements.txt \
 && pip install "git+https://github.com/openai/privacy-filter.git" \
 && python -c "import torch; assert torch.version.cuda is None, 'se colo torch CUDA'; print('torch CPU', torch.__version__)"

# Usuario NO-root, creado antes del horneado para que el checkpoint quede en su
# HOME y sea de su propiedad (sin chown de 2,8 GB en runtime).
RUN useradd -m -u 10001 anon
USER anon
ENV HOME=/home/anon \
    HF_HOME=/home/anon/.cache/huggingface

# --- Horneado del checkpoint (~2,8 GB) en una capa ESTABLE ------------------
RUN for i in 1 2 3 4 5; do \
      python -c "from opf._common.checkpoint_download import ensure_default_checkpoint; print('checkpoint:', ensure_default_checkpoint())" && break; \
      echo "Reintento de descarga de OPF ($i)..."; sleep 30; \
    done \
 && python -c "from opf import OPF; OPF(device='cpu', output_mode='typed').redact('warm-up')" \
 && test -d /home/anon/.opf/privacy_filter

COPY anonimal_lite/ ./anonimal_lite/
COPY app/ ./app/

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=5 \
  CMD curl -fsS http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
