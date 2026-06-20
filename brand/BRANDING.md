# Anonimal — Identidad de marca

Anonimal es el guardián de privacidad del ecosistema **Escriba** (junto a
**Extracta** y **Fisherboy**). Detecta y enmascara datos personales (PII)
localmente, sobre CPU: *detecta, no decide*. La marca tiene que sentirse parte
de la misma suite —el "violín afinado"— pero con voz propia.

> Fuente de verdad del sistema: el **brand board** del ecosistema en
> `E:\Claude\ecosistema-brand` (logos + paleta canónica). Este archivo es la
> bajada de ese sistema a Anonimal.

Reglas heredadas del ecosistema (no negociables):

- Tipografía **Inter Variable** (con fallback al stack del sistema).
- Modo **claro por defecto** + oscuro vía `[data-theme="dark"]`, persistencia y
  script anti-FOUC en `<head>`.
- **Sin emojis** en la UI: íconos de línea SVG.
- **Español neutro** (sin voseo).
- Tile compartido: cuadrado redondeado (`viewBox 0 0 64 64`, `rx=15`), un color
  plano de marca y un símbolo **blanco** centrado. Sin gradientes ni sombras.
- Cada app con **su acento propio**. El de Anonimal es el **índigo antifaz**.

---

## Acento de marca — Índigo antifaz

Color plano **`#4a4e7c`**: un índigo apagado, tono "noche / máscara". Convive con
el resto del ecosistema (coral Escriba `#e06a3a`, teal Fisherboy `#0f8f6a`,
violeta Extracta `#6c5cf0`) como la nota más sobria y reservada — coherente con
"esconder, proteger".

| Rol | Claro | Oscuro |
|---|---|---|
| Acento | `#4a4e7c` | `#9aa0db` |
| Acento (press / hover) | `#3c3f66` | `#7e84c4` |
| Texto sobre acento | `#ffffff` | `#13141f` |

---

## Tokens (listos para pegar)

Mismo esquema que Escriba/Fisherboy: `:root` = oscuro, `[data-theme="light"]`
sobreescribe a claro.

```css
:root {
  --bg: #0c0d14; --bg-2: #11131c; --panel: #161824;
  --card: rgba(255,255,255,0.04); --card-2: rgba(255,255,255,0.022);
  --border: rgba(255,255,255,0.10); --hairline: rgba(255,255,255,0.16);
  --text: #edeef4; --muted: #8b8fa3; --muted-2: #c2c5d6;
  --accent: #9aa0db; --accent-2: #7e84c4;
  --on-accent: #13141f;
  --ok: #3fb950; --warn: #d6a01a; --err: #f85149;
  --radius: 12px; --radius-lg: 16px;
  --ring: 0 0 0 3px rgba(154,160,219,.26);
  --shadow: 0 1px 2px rgba(0,0,0,.4), 0 8px 24px -12px rgba(0,0,0,.6);
  color-scheme: dark;
}
[data-theme="light"] {
  --bg: #f7f7fb; --bg-2: #ffffff; --panel: #ffffff;
  --card: rgba(18,20,40,0.028); --card-2: rgba(18,20,40,0.016);
  --border: rgba(18,20,40,0.10); --hairline: rgba(18,20,40,0.17);
  --text: #15161f; --muted: #6c6f80; --muted-2: #3a3c49;
  --accent: #4a4e7c; --accent-2: #3c3f66;
  --on-accent: #ffffff;
  --ok: #1a7f37; --warn: #9a6700; --err: #cf222e;
  --ring: 0 0 0 3px rgba(74,78,124,.20);
  --shadow: 0 1px 2px rgba(18,20,40,.04), 0 12px 32px -16px rgba(18,20,40,.16);
  color-scheme: light;
}
```

`theme-color` recomendado: `#f7f7fb` (claro) / `#0c0d14` (oscuro).

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
  con el acento de fondo y el antifaz en blanco. Idéntico al canónico del brand
  board del ecosistema.
- **`logo-wordmark.svg`** — lockup horizontal (isotipo + "Anonimal"). El texto
  usa `currentColor`, así adopta `--text` del tema donde se inserte.
- **`anonimal-lockup.svg`** / **`anonimal-lockup.png`** — lockup de presentación
  (texto negro, fondo transparente), mismo encuadre que el de Escriba. El PNG es
  720×240 @2x (1440×480) listo para componer.

**Concepto:** un **antifaz** (máscara con dos huecos para los ojos). Dice
exactamente lo que hace la herramienta: *anonimiza antes de enviar* — el antifaz
de tus datos hacia el LLM. Símbolo blanco, sólido, centrado y con aire.

**Uso:** mantener el área de respeto (≈ media altura del tile) alrededor. No
rotar, no deformar, no cambiar el color del isotipo (siempre acento + blanco).
Si se necesita la marca suelta sin tile, usar el índigo `#9aa0db` (versión clara
para fondos oscuros).

---

## Handoff del ecosistema (cuando Anonimal tenga UI)

Si en algún momento Anonimal expone interfaz, hereda gratis "Enviar a Escriba"
escribiendo el contrato en `sessionStorage['escriba.handoff']`:

```js
{ from:'anonimal', version:1, title, source, mime:'text/markdown', content, alt:{csv}, ts }
```

Escriba ya lo consume con `consumeEcosystemHandoff()`. El contenido nunca sale
del navegador.
