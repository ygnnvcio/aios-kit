# Pattern Log

Registro append-only de **familias** de error: grupos de fallas que comparten causa raíz. Hermano de `LEARNING-LOG.md` (un error por entrada) y de `AUDIT-LOG.md` (audita el repo).

Por qué existe: un error suelto se arregla con una memoria. Tres errores de la misma causa no se arreglan con una cuarta línea de prosa: se arreglan cambiando el sistema. Aquí se cuenta cuántos van.

Regla que lo gobierna: `.claude/rules/learning-from-errors.md` § Escalamiento.

## Regla de escalamiento

| Miembros de la familia | Qué corresponde |
|---|---|
| 1 | Entrada en `LEARNING-LOG.md` + memoria `feedback_*`. Nada más |
| 2 | Se abre la familia aquí. Se revisa si la memoria está mal escrita o mal ubicada |
| **3 o más** | **La memoria queda declarada insuficiente. Prohibido escribir otra.** Cambio estructural: hook, gate en una skill, o quitar el permiso que lo habilita. Si no hay ninguno posible, se escribe por qué |

## Estados

| Estado | Significa |
|---|---|
| `abierta` | Detectada, sin arreglo estructural |
| `fix pendiente` | Llegó a 3, el arreglo está propuesto y espera aprobación del usuario |
| `cerrada` | Arreglo estructural aplicado y verificado. Se anota cuál y dónde |
| `descartada` | Revisada y rechazada como familia. No se vuelve a proponer |

Formato por familia (numerar en orden: FAM-NN):

```
### FAM-NN — Causa en una línea

| Campo | Detalle |
|---|---|
| **Causa raíz** | Qué tienen en común los errores |
| **Miembros** | ERR-NNN, ERR-NNN |
| **Estado** | abierta / fix pendiente / cerrada / descartada |
| **Arreglo estructural** | Hook, gate o permiso, con su ruta. Vacío mientras esté abierta |
```

---
