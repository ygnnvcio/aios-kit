# Aprendizaje de errores

Aplicación de "todo sistema se evalúa y mejora" sobre Claude mismo, no solo sobre el AIOS.

Una skill no sirve para esto: las skills solo se cargan cuando se invocan. Esta regla y la memoria persistente de Claude Code se cargan solas en cada sesión; ahí tiene que vivir el aprendizaje.

## Cuándo se dispara

Se captura **en el momento**, antes de seguir con la tarea. No al final de la sesión, no cuando haya tiempo.

| Señal | Ejemplo |
|---|---|
| El usuario corrige una acción ya ejecutada | "no era eso", "eso no te lo pedí", "por qué hiciste X" |
| El usuario corrige un criterio, no un hecho puntual | "siempre pregúntame antes de X" |
| Claude descubre solo que hizo algo mal antes de que el usuario lo note | rodear un bloqueo, asumir un dato sin verificarlo |
| Una acción produjo un efecto hacia afuera que el usuario no autorizó | mensaje a un tercero, merge, gasto de créditos |

**No se dispara** por: preferencias de formato puntuales, correcciones de datos que ya viven en un archivo del repo (eso se arregla en el archivo), ni errores de una sola vez sin criterio generalizable detrás.

## Qué hacer cuando se dispara

| # | Paso | Verificación |
|---|---|---|
| 1 | Separar el error puntual del **criterio** que lo hubiera evitado. El criterio es lo que se guarda | Si no puedes escribir el criterio como regla aplicable a otro caso distinto, no hay aprendizaje: hay solo un arreglo |
| 2 | Escribir o actualizar una memoria `feedback_*.md` en la carpeta de memoria del proyecto (`~/.claude/projects/<ruta-del-proyecto-con-guiones>/memory/`) con **Por qué** y **Cómo aplicarlo** | Antes de crear una nueva, revisar si ya hay una que cubre el caso: se actualiza, no se duplica |
| 3 | Agregar la línea en `MEMORY.md` de esa carpeta | Es el índice que se carga solo; sin la línea la memoria no se lee |
| 4 | Agregar la entrada al final de `LEARNING-LOG.md` (raíz del repo) | Es el rastro auditable. La memoria dice qué se aprendió; el log dice cuándo, por qué y si se repitió |
| 5 | Si el criterio es duradero y aplica siempre, además: fila en `CLAUDE.md` o en el archivo de reglas que corresponda | Solo si aplica siempre y no solo a un proyecto |

## Reglas duras

| Regla | Por qué |
|---|---|
| **Se escribe el error aunque incomode y aunque nadie lo haya notado** | Un problema documentado ya está medio resuelto para quien viene después (`evidence-based-operating.md`). Un error oculto se repite |
| **Se registra el error, no la disculpa** | El log es para decisiones futuras. Sin párrafos de autocrítica |
| **Nunca inventar la causa** | Si no se sabe por qué pasó, se escribe `causa: not_available` con lo que sí se sabe |
| **Reincidencia > error nuevo** | Un error que ya estaba en el log y volvió a pasar significa que la memoria está mal escrita o mal ubicada. Se arregla la memoria, no solo el error |
| **El log es append-only** | Las entradas viejas no se editan ni se borran. Se agregan entradas de seguimiento |

## Escalamiento: cuando la memoria deja de alcanzar

Los pasos de arriba responden a **un** error. No responden a tres errores de la misma causa. Un error suelto se arregla con una memoria; una causa que reaparece no, y seguir escribiendo memorias sobre ella disfraza el problema.

El caso típico: tres errores de "afirmar sin verificar" se responden ampliando la misma memoria, que pasa de una línea a una página. La memoria crece; el sistema no cambia.

| Ocurrencias de la misma causa | Qué corresponde |
|---|---|
| 1 | Los pasos 1 a 5 de arriba. Nada más |
| 2 | Se abre la familia en `PATTERN-LOG.md`. Se revisa si la memoria está mal escrita o mal ubicada, y se dice cuál de las dos |
| **3 o más** | **La memoria queda declarada insuficiente. Prohibido escribir otra.** Se exige cambio estructural: hook en `.claude/settings.json`, gate en una skill, o quitar el permiso que lo habilita. Si no existe ninguno posible, se escribe en `PATTERN-LOG.md` por qué no lo hay |

El umbral es un piso, no un techo: una familia de 2 con consecuencia irreversible (algo que llega a un tercero, un merge, un gasto) puede recibir su arreglo antes de llegar a 3. Lo que prohíbe es lo contrario: llegar a 3 y responder con más prosa.

Los hooks de este kit (`guard-outward`, `guard-commit-ajeno`, `token-stop`) son ejemplos de ese cambio estructural: cada uno nació de una causa que se repitió.

## Verificación

`/alignment-check` revisa en su paso 6 si algún error del `LEARNING-LOG.md` se repitió y si cada criterio sigue viviendo donde dice. Sin ese paso, escribir el log no prueba que el aprendizaje se aplique.
