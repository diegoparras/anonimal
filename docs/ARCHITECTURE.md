# Arquitectura de Anonimal

## Decision del ecosistema (2026-06-20)

El anonimato es **competencia exclusiva de Anonimal**. Escriba, Fisherboy y
Extracta dejan de tener logica de anonimizacion propia y la delegan en Anonimal.

Se separan dos cosas que antes estaban mezcladas:

- **Capacidad** (el codigo que anonimiza) -> vive solo en Anonimal.
- **Flujo** (quien llama a quien) -> dos carriles:
  - **Humano (handoff):** Extracta -> Escriba y Fisherboy -> Escriba (contrato
    `sessionStorage['escriba.handoff']`). Dentro de Escriba, el boton
    "Anonimizar" llama a la API de Anonimal.
  - **Automatico (API directa):** un proceso sin humano (el worker de Fisherboy
    scrapeando a escala, o Anonimal usado solo) llama a la API de Anonimal
    directo, sin obligar a meter a Escriba en el medio.

Asi cada herramienta sigue siendo standalone y Anonimal es el unico dueño del
anonimato, pero accesible como servicio compartido (no escondido detras de
Escriba).

## Motor: "detecta, no decide"

Un motor solo DETECTA (`detect(text) -> [Span]`). El reemplazo lo decide
`engine/modes.py`. Hay dos motores:

- **lite** (`lite_engine.py`): solo regex. Liviano, offline, sin modelo. Cubre
  datos estructurados (mail, telefono, tarjeta con Luhn, URL, IPv4, secrets) y
  LATAM (`latam.py`: DNI, CUIT/CUIL con digito verificador, CBU). No ve nombres
  ni direcciones libres.
- **ml** (`opf_engine.py`): envuelve OpenAI Privacy Filter (OPF, Apache-2.0).
  Preciso para PII libre. Pesado (~2,8 GB checkpoint, ~5 GB RAM), CPU-bound,
  carga perezosa en background, inferencia serializada.

Seleccion (`ANONIMAL_ENGINE`): `auto` (ML si esta listo, si no lite) | `lite` |
`ml`. Solapes entre detecciones se resuelven en `base.resolve_overlaps` (gana el
span mas largo; a igual largo, mayor prioridad de etiqueta).

## Modos de reemplazo (`modes.py`)

| Modo | Resultado | Reversible |
|---|---|---|
| `typed` | `[EMAIL]` (placeholder por categoria) | no |
| `anon` | `«REDACTADO»` (token unico para todo) | no |
| `pseudo` | `EMAIL_1` (seudonimo estable, numerado) | **si** (guarda mapa) |
| `mask` | `j***@***.com` / `****-****-****-1234` | no |
| `hash` | `EMAIL_a1b2c3d4e5` (hash determinista) | no |

Consistencia: un `Anonymizer` por documento -> el mismo valor recibe siempre el
mismo reemplazo. Solo `pseudo` expone `mapping` (token->original) para
re-identificar con `deanonymize()`.

## Formatos (`formats.py`)

Anonimizacion que preserva el formato de archivos que YA son texto: txt, md,
log, srt, html (texto plano), **csv** (anonimiza celdas, mantiene columnas),
**json** (anonimiza valores string, nunca claves; sigue siendo JSON valido). Un
unico `Anonymizer` por archivo -> consistencia y mapa de reversion para todo el
documento.

Lo que Anonimal **no** hace: convertir Word/Excel/imagenes/audio/URL. Eso es
Escriba/Extracta/Fisherboy; el texto ya convertido llega anonimizable.

## API

| Metodo | Ruta | Que hace |
|---|---|---|
| GET | `/health` | estado + disponibilidad del motor ML |
| POST | `/detect` | `{text}` -> spans detectados |
| POST | `/anonymize` | `{text, mode, engine?}` -> `{output, map, summary}` |
| POST | `/deanonymize` | `{text, map}` -> texto original |
| POST | `/anonymize_file` | archivo + `mode` -> contenido anonimizado (mismo formato) |

## Seguridad

Pensado para correr LOCAL. Si se expone: `ANONIMAL_TOKEN` obligatorio + reverse
proxy con TLS. Topes de tamaño (`ANONIMAL_MAX_CHARS`). Usuario no-root en la
imagen. El dato nunca sale de la maquina (todo el procesamiento es local).

## Plan de migracion (fases siguientes)

1. **Standalone primero, funcionando** (esta fase).
2. UI web.
3. CI -> GHCR (full + lite).
4. **Recien entonces** migrar Escriba (saca sus 5 modos + redaccion PDF) y
   Fisherboy (saca su regex casero + su llamada directa) para que consuman esta
   API. Extracta ya no anonimiza (a confirmar). Nunca se rompe lo deployado: se
   da vuelta la llave de cada uno solo cuando Anonimal ya esta arriba.
