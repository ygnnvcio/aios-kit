---
name: video-scout
description: Analiza un video (YouTube, Reel, TikTok u otro link) en tres partes, siempre las tres. Primero lo explica con transcripción y pantalla completas. Segundo, lo guarda en la wiki como conocimiento reutilizable. Tercero, busca casos de uso en todos los proyectos vivos del usuario y los puntúa hasta dar con el de más match, con su escalera. Para cuando el usuario pegue un link de video y pregunte "esto me sirve", "analiza este video", "explícame este video", "vale la pena este video", o invoque /video-scout.
---

# Skill: Video Scout

## Cuándo se usa

El usuario manda un video y quiere entender qué dice y qué puede hacer con eso. El resultado es: explicación, conocimiento guardado en la wiki y el caso de uso de más match. Manual o con `/video-scout`.

**"No aplica hoy" no cierra el análisis.** Un video que no sirve para el proyecto del momento igual se guarda en la wiki y pasa por la exploración de usos (pasos 5 y 6): el conocimiento se cruza después con estrategias y proyectos nuevos.

## Contra qué se compara "sirve"

Contra lo que el usuario está construyendo, leído en la fuente y no de memoria:

| Fuente | Qué da |
|---|---|
| `context/` (lo que llenó `/onboard` de AIS-OS) | Proyectos, prioridades del trimestre, a quién sirve |
| `decisions/log.md` | Lo que ya se decidió y por qué (no se re-debate porque lo diga un video) |
| `CLAUDE.md` § Knowledge base y § Connections | Herramientas conectadas y en qué se usan |

Un video "sirve" si aporta algo accionable a alguna prioridad o proyecto vivo. Si no toca ninguno, el veredicto es DESCARTAR, sin forzar relevancia, **pero el análisis sigue con los pasos 5 y 6**.

Una capacidad que el sistema del usuario no tiene y el video muestra es un **hueco**, no un "no aplica". Que la herramienta concreta del video no encaje (otra plataforma, precio, volumen) no descarta el mecanismo: se evalúa construirlo con lo que ya hay.

## Proceso

### 1. Extraer el contenido

#### YouTube

Metadatos primero (barato, a veces alcanza para un DESCARTAR):

```bash
curl -s "https://www.youtube.com/oembed?url=<URL-codificada>&format=json"
```

Transcripción: **correr el script, no reescribir el parser**.

```bash
python3 .claude/skills/video-scout/scripts/transcript.py "<URL>" --out .claude/tmp/vs
```

Deja `meta.txt` (título, canal) y `t.txt` (bloques `[mm:ss]` de 15 s). Código 2 = sin subtítulos en el idioma original: declarar `not_available` y bajar el nivel de evidencia a Parcial. Código 3 = falta yt-dlp (`brew install yt-dlp`).

| Detalle | Por qué importa |
|---|---|
| `player_client=android` | La versión web de YouTube suele devolver 0 pistas de subtítulos sin un token extra; la de android sí las sirve. El script ya lo usa |
| Pista `-orig` | Es el idioma real del video (`en-orig`, `es-orig`). Las demás son traducciones automáticas y pierden matices |
| El `.json3` no es texto plano | Cada `event` tiene `tStartMs` y `segs[].utf8`; el script los agrupa en bloques citables por minuto |

Pantalla: **obligatoria, no opcional.** Un video se analiza con pantalla y transcripción completas; en tutoriales y demos lo que decide está en la pantalla. Después de la transcripción, con el mismo `--out`:

```bash
python3 .claude/skills/video-scout/scripts/pantalla.py "<URL>" --out .claude/tmp/vs
```

Baja el video a 1080p, saca un fotograma cada 10 s y escribe `tramos.txt`: qué fotogramas y qué líneas de `t.txt` le tocan a cada agente (10 minutos por tramo). Se lanza **un subagente por tramo** que abre TODOS sus fotogramas con `Read` junto a su transcripción y devuelve texto: qué se ve, cifras y ajustes visibles, qué se dice y si coincide con lo que se ve. Un dato ilegible se saca ampliando el fotograma exacto antes de declararlo `not_available`. Lo que decide (un panel, un resultado, una configuración) lo revisa el agente principal en persona.

Si los subtítulos fallan (error 429 o sin pista), alternativa: transcribir el audio con Whisper local (por ejemplo `pip3 install --user openai-whisper` o `mlx-whisper` en Mac con chip Apple). Es opcional y no viene en el kit.

#### Otras fuentes

| Fuente | Cómo extraer |
|---|---|
| Reel / TikTok / video corto | `yt-dlp` suele bajarlos (`pantalla.py` funciona igual). Si pide inicio de sesión, pedirle al usuario el texto del post, el gancho y 2 o 3 frases de qué muestra |
| Artículo, hilo, página | WebFetch directo |
| Transcripción ya pegada | Usarla tal cual |

#### Videos largos

| Duración | Estrategia |
|---|---|
| Hasta 60 min | Leer la transcripción en el agente principal |
| Más de 60 min | Subagente con el modelo más barato (Haiku) que pagina la transcripción y devuelve ~2k tokens: tema, segmentos, citas y datos clave, herramientas, tácticas |

### 2. Declarar el nivel de evidencia

Antes del veredicto, decir con qué se está juzgando. Un dato ausente se registra `not_available` con la razón; nunca se inventa.

| Nivel | Qué se tiene |
|---|---|
| Completo | Transcripción entera **y** todos los fotogramas vistos |
| Parcial | Solo transcripción, o título + descripción + capítulos. Alcanza para un DESCARTAR, **no para un SIRVE** con acción concreta; se dice qué falta |
| Insuficiente | Ni eso. Pedírselo al usuario y parar |

Un SIRVE sobre evidencia parcial es una tesis, no un veredicto.

### 3. Explicar y dar el veredicto

Primero, qué es y cómo funciona lo que muestra el video, en tablas. Los datos externos se verifican en la fuente más confiable: un nombre propio sacado de subtítulos automáticos se confirma antes de escribirlo.

Después, SIRVE o DESCARTAR contra los proyectos y prioridades vivos, con una frase de justificación. Si es SIRVE:

- Qué aporta: 3 a 5 frases, sin relleno.
- Tabla: proyecto o prioridad que toca | qué aporta ahí.
- Acción concreta: lista ordenada, verbo + objeto. Si la acción es para el usuario, lleva su "para qué".
- Si contradice algo de `decisions/log.md`, decirlo explícito. Una decisión con razón escrita no se re-debate porque un video diga otra cosa: primero se refuta la razón.

### 4. Antes de proponer un mecanismo nuevo

Si la acción implica agregar una regla, hook, skill o rutina, pasa **antes** los 4 tests de `.claude/rules/evidence-based-operating.md` § Antes de agregar un mecanismo. Un video es la tesis de un referente: el escalón más bajo de la evidencia. Define qué probar; no cierra nada.

### 5. Guardar en la wiki, siempre

| # | Paso |
|---|---|
| 1 | Escribir la fuente en `references/AAAA-MM-DD-<tema>.md`: qué es, cifras con fuente y nivel, límites, críticas y el banco de usos del paso 6. **Resumen propio, no la transcripción entera**: la transcripción queda en `.claude/tmp/` y se citan minutos `[mm:ss]` |
| 2 | Capturarla: `python3 wiki/tools/wiki.py capture references/<archivo> --title "..."` |
| 3 | Integrarla según `wiki/SCHEMA.md` § Ingestar: página propia si es una herramienta o técnica reutilizable, enlaces reales a los proyectos donde encaja, índice, log, `catalog` y `check` |

### 6. Explorar usos hasta el de más match, siempre

Antes de puntuar, sin excepción:

| Chequeo | Qué exige | Falla cuando |
|---|---|---|
| A. Funciones completas | Tabla con **todas** las funciones de la herramienta, sacadas de su fuente oficial y no solo de lo que muestra el video | El banco parte de la función que el video destaca |
| B. Proyectos desde la fuente | Leer `context/` y cruzar **cada proyecto vivo** (y la operación del propio AIOS) contra esas funciones, con una columna "Hoy lo hace" (lo que ya cubre ese hueco) | Se listan proyectos de memoria, o queda uno sin fila |
| C. Qué funciona hoy | Separar lo que la herramienta ya probó de lo que sigue en demo | Se puntúa sin saber qué funciona de verdad |
| D. Sin ancla | No partir de una recomendación ya dada en la sesión | El ganador es la recomendación anterior con otro nombre |

| # | Paso |
|---|---|
| 1 | Mapear los puntos del sistema donde la técnica o herramienta podría entrar, con su volumen medido con fuente, o `not_available` |
| 2 | Generar casos concretos desde varios ángulos: volumen y costo, tiempo, rol del usuario, capacidad nueva |
| 3 | Puntuarlos con una rúbrica explícita (volumen, valor, ajuste, ventaja sobre lo actual, factibilidad, alineación con las prioridades, riesgo). Iterar variantes sobre los mejores hasta que el puntaje deje de subir |
| 4 | Intentar refutar el top 3: ¿el volumen es real?, ¿un script simple lo hace igual?, ¿contradice una decisión escrita? |
| 5 | Entregar el de más match con su escalera (nivel actual, siguiente nivel con costo y gatillo, nivel final) y guardar el banco completo de casos en la wiki |

La honestidad está en la puntuación: un caso puede puntuar bajo y se dice, pero se exploran varios antes de concluir.

## Formato de salida

```
# [Título]
Canal o cuenta · Duración · URL

## Veredicto: SIRVE / DESCARTAR
Una frase.

## Qué es y cómo funciona
Tablas, con la fuente y su nivel en cada dato.

## Nivel de evidencia
| Ítem | Estado |     <- qué se obtuvo, qué quedó not_available y por qué

## Qué aporta y dónde pega (si SIRVE)
| Proyecto o prioridad | Qué aporta |

## Acción concreta (si SIRVE)
1. ...

## Choca con algo decidido (si aplica)
Qué decisión y qué dice su razón escrita.

## Herramientas nuevas (si hay)
| Herramienta | Para qué | Ya en el stack |

## Usos en el sistema (siempre)
Caso de más match y por qué.
| # | Caso | Proyecto | Puntaje | Qué desbloquea | Debilidad |
Escalera del ganador: nivel actual -> siguiente (costo, gatillo) -> final.

## Guardado en la wiki (siempre)
Referencia, ID de captura y páginas tocadas.
```

## Reglas

| Regla | Detalle |
|---|---|
| Veredicto primero | No arrancar por el resumen del video |
| No inflar relevancia | Si toca el tema de forma tangencial y no deja acción concreta, es DESCARTAR. La misma honestidad vale en el paso 6 |
| Nunca cerrar con "no aplica" | El DESCARTAR no termina el resultado: la wiki y la exploración de usos se hacen siempre |
| No rellenar secciones vacías | Si no hay herramientas nuevas, decir "ninguna" |
| Fuente viva | Releer `context/` y `decisions/log.md` en cada corrida |
| Evidencia antes que veredicto | Nunca un SIRVE con acción concreta sobre solo título y descripción |
| Cuentas y plataformas | Si la acción toca una cuenta publicitaria o una plataforma con reglas de uso, sus reglas escritas mandan sobre cualquier táctica del video |
