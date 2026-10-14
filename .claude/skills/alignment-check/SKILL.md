---
name: alignment-check
description: Auditoría de mantenimiento del AIOS. Revisa frescura de los archivos de estado y contexto, coherencia entre archivos, rutas rotas en CLAUDE.md, skills sin uso, archivos sueltos, reincidencia de errores del LEARNING-LOG y estado git (sin commitear, sin subir, ramas huérfanas, worktrees). Arregla solo lo que no requiere criterio y deja el informe en AUDIT-LOG.md. Usar cuando el usuario diga "audita el sistema", "revisa si está alineado", "qué está desactualizado", "ordena el AIOS", o invoque /alignment-check. No es /audit de AIS-OS (ése puntúa las Cuatro C y la compatibilidad con Codex).
---

# Skill: alignment-check

Checklist de mantenimiento para que el AIOS siga alineado con lo que el usuario está haciendo y no acumule fricción. Corre a mano con `/alignment-check`, o como rutina programada (por ejemplo una vez al día o a la semana con `/schedule`).

Se corre cada paso una vez y se confía en el resultado: no hace falta repasar el propio informe al final.

**Regla de corte de todo el checklist:** lo que es índice roto, referencia muerta o ruido sin dueño se arregla solo (es reversible con git). Lo que fija criterio (contexto, decisiones, prioridades, qué proyecto vive o muere) se reporta y lo decide el usuario.

## 1. Frescura

```bash
python3 scripts/frescura.py
```

Mide la fecha que declara cada archivo de estado (`STATUS.md` si existe, `context/*.md` y los imports `@` de `CLAUDE.md`) contra su último commit. Cada fila `DESACTUALIZADA` es un hallazgo con sus días de deriva. `NO COMPROBABLE` y `SIN COMMITEAR` se reportan con su razón, sin tratarlas como vigentes.

**La fecha no se autoedita.** La herramienta mide; la cabecera la corrige quien verificó el contenido. Si Claude la pisa, la señal deja de servir.

## 2. Coherencia cruzada

Leer las últimas entradas de `decisions/log.md` (con `grep -n` por fecha, no entero) y confirmar que lo que dicen calza con `context/`, la sección de prioridades de `CLAUDE.md` y `STATUS.md` si existe: qué proyecto está vivo o muerto, quién hace qué, cuál es la prioridad.

Contradicción de contenido: **nunca autoeditar.** Es un hallazgo para que el usuario decida cuál versión es la correcta.

## 3. Integridad del routing

```bash
python3 scripts/revisar.py rutas
```

Lista las rutas citadas en `CLAUDE.md` y `AGENTS.md` que no existen en disco. Ruta rota = hallazgo. Si la ruta cambió de nombre y el destino nuevo es obvio (mismo archivo movido, `git log --follow` lo confirma), se corrige la referencia: es un índice roto, no una decisión.

## 4. Skills sin uso

```bash
python3 scripts/revisar.py skills --dias 30
```

Cuenta las invocaciones de cada skill de `.claude/skills/` en los transcripts de Claude Code de este proyecto. Después, para cada skill con 0 usos, leer su `SKILL.md` y ver a qué proyecto está atada:

| Caso | Qué hacer |
|---|---|
| Atada a un proyecto vivo | Se queda. Sin uso no es inútil: puede ser de temporada |
| Atada **solo** a un proyecto que `decisions/log.md` declara muerto o archivado | Autoarchivar: `git mv .claude/skills/<skill> archives/skills/<skill>` y anotarlo en el informe con la decisión que lo respalda |
| Sin proyecto claro | Hallazgo: preguntar al usuario si la archiva |
| Enlace simbólico roto | Hallazgo, no autoeditar (puede estar reinstalándose) |

## 5. Ruido

Buscar en la raíz, `references/` y `context/`: archivos sueltos sin propósito claro, carpetas vacías, duplicados de lo que ya está en `archives/`, temporales olvidados. Una referencia en `.claude/settings.json` o `CLAUDE.md` a un archivo que ya no existe se borra (reversible con git). Un archivo suelto con contenido se reporta, no se borra.

## 6. Reincidencia de errores

Leer `PATTERN-LOG.md`:

- Familia en estado `fix pendiente` hace más de 3 días: hallazgo. Una familia que llegó al umbral y sigue esperando es deuda, no registro.

Leer `LEARNING-LOG.md` (con `grep -n "^## ERR"` para el índice y el tramo de cada entrada). Para cada entrada:

- **Que el criterio siga existiendo donde dice vivir.** Si apunta a una memoria `feedback_*.md`, confirmar que el archivo existe en la carpeta de memoria del proyecto (`~/.claude/projects/<ruta-del-proyecto-con-guiones>/memory/`) y que su línea está en `MEMORY.md`: sin la línea del índice, la memoria no se carga. Si apunta a una regla o a `CLAUDE.md`, confirmar que la fila sigue.
- **Que no haya reincidido.** Si en el período pasó otra vez algo que ya estaba en el log, es hallazgo de prioridad alta: la memoria está mal escrita o mal ubicada. Se propone el arreglo y se agrega una entrada de seguimiento al `LEARNING-LOG.md` que cite la original. Con 3 ocurrencias de la misma causa aplica `.claude/rules/learning-from-errors.md` § Escalamiento.

Nunca reescribir ni borrar entradas del log: es append-only. Autofix permitido: **solo** restaurar en `MEMORY.md` una línea faltante cuyo archivo `feedback_*.md` sí existe.

## 7. Estado git

```bash
python3 scripts/estado_git.py
```

Hace `git fetch` y reporta, en el repo y en cada worktree: archivos sin commitear quietos hace más de 6 horas, commits que no están en ningún remoto, ramas que solo existen en este equipo, ramas cuyo remoto desapareció y worktrees cuya carpeta ya no existe.

| Señal | Qué significa |
|---|---|
| Sin commitear quieto | Trabajo que se puede perder u olvidar |
| Commits sin subir | Si el disco muere, se pierden |
| Rama solo local | Trabajo en el limbo: ni subido ni descartado |
| Remoto `gone` | El PR ya se mergeó o se cerró; la rama quedó de ruido |
| Worktree perdido | Registro que apunta a una carpeta borrada |

**Autofix permitido:** borrar una rama local con remoto `gone` **solo si** el script dice que su trabajo ya está en la rama principal (`git branch -d`, nunca `-D`), y `git worktree prune` para los worktrees perdidos.

**Nunca autofix:** `push`, `pull`, `merge`, `stash`, ni commitear cambios sueltos de otra sesión. Se reporta y decide el usuario.

## 8. Registro

Agregar al final de `AUDIT-LOG.md` (raíz) una entrada con este formato:

```
## AAAA-MM-DD

**Revisado:** frescura, coherencia, routing, skills, ruido, reincidencia, git
**Autoarreglado:** [qué se movió, borró o corrigió y por qué, o "nada"]
**Pendiente de tu decisión:** [contradicciones y hallazgos ambiguos, o "nada"]
**Reincidencia:** [error del LEARNING-LOG que volvió a pasar, o "nada"]
**Git:** [limpio, o el resumen de estado_git.py]
**Skills sin uso:** [lista, o "ninguna"]
```

Si "Autoarreglado" y "Pendiente de tu decisión" están vacíos, la entrada igual se escribe (deja rastro de que corrió). Según `.claude/rules/operating-modes.md` § Commits, `AUDIT-LOG.md` se commitea y se sube solo.

Al usuario se le entrega solo "Pendiente de tu decisión", cada ítem con su dato y su fuente.
