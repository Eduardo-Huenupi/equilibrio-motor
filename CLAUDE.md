# Reglas de trabajo para Claude Code en este repositorio

- Explica cada cambio en español simple: qué hiciste y por qué. El dueño del repositorio está aprendiendo.
- Antes de programar algo nuevo, muestra el plan y espera confirmación.
- Nunca escribas claves o tokens en el código ni en los commits; todo va en `.env`.
- Cada función nueva lleva su prueba en `tests/`. Corre `make test` y `make evals` antes de dar algo por terminado.
- Si un cambio baja la exactitud, la fidelidad o el rechazo correcto de los evals, detente y avisa.
- Toda búsqueda o lectura de datos filtra por `org_id`. Agrega una prueba de aislamiento cuando crees un acceso nuevo.
- Datos de salud o personales: nunca en logs sin enmascarar, nunca reales en desarrollo o pruebas.
- Cambios de base de datos: siempre como archivo nuevo en `supabase/migrations/`, mostrado antes de aplicarse.
- Antes de borrar archivos o datos, pregunta.
- Si una decisión de arquitectura tiene alternativas, anótala en `docs/decisiones.md`.
- Commits pequeños con mensajes claros en español.

## Comandos

- `make test`: pruebas automáticas
- `make evals`: evals del dataset de demostración (con umbrales mínimos)
- `make demo`: API local con datos de demostración
