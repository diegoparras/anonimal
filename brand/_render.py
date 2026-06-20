# -*- coding: utf-8 -*-
"""Render del lockup SVG a PNG transparente 2x, con Inter cargada (Chromium)."""
import pathlib
from playwright.sync_api import sync_playwright

HERE = pathlib.Path(__file__).parent
SVG = (HERE / "anonimal-lockup.svg").read_text(encoding="utf-8")

# El SVG inline en una pagina; cargamos Inter Variable de fontsource y esperamos
# a que la fuente este lista antes de capturar, para que el texto no caiga al fallback.
HTML = f"""<!doctype html><html><head><meta charset=utf-8>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@fontsource-variable/inter/index.css">
<style>html,body{{margin:0;background:transparent}} svg{{display:block}}</style>
</head><body>{SVG}</body></html>"""

W, H, SCALE = 720, 240, 2

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": W, "height": H}, device_scale_factor=SCALE)
    pg.goto("about:blank")
    pg.set_content(HTML, wait_until="networkidle")
    pg.evaluate("document.fonts.ready")
    pg.wait_for_timeout(400)
    el = pg.query_selector("svg")
    el.screenshot(path=str(HERE / "anonimal-lockup.png"), omit_background=True)
    b.close()
print("OK -> anonimal-lockup.png")
