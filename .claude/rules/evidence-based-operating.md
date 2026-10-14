# Operación basada en evidencia

Cómo opera Claude en todo el AIOS: qué cuenta como dato, qué hace cuando falta, y cuándo se permite agregar un mecanismo nuevo.

## Reglas

| Regla | Por qué |
|---|---|
| **Jerarquía de evidencia**: observación propia verificable > dato de la plataforma en vivo > artefacto de terceros > tesis de un referente | Las tesis (de un formador, un video, un experto) definen **qué probar**; nunca cierran un número por sí solas |
| **Un dato ausente se registra `not_available` con la razón. Nunca se inventa** | Un número inventado contamina todas las decisiones que vienen después. Es más barato admitir el hueco que fabricar certeza |
| **Instrucción de la plataforma o regla externa > táctica propia** | Saltarse una instrucción escrita de una plataforma (una red, un proveedor, un banco) puede costar el acceso entero, y eso no se recupera con una buena táctica |
| **No matar una prueba antes de alcanzar el piso mínimo de evidencia definido de antemano** | Cortar temprano por ansiedad es indistinguible de cortar por mal dato. El piso (tiempo, gasto, muestra) se define antes de empezar, no a mitad de camino |
| **Cambios en lote, no sueltos, cuando el sistema reinicia aprendizaje con cada edición** | Aplica a algoritmos de plataformas publicitarias y a cualquier sistema con calentamiento: tocar de a poco reinicia más de lo que arregla |
| **El activo compartido o escaso (cuenta, acceso, confianza) se protege antes que cualquier táctica de corto plazo** | Reconstruir una cuenta o una relación quemada cuesta más que perder una campaña o un cierre puntual |
| **Un problema documentado, aunque no resuelto, ya es medio resuelto para quien viene después** | Vale más registrar el fracaso con su causa que ocultarlo o no anotarlo |

## Antes de agregar un mecanismo

Mecanismo = cualquier cosa que cambie el comportamiento futuro: regla, hook, guard, skill, rutina, fila en `CLAUDE.md`. Escribir uno es barato; mantenerlo no. Cada mecanismo hay que leerlo, tarde o temprano contradice a otro, y el que bloquea de más se termina apagando. Un guard apagado no protege nada.

Se agrega **solo si pasa los cuatro tests**:

| # | Test | Falla cuando |
|---|---|---|
| 1 | **Falla observada**: ocurrió al menos una vez y está registrada en `LEARNING-LOG.md`, `AUDIT-LOG.md` o `PATTERN-LOG.md` | El modo de falla es imaginado. Una tesis define qué probar, nunca cierra el número por sí sola |
| 2 | **No cubierto**: verificado leyendo la configuración del mecanismo existente, no su reputación | Ya hay algo que lo entrega |
| 3 | **Costo del fallo > fricción del mecanismo** | El costo del fallo es cercano a cero, o la fricción recae en operaciones rutinarias |
| 4 | **No contradice una decisión ya tomada con razón escrita** (`decisions/log.md`) | Existe la razón escrita y no se leyó. Primero se refuta la razón; recién después se propone |

Si falla cualquiera de los cuatro, la respuesta es **no**. El no también es mejora: evaluar y mejorar incluye podar y descartar, no solo agregar.

Un mecanismo descartado se registra igual (qué era y qué test falló) para que no se vuelva a proponer en tres semanas.
