# Changelog

Formato basado en [Keep a Changelog](https://keepachangelog.com/es/1.0.0/).

## [No publicado]

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
  ruff + vulture (sin código redundante/muerto), bandit (SAST), pip-audit (vulns
  de deps), detect-secrets (no filtrar secretos). Config en `pyproject.toml`,
  herramientas en `requirements-dev.txt`, `SECURITY.md` y `.secrets.baseline`.

### Pendiente (proximas fases)
- Fase 1: UI web (fucsia, claro/oscuro, i18n x7, reglas propias, redaccion de
  PDF, "Enviar a Escriba").
- Fase 2: CI -> GHCR (`anonimal:latest` + `:lite`).
- Fase 3: migrar Escriba/Fisherboy a consumir esta API (sacarles el anonimato
  propio).
- Fase 4: README x7, publicar repo + package GHCR.
