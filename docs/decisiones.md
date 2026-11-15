# Decisiones de arquitectura

Cada decisión anota qué se eligió, por qué y qué se descartó.

## 1. Interfaces para almacén, embeddings y modelo
**Decisión:** el motor depende de tres interfaces (`Almacen`, `Embedder`, `LLM`), con una versión local y una de producción de cada una.
**Por qué:** las pruebas y los evals corren sin claves, sin costo y con resultados reproducibles; cambiar de proveedor no toca la lógica.
**Descartado:** llamar a Supabase y Claude directo desde el motor (más corto, pero imposible de probar en CI sin secretos).

## 2. Búsqueda híbrida con RRF
**Decisión:** combinar búsqueda vectorial y por palabras con Reciprocal Rank Fusion.
**Por qué:** la vectorial encuentra paráfrasis; la de palabras encuentra números, siglas y nombres exactos (artículos, plazos, RUT). RRF no necesita calibrar pesos.
**Descartado:** solo vectorial (falla con términos exactos); suma ponderada de puntajes (escalas distintas, pesos frágiles).

## 3. Fragmentos que no cruzan páginas
**Decisión:** cada fragmento pertenece a una sola página.
**Por qué:** la cita "documento, página" es la promesa central del producto y debe ser exacta.
**Costo:** una idea partida entre dos páginas queda en dos fragmentos.

## 4. Rechazar antes que inventar
**Decisión:** tres barreras (umbral de evidencia, NO_ENCONTRADO, cita válida obligatoria). Ante la duda, el motor dice que no encontró la información.
**Por qué:** en colegios y salud, una respuesta inventada cuesta más que una no respondida.
**Costo:** algunos falsos rechazos; se miden en los evals (`exactitud`).

## 5. Seguridad en Supabase: RLS sin políticas + service key en el backend
**Decisión:** todas las tablas con RLS activado y ninguna política; solo el backend accede, y filtra por `org_id` en cada consulta.
**Por qué:** nada es legible desde un navegador aunque se filtre la clave pública.
**Riesgo:** el aislamiento entre organizaciones depende del código del backend; por eso hay pruebas de aislamiento.
**Siguiente paso:** Supabase Auth con `org_id` en el JWT y políticas RLS por organización (defensa en dos capas).

## 6. Auditoría encadenada por hash
**Decisión:** cada entrada guarda el hash de la anterior; la tabla bloquea UPDATE, DELETE y TRUNCATE.
**Por qué:** permite demostrar que el registro no fue alterado.
**Límite:** quien administra la base puede desactivar los triggers; la cadena hace que la alteración sea detectable, no imposible.

## 7. Detección de prompt injection por patrones
**Decisión:** filtro por expresiones regulares en preguntas y documentos.
**Por qué:** barato, explicable y sin dependencias.
**Límite:** se puede evadir. Las defensas de fondo son tratar los fragmentos como datos, exigir citas y pedir aprobación humana para acciones sensibles.
