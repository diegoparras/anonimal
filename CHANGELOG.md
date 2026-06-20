# Changelog

Formato basado en [Keep a Changelog](https://keepachangelog.com/es/1.0.0/).

## [No publicado]

### Fase 3.1 — Paridad de motor + endpoint legacy (compat)

Prepara la migración del ecosistema (Escriba/Fisherboy delegarán en Anonimal)
sin tocar todavía los repos deployados.

- **Paridad de salida con Escriba** en el motor:
  - taxonomía de etiquetas (`engine/labels.py`): cada label → tipo legible
    («PERSONA», «ID», «EMAIL»…) + placeholder estilo OPF (`<PRIVATE_*>`).
  - tokens pseudo `«TIPO_N»` y anon `<<ANOM_DATA>>` (contratos del ecosistema);
    `deanonymize` por regex de token (compatible con `restore` de Escriba).
  - máscara **type-aware** (`j•••@acme.com`, `••••78-6`) y **hash HMAC** estable
    (`ANON_HASH_KEY`).
  - **propagación** (un dato detectado se tapa en todas sus apariciones) y
    **normalización** de guiones de PDF, en `engine/base.finalize`.
  - reglas: whitelist normalizada (NFC + casefold).
- **Endpoint legacy (drop-in):** `POST /anonymize` SIN `mode` devuelve el
  contrato viejo `{detected_spans, redacted_text, summary}` con `placeholder`,
  igual que el Anonimal embebido → Escriba/Fisherboy pueden apuntar su
  `ANONIMAL_URL` al nuevo servicio sin cambiar una línea. Con `mode`, responde la
  API nueva.
- 35 tests en verde, cobertura 86%.

### Infra — Fase 2: publicación a GHCR (CI)

- `.github/workflows/release.yml`: al cortar un tag `v*` (o por `workflow_dispatch`)
  construye y **publica** a `ghcr.io/diegoparras/anonimal` la imagen **full**
  (`:latest`, `:<versión>`) y la **lite** (`:lite`, `:<versión>-lite`).
- Gate antes de publicar: smoke del contenedor (lite) + **Trivy** sobre cada
  imagen; si hay HIGH/CRITICAL no se pushea.
- `ci.yml` sigue como gate de PR (no publica). Versionado: el tag lo corta Diego.
- Pendiente (manual de Diego): hacer **público** el package en GHCR.

### 0.2.0 — Fase 1: UI web

Interfaz web servida por FastAPI, con el sistema de diseño del ecosistema
(índigo antifaz `#4a4e7c`, Inter, claro/oscuro con `[data-theme]`, sin emojis,
español neutro). i18n en 7 idiomas (es/en/fr/pt/it/zh/ja).

- Pegar texto → resaltado de los datos detectados + salida anonimizada, con
  selector de **modo** (5) y **motor**, y chips de resumen por categoría.
- Pestaña **Re-identificar** (texto anonimizado + mapa → original).
- **Reglas propias** (ocultar siempre / no ocultar nunca) — motor `RuledEngine`,
  param `rules` en `/detect` y `/anonymize`, `rules_json` en `/anonymize_file`.
- **Subir archivos** (uno o varios) preservando formato, con descarga por archivo.
- **Copiar / Descargar / Descargar mapa / Enviar a Escriba** (handoff
  `sessionStorage['escriba.handoff']`).
- **Redacción visual de PDF** (`/redact_pdf`, `app/pdf.py` con PyMuPDF): tachado
  real (apply_redactions) de los datos detectados + borrado de metadata
  (DocInfo + XMP). Control de subida de PDF en la UI.
- Backend: estáticos servidos, headers de seguridad (CSP), `/anonymize` ahora
  devuelve `spans` para resaltar.
- 32 tests en verde (motor + API + privacidad + reglas + PDF + calidad),
  cobertura 86%.

### 0.1.0 — Fase 0: motor + API (standalone)

Primer corte del producto standalone, extraido del microservicio que vivia
dentro de Escriba. **No toca Escriba/Fisherboy/Extracta.**

- Motor doble:
  - `lite` (solo regex, sin modelo): mail, telefono, tarjeta (Luhn), URL, IPv4,
    secrets, y detectores LATAM (DNI, CUIT/CUIL con digito verificador, CBU).
  - `ml` (OpenAI Privacy Filter): wrapper con carga perezosa en background e
    inferencia serializada. Opcional (solo si `opf` esta instalado).
- 5 modos de reemplazo: `typed`, `anon`, `pseudo` (reversible), `mask`, `hash`.
- Reversibilidad: el modo `pseudo` devuelve un mapa token->original;
  `/deanonymize` re-identifica.
- Anonimizacion de archivos preservando el formato: txt, md, log, srt, html,
  csv (mantiene columnas), json (mantiene estructura y claves).
- API FastAPI: `/health`, `/detect`, `/anonymize`, `/deanonymize`,
  `/anonymize_file`. Auth opcional por token (`ANONIMAL_TOKEN`).
- Empaquetado: imagen full (ML, ~6-7 GB) y lite (regex, liviana) + compose.
- 18 tests (motor + API) en verde.
- Calidad y seguridad como pruebas (runner local + CI `.github/workflows/ci.yml`):
  ruff + vulture (sin código redundante/muerto), mypy (tipos), bandit (SAST),
  pip-audit (vulns de deps), detect-secrets (no filtrar secretos), cobertura ≥85%
  (coverage), invariante de privacidad (`tests/test_privacy.py`), smoke real
  (`scripts/smoke.py`) y Trivy (scan de la imagen Docker en CI). Config en
  `pyproject.toml`, herramientas en `requirements-dev.txt`, `SECURITY.md` y
  `.secrets.baseline`. 28 tests en verde, cobertura 92%.

### Pendiente (proximas fases)
- Fase 1: UI web (fucsia, claro/oscuro, i18n x7, reglas propias, redaccion de
  PDF, "Enviar a Escriba").
- Fase 2: CI -> GHCR (`anonimal:latest` + `:lite`).
- Fase 3: migrar Escriba/Fisherboy a consumir esta API (sacarles el anonimato
  propio).
- Fase 4: README x7, publicar repo + package GHCR.
