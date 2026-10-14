# Learning Log

Registro append-only de errores de Claude y del criterio que salió de cada uno. Gemelo de `AUDIT-LOG.md`: aquel audita el repo, este audita a Claude.

Regla que lo gobierna: `.claude/rules/learning-from-errors.md`. Verificación de reincidencia: paso 6 de `/alignment-check`.

**Las entradas no se editan ni se borran.** Si algo cambia, se agrega una entrada de seguimiento que cite la vieja.

Formato por entrada (copiar el bloque, numerar en orden: ERR-NNN):

```
## ERR-NNN — AAAA-MM-DD — Título corto del error

| Campo | Detalle |
|---|---|
| **Qué pasó** | Los hechos, sin adjetivos |
| **Causa** | Por qué pasó. Si no se sabe: not_available, con lo que sí se sabe |
| **Criterio** | La regla que lo hubiera evitado, escrita para aplicarse a otro caso distinto |
| **Dónde vive** | Memoria feedback_*.md, regla de .claude/rules/ o fila de CLAUDE.md |
| **Reincidencias** | Ninguna registrada, o los ERR de seguimiento |
```

---
