# Anonimal — Identidad de marca

Anonimal es el guardián de privacidad del ecosistema **Escriba** (junto a
**Extracta** y **Fisherboy**). Detecta y enmascara datos personales (PII)
localmente, sobre CPU: *detecta, no decide*. La marca tiene que sentirse parte
de la misma suite —el "violín afinado"— pero con voz propia.

Reglas heredadas del ecosistema (no negociables):

- Tipografía **Inter Variable** (con fallback al stack del sistema).
- Modo **claro por defecto** + oscuro vía `[data-theme="dark"]`, persistencia y
  script anti-FOUC en `<head>`.
- **Sin emojis** en la UI: íconos de línea SVG.
- **Español neutro** (sin voseo).
- Cada app con **su acento propio**. El de Anonimal es el **fucsia magenta**.

---

## Acento de marca — Fucsia magenta

Los acentos ya tomados del ecosistema son **naranja/coral** (Escriba), **verde
esmeralda** (Fisherboy) y **azul→violeta/lavanda** (Extracta). El fucsia magenta
cae en un hueco totalmente libre de la rueda (hue ~335°): no se confunde con
ninguno, mantiene la energía saturada de la suite y lee perfecto con el isotipo
en blanco.

| Rol | Claro | Oscuro |
|---|---|---|
| Acento | `#d6336c` | `#f06595` |
| Acento (press / hover) | `#b02a59` | `#e64980` |
| Texto sobre acento | `#ffffff` | `#2a0f17` |

---

## Tokens (listos para pegar)

Mismo esquema que Escriba/Fisherboy: `:root` = oscuro, `[data-theme="light"]`
sobreescribe a claro.

```css
:root {
  --bg: #0f0a0c; --bg-2: #151013; --panel: #191317;
  --card: rgba(255,255,255,0.04); --card-2: rgba(255,255,255,0.022);
  --border: rgba(255,255,255,0.10); --hairline: rgba(255,255,255,0.16);
  --text: #f0edee; --muted: #9a8b90; --muted-2: #cdbfc4;
  --accent: #f06595; --accent-2: #e64980;
  --on-accent: #2a0f17;
  --ok: #3fb950; --warn: #d6a01a; --err: #f85149;
  --radius: 12px; --radius-lg: 16px;
  --ring: 0 0 0 3px rgba(240,101,149,.26);
  --shadow: 0 1px 2px rgba(0,0,0,.4), 0 8px 24px -12px rgba(0,0,0,.6);
  color-scheme: dark;
}
[data-theme="light"] {
  --bg: #fdf6f9; --bg-2: #ffffff; --panel: #ffffff;
  --card: rgba(30,15,22,0.028); --card-2: rgba(30,15,22,0.016);
  --border: rgba(30,15,22,0.10); --hairline: rgba(30,15,22,0.17);
  --text: #1c151a; --muted: #7b6b73; --muted-2: #453840;
  --accent: #d6336c; --accent-2: #b02a59;
  --on-accent: #ffffff;
  --ok: #1a7f37; --warn: #9a6700; --err: #cf222e;
  --ring: 0 0 0 3px rgba(214,51,108,.18);
  --shadow: 0 1px 2px rgba(30,15,22,.04), 0 12px 32px -16px rgba(30,15,22,.16);
  color-scheme: light;
}
```

`theme-color` recomendado: `#fdf6f9` (claro) / `#0f0a0c` (oscuro).

Fuente (igual que el resto del ecosistema):

```html
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@fontsource-variable/inter/index.css" />
```

```css
font-family: "Inter Variable","Inter",-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
letter-spacing: -.011em;
```

---

## Logo

- **`logo.svg`** / **`favicon.svg`** — isotipo 64×64, tile redondeado (`rx=15`)
  con el acento de fondo y la marca en blanco. Mismo formato que el resto del
  ecosistema.
- **`logo-wordmark.svg`** — lockup horizontal (isotipo + "Anonimal"). El texto
  usa `currentColor`, así adopta `--text` del tema donde se inserte.
- **`anonimal-lockup.svg`** / **`anonimal-lockup.png`** — lockup de presentación
  (texto negro, fondo transparente), mismo encuadre que el de Escriba. El PNG es
  720×240 @2x (1440×480) listo para componer.

**Concepto:** una cabeza de animal con una **barra de censura** sobre los ojos.
Une los dos sentidos del nombre —*anónimo* + *animal*— y dice exactamente lo que
hace: oculta la identidad (redacción de PII). Trazo monolínea, geométrico, legible
en tamaños chicos.

**Uso:** mantener el área de respeto (≈ media altura del tile) alrededor. No
rotar, no deformar, no cambiar el color del isotipo (siempre acento + blanco).
Sobre fondos oscuros el tile funciona igual; si se necesita la marca suelta sin
tile, usar el fucsia `#f06595`.

---

## Handoff del ecosistema (cuando Anonimal tenga UI)

Si en algún momento Anonimal expone interfaz, hereda gratis "Enviar a Escriba"
escribiendo el contrato en `sessionStorage['escriba.handoff']`:

```js
{ from:'anonimal', version:1, title, source, mime:'text/markdown', content, alt:{csv}, ts }
```

Escriba ya lo consume con `consumeEcosystemHandoff()`. El contenido nunca sale
del navegador.
