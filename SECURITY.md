# Seguridad

Anonimal procesa datos personales, así que la seguridad es parte del producto.

## Reportar una vulnerabilidad

No abras un issue público. Escribí a **diegoparras@gmail.com** con los detalles
(pasos para reproducir, impacto). Respondemos lo antes posible y coordinamos la
divulgación responsable.

## Controles del repo (automáticos)

Cada push / PR corre en CI (ver `.github/workflows/ci.yml`) y también local
(`python -m tests.run_tests`):

- **bandit** — auditoría de seguridad estática (SAST) del código.
- **pip-audit** — vulnerabilidades conocidas en dependencias (OSV/CVE).
- **detect-secrets** — evita filtrar credenciales al repo (baseline en
  `.secrets.baseline`).
- **ruff** + **vulture** — sin código redundante ni muerto (menos superficie,
  menos sorpresas).

## Modelo de exposición

Anonimal está pensado para correr **local**. El dato nunca sale de la máquina.
Si se expone a una red:

- Definí `ANONIMAL_TOKEN` (se exige en cada request).
- Poné un reverse proxy con TLS adelante.
- Mantené los topes de tamaño (`ANONIMAL_MAX_CHARS`).
- La imagen corre como usuario no-root.
