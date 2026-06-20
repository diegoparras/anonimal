# Desplegar Anonimal

Anonimal corre **local / self-hosted**: el dato nunca sale de tu infraestructura.
Hay dos imágenes — elegí según el caso:

| Imagen | Tag | Pesa | Detecta | Cuándo |
|---|---|---|---|---|
| **full** (ML) | `:latest`, `:<ver>` | ~6-7 GB + ~3 GB RAM | estructurado **+ nombres/direcciones** (OPF) | reemplazar al Anonimal del ecosistema; máxima cobertura |
| **lite** (regex) | `:lite`, `:<ver>-lite` | decenas de MB | estructurado (mail, tel, tarjeta, DNI, CUIT, CBU, secrets) | instalación liviana, sin ML; no ve nombres libres |

> Para reemplazar al Anonimal que usa **Escriba**, usá la **full**: la lite no
> detecta nombres/direcciones y se perdería cobertura.

Formas de desplegar, de más simple a más controlada:

1. [Docker (un comando)](#1-docker-un-comando)
2. [Docker Compose](#2-docker-compose)
3. [EasyPanel](#3-easypanel) — la del servidor propio
4. [Dentro del ecosistema (detrás de Escriba)](#4-dentro-del-ecosistema-detras-de-escriba)
5. [Desarrollo local](#5-desarrollo-local)

Después: [variables de entorno](#variables-de-entorno), [recursos](#recursos) y
[checklist de producción](#checklist-de-produccion).

---

## 1. Docker (un comando)

```bash
# Lite (arranca al instante)
docker run -d --name anonimal -p 8920:8000 ghcr.io/diegoparras/anonimal-svc:lite

# Full (ML; la primera vez tarda en cargar el modelo a RAM)
docker run -d --name anonimal -p 8920:8000 ghcr.io/diegoparras/anonimal-svc:latest
```

Probar:

```bash
curl -s localhost:8920/health
curl -s localhost:8920/anonymize -H "Content-Type: application/json" \
  -d '{"text":"mail juan@acme.com, CUIT 20-12345678-6","mode":"pseudo"}'
```

La UI web queda en <http://localhost:8920>.

> ¿No tenés la imagen publicada todavía? Ver
> [publicar la imagen](#publicar-la-imagen-ghcr), o construí local:
> `docker build -t anonimal:lite -f Dockerfile.lite .` (o `Dockerfile` para full).

---

## 2. Docker Compose

El repo trae `docker-compose.yml`:

```bash
docker compose up -d anonimal              # full  -> http://localhost:8920
docker compose --profile lite up -d anonimal-lite   # lite -> http://localhost:8921
```

Detener: `docker compose down`. Logs: `docker compose logs -f`.

---

## 3. EasyPanel

Dos rutas. La **A (imagen)** es la recomendada para producción; la **B (build)**
sirve si no querés publicar la imagen primero.

### Ruta A — desde la imagen de GHCR (recomendada)

Requisito: la imagen tiene que estar **publicada y accesible** (ver
[publicar la imagen](#publicar-la-imagen-ghcr); si el package es privado, cargá
las credenciales del registry en EasyPanel).

1. En tu proyecto de EasyPanel, **Create → App**.
2. **Source → Docker Image**: `ghcr.io/diegoparras/anonimal-svc:latest` (full) o
   `:lite`.
3. **Port**: el contenedor expone **8000**.
4. **Environment** (ver tabla abajo). Mínimo recomendado si lo vas a exponer:
   `ANONIMAL_TOKEN=<secreto largo>` y `ANON_HASH_KEY=<secreto largo>`.
5. **Resources** (solo full): asigná **~6 GB de RAM** (el modelo es residente) y
   disco para la imagen.
6. **Deploy**. El healthcheck (`GET /health`) confirma que levantó; en la full,
   `model_loaded` pasa a `true` cuando termina de cargar el modelo en background.

> **Si es para el ecosistema (lo usa Escriba): NO le pongas dominio público.**
> Dejalo en la red interna del proyecto y que Escriba lo llame por el hostname
> interno (ver sección 4). Anonimal **no tiene login**; su única protección al
> exponerse es `ANONIMAL_TOKEN` + TLS por reverse proxy.

### Ruta B — build desde el repo de GitHub

1. **Create → App → Source → GitHub**: `diegoparras/anonimal`, rama `main`.
2. **Build → Dockerfile**: `Dockerfile` (full) o `Dockerfile.lite` (lite).
3. Port **8000** + Environment igual que arriba. Deploy.

> La **full** baja el modelo (~2,8 GB) al construir: el build tarda y necesita
> disco/tiempo. La **lite** construye en segundos. Si el build de la full te
> complica en EasyPanel, usá la Ruta A con la imagen ya construida por el CI.

---

## 4. Dentro del ecosistema (detrás de Escriba)

Anonimal es el especialista de privacidad del ecosistema **Escriba**. Escriba
(y opcionalmente el worker de Fisherboy) lo llaman por HTTP.

1. Desplegá Anonimal **full** en el mismo proyecto/red de EasyPanel que Escriba,
   **sin dominio público** (sección 3, Ruta A).
2. En el servicio de **Escriba**, seteá `ANONIMAL_URL` al hostname interno, p. ej.
   `http://anonimal:8000`.
3. Listo: Escriba lo usa para anonimizar. **Compatibilidad:** este Anonimal expone
   el contrato viejo (`POST /anonymize {text}` → `detected_spans`) cuando se llama
   **sin `mode`**, así que reemplaza al Anonimal embebido **sin cambiar una línea
   en Escriba** (ver `docs/ARCHITECTURE.md`).

---

## 5. Desarrollo local

```bash
pip install -r requirements.txt          # motor lite, sin modelo
uvicorn app.main:app --reload            # http://localhost:8000
python -m tests.run_tests                # tests
```

Para el motor ML local: `pip install "git+https://github.com/openai/privacy-filter.git"`
(pesado) y `ANONIMAL_ENGINE=ml`.

---

## Variables de entorno

| Variable | Default | Para qué |
|---|---|---|
| `ANONIMAL_ENGINE` | `auto` | `auto` (ML si está listo, si no lite) · `lite` · `ml` |
| `ANONIMAL_MODE` | `pseudo` | modo por defecto de la API/UI |
| `ANONIMAL_TOKEN` | (vacío) | si se setea, se exige en cada request (`Authorization: Bearer` o `X-Anonimal-Token`) |
| `ANON_HASH_KEY` | (aleatoria por proceso) | clave del modo `hash`; seteala para seudónimos **estables** entre reinicios |
| `ANONIMAL_MAX_CHARS` | `500000` | tope de texto (más → 413) |
| `ANONIMAL_MAX_PDF_BYTES` | `26214400` (25 MB) | tope de PDF a redactar |
| `OPF_DEVICE` | `cpu` | `cpu` o `cuda` (solo imagen full) |
| `OPF_CHECKPOINT` | (default) | ruta a un checkpoint OPF propio (solo full) |

---

## Recursos

- **lite:** unas decenas de MB de imagen, RAM mínima. Arranca al instante.
- **full:** imagen ~6-7 GB, **~3 GB de RAM fijos** por el modelo residente, y es
  CPU-bound (la inferencia comparte cores). Dale ~6 GB de RAM al contenedor.

---

## Checklist de producción

- [ ] ¿Se expone a una red/internet? → `ANONIMAL_TOKEN` **obligatorio** + reverse
      proxy con **TLS** adelante. Si es interno del ecosistema, mejor **sin
      dominio público**.
- [ ] `ANON_HASH_KEY` seteada (si usás el modo `hash` y querés linkage estable).
- [ ] Recursos acordes (full ≈ 6 GB RAM).
- [ ] La imagen corre como usuario **no-root** (ya viene así).
- [ ] Healthcheck `GET /health` verde.
- [ ] Antes de publicar/actualizar la imagen, pasó el **gate** (ver
      `SECURITY.md` y el CI): tests + ruff/mypy/bandit/pip-audit/detect-secrets +
      Trivy sobre la imagen.

---

## Publicar la imagen (GHCR)

Las imágenes las construye y publica el CI (`.github/workflows/release.yml`)
cuando se corta un **tag** `v*`:

```bash
git tag v0.3.0      # el número lo decidís vos
git push origin v0.3.0
```

Eso buildea y empuja `ghcr.io/diegoparras/anonimal-svc:latest` (+ `:<ver>`) y
`:lite` (+ `:<ver>-lite`), con smoke + Trivy como gate antes de publicar. Después,
en GitHub, hacé **público** el package (Packages → **anonimal-svc** → Package
settings → Change visibility) si querés que EasyPanel lo baje sin credenciales.

> **Nota del nombre:** se publica como **`anonimal-svc`** porque el package
> `anonimal` está ocupado por la imagen vieja (Anonimal embebido) y su ACL no deja
> que este repo escriba. Para consolidar a `anonimal`: borrar el package viejo en
> GHCR y cambiar `IMAGE` en `release.yml` a `ghcr.io/diegoparras/anonimal`.
