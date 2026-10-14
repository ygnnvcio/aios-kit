# Bloque para pegar en CLAUDE.md (y en AGENTS.md, que AIS-OS mantiene igual)

Pegarlo después de "## How you work with me". Ajustar la última tabla con tu propia wiki compartida si tienes una.

---

## Reglas de operación

| Regla | Dónde vive |
|---|---|
| Cómo hablarme: tablas, empezar por la respuesta, cada número que decide con su fuente, cada acción mía con su "para qué" | `.claude/rules/communication-style.md` |
| Evidencia: un dato que falta es `not_available`, nunca se inventa; 4 tests antes de agregar un mecanismo | `.claude/rules/evidence-based-operating.md` |
| Plan Mode, subagentes, contexto, qué se commitea solo y qué espera mi permiso, trámites hasta mi paso | `.claude/rules/operating-modes.md` |
| Cuando te corrijo: memoria `feedback_*`, línea en `MEMORY.md` y entrada en `LEARNING-LOG.md` en el momento; 3 errores de la misma causa = cambio estructural | `.claude/rules/learning-from-errors.md` |
| Hooks activos: preguntan antes de mergear o escribirle a un tercero, frenan commits con líneas de otra sesión, avisan y frenan por tokens | `.claude/settings.json`, pruebas en `scripts/test_guards.py` |

## Routing del kit

| Pregunta | Dónde ir |
|---|---|
| ¿Qué errores cometió Claude y qué criterio salió de cada uno? | `LEARNING-LOG.md` |
| ¿Qué causa se está repitiendo y qué hay que cambiar del sistema? | `PATTERN-LOG.md` |
| ¿Qué encontró la última auditoría de mantenimiento? | `AUDIT-LOG.md` (lo escribe `/alignment-check`) |
| ¿Dónde está el conocimiento guardado, con sus fuentes? | `wiki/index.md`; reglas en `wiki/SCHEMA.md`; herramienta `python3 wiki/tools/wiki.py` |
| Me pasaron un video: ¿qué dice y para qué me sirve? | `/video-scout <link>` (lo explica, lo guarda en la wiki y busca usos) |
| ¿Qué quedó sin commitear, sin subir o solo en este equipo? | `python3 scripts/estado_git.py` |

## Wiki compartida (si la tienes)

| Wiki | Ruta local | Qué va | Cómo se escribe |
|---|---|---|---|
| Privada (esta) | `wiki/` | Todo lo mío, incluido lo personal | Directo, con `wiki.py` |
| Compartida | `~/wikis/<nombre>` (clon del repo compartido) | Solo conocimiento del proyecto común, nada personal | Rama + PR, nunca directo a la rama principal. `git pull` antes de leerla |
