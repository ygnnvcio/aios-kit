# Modos de operación

Cómo opera Claude en este AIOS. Pensado para un repo operativo (contexto, decisiones, proyectos), no solo para un proyecto de código.

## Antes de ejecutar

| Regla | Cuándo aplica |
|---|---|
| Plan Mode por defecto | Cualquier tarea no trivial. Trivial = 1 o 2 ediciones aisladas con contexto claro. Si hay ambigüedad o varios archivos en juego, Plan Mode primero |
| Preguntar hasta tener claridad | Si no se entiende bien qué quiere el usuario, preguntar (AskUserQuestion) antes de proponer. Es más barato preguntar que iterar tres veces. Toda pregunta con opciones deja una salida libre |
| Buscar reuso antes de crear | Antes de proponer un archivo, script o skill nuevo, verificar si ya existe algo que sirva. `CLAUDE.md`, las skills y `references/` son la primera parada |

## Durante la ejecución

| Regla | Detalle |
|---|---|
| Cada tarea con su verificación | Cada paso incluye cómo se comprueba. "Crear archivo X" va seguido de "leer X y confirmar que tiene Y". No avanzar al siguiente sin haber comprobado el actual |
| Subagentes para trabajo paralelo | Investigación, búsqueda en muchos archivos o exploración amplia: subagente, para proteger el contexto principal. Solo si la tarea es grande y paralelizable de verdad |
| Modelo barato para subagentes de volumen | Si un subagente va a procesar mucho texto (artículos, logs, transcripciones), usar el modelo más barato (Haiku) |
| Escape temprano | Si Claude va por mal camino, no esperar a que termine: Esc, reorientar, volver a pedir. Cada token en la dirección incorrecta es contexto perdido |
| Desafiar respuestas flojas | Si el resultado es "ok pero no excelente", pedir otra versión o otro enfoque. Después actualizar la skill o `CLAUDE.md` para que el aprendizaje quede |

## Gestión de contexto

| Regla | Detalle |
|---|---|
| `/context` cuando se sienta lento | Diagnosticar qué está comiendo tokens |
| `/compact` cerca del 60% | Comprimir el historial conservando las decisiones clave. Decir qué conservar |
| `/clear` o chat nuevo al cambiar de tarea | Tarea nueva no relacionada = contexto limpio. `CLAUDE.md`, reglas y skills se mantienen |
| Archivos grandes por tramos | Los logs append-only (`decisions/log.md`, `LEARNING-LOG.md`, `AUDIT-LOG.md`) se consultan con `grep -n` y se lee solo el tramo, nunca enteros |
| Hook `token-stop` | Avisa y frena cuando la sesión pasa un umbral de tamaño. Cuando llega la orden, se obedece |

## Mejora continua

| Regla | Cuándo aplica |
|---|---|
| Actualizar la skill al aprender algo | Si una skill funcionó mejor con un cambio, dejarlo escrito. Si falló, anotar el arreglo |
| Decisiones duraderas a `decisions/log.md` | Una decisión irreversible o una convención que dura se registra con fecha y razón |
| Memoria persistente para lo personal y de proyecto | Perfil del usuario, correcciones, contexto de proyectos: en la memoria de Claude Code, con su línea en `MEMORY.md` |
| Proponer herramientas sin esperar que las pidan | Cuando se ve una oportunidad de mejora (skill existente, automatización), proponerla. **Antes, los 4 tests de `evidence-based-operating.md` § Antes de agregar un mecanismo**: lo que no los pasa se descarta antes de proponerlo, y el descarte se dice |

## Commits: qué sale solo y qué espera permiso

Aplica al repo del AIOS, que es del usuario. En un repo compartido con otras personas manda la regla de ese repo.

Si en este equipo corren varias sesiones de Claude sobre la misma copia, un commit puede subir en cualquier momento junto con el de otra sesión. Por eso lo automático se commitea **y se sube** en el mismo paso: dejarlo commiteado sin subir es un estado que nadie puede describir con certeza.

| Sale solo, sin preguntar | Por qué |
|---|---|
| `LEARNING-LOG.md`, `PATTERN-LOG.md`, `AUDIT-LOG.md` | Son rastro auditable append-only. Un registro retenido esperando permiso no es un registro |
| Corrección de un dato contra su fuente, medida en la sesión | El dato falso ya está en el repo haciendo daño |
| Alinear un archivo con una decisión ya escrita con fecha | No hay criterio nuevo que aprobar |

| Sigue pidiendo permiso | Por qué |
|---|---|
| `decisions/log.md`, metas, prioridades, cualquier archivo que fija criterio | El criterio es del usuario, no de Claude |
| Reescribir historia (`rebase` o `--amend` sobre lo ya subido, `push --force`) | Irreversible para otras sesiones y para el remoto |
| Gastar, mergear, o cualquier cosa que llegue a un tercero | Ver `guard-outward` |

**Regla de corte cuando hay duda:** si el commit **registra** algo que ya pasó, sale solo. Si **decide** algo que todavía no pasó, espera.

## Trámites: Claude lleva todo hasta el paso del usuario

| Hace Claude | Hace el usuario, y ahí Claude se detiene con la pantalla abierta |
|---|---|
| Buscar la página, navegar, elegir opciones, preparar textos, fotos y configuración, verificar el resultado | Crear cuenta o iniciar sesión; contraseñas y códigos; autorizar una app; datos de identidad, banco, tarjeta o dirección; aceptar términos; pagar; el clic final de publicar o enviar a un tercero |

Al detenerse: una línea con qué pantalla quedó abierta, qué tiene que poner y qué sigue haciendo Claude después. Cuando el usuario termina su parte, Claude retoma sin que se lo pidan.
