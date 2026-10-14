# aios-kit

Kit complementario para [AIS-OS](https://github.com/nateherkai/AIS-OS) de Nate Herk. AIS-OS te da la estructura del sistema (contexto, decisiones, `/onboard`, `/audit`, `/grill-me`, `/link`, `/level-up`, `/3d-brain`). Este kit agrega lo que AIS-OS no trae: que Claude aprenda de sus errores, frenos automáticos para lo que no se deshace, una wiki con fuentes, un auditor de mantenimiento y un analizador de videos.

Todo está escrito en español, es genérico (no trae datos de nadie) y está probado en macOS con el `python3` y el `bash` que trae el sistema.

## Requisitos (macOS)

| Qué | Para qué | Cómo |
|---|---|---|
| Claude Code | Todo | https://claude.com/claude-code (app de escritorio o terminal) |
| AIS-OS instalado y `/onboard` corrido | El kit se monta encima | Instrucciones en su repo |
| `git` y `python3` (3.9 o más) | Hooks, scripts y wiki | Vienen con las Command Line Tools: `xcode-select --install` |
| Homebrew | Solo para instalar lo de abajo | https://brew.sh |
| `gh` (GitHub CLI) | Abrir PRs, wiki compartida | `brew install gh` y después `gh auth login` |
| `yt-dlp` y `ffmpeg` | Solo para `/video-scout` (bajar subtítulos, video y fotogramas) | `brew install yt-dlp ffmpeg` |

Nada más: los scripts no usan librerías de Python externas ni opciones de GNU (`sed`, `stat`), y los `.sh` corren en el bash 3.2 de macOS.

## Qué trae

| Pieza | Archivos | Qué hace | Por qué sirve |
|---|---|---|---|
| Aprendizaje de errores | `.claude/rules/learning-from-errors.md`, `LEARNING-LOG.md`, `PATTERN-LOG.md` | Cuando corriges a Claude, guarda el criterio (no el error puntual) en su memoria y en un log. Si la misma causa se repite 3 veces, deja de escribir memorias y exige un cambio estructural (un hook, un permiso) | Sin esto Claude repite el mismo error en cada sesión nueva |
| Reglas de operación | `.claude/rules/communication-style.md`, `evidence-based-operating.md`, `operating-modes.md` | Cómo te habla (tablas, empieza por la respuesta, cada número con fuente), qué cuenta como dato, cuándo usa Plan Mode y subagentes, qué commitea solo y qué te pregunta, y 4 tests antes de agregar cualquier regla o automatización | Respuestas verificables y un sistema que no se llena de reglas inútiles |
| `guard-outward` | `.claude/hooks/guard-outward.sh` + `guards.py` | Te pregunta antes de mergear un PR, comentar, abrir un PR o issue o publicar un release, también si lo intenta por la API | Lo que sale de tu cuenta habla por ti; el permiso técnico no es tu visto bueno |
| `guard-commit-ajeno` | `.claude/hooks/guard-commit-ajeno.sh` + `guards.py` | Si tienes varias sesiones de Claude abiertas sobre la misma carpeta, frena el commit que se llevaría líneas que escribió otra sesión, y frena `git stash` en esa carpeta | Evita commits mezclados y cambios de otra sesión que desaparecen |
| `guard-plan-decide` (opcional, no viene activado) | `.claude/hooks/guard-plan-decide.sh` | Rechaza un plan que cierra una decisión sin declarar opciones, variable que decide y restricciones | Actívalo solo si te pasa que los planes deciden sin mostrar alternativas |
| `token-stop` | `.claude/hooks/token-stop.py` | Mide el tamaño de la sesión en cada mensaje: primero avisa, después ordena cerrar con resumen y dejar la continuación lista | Las sesiones largas cuestan mucho más por mensaje y razonan peor |
| Wiki con fuentes | `wiki/` (`SCHEMA.md`, `tools/wiki.py`, estructura vacía) | Captura cada fuente con su hash, registra qué páginas salieron de cada una y revisa enlaces, índice y si un original cambió | Conocimiento que se acumula y se puede auditar, no notas sueltas |
| `/alignment-check` | `.claude/skills/alignment-check/`, `scripts/frescura.py`, `revisar.py`, `estado_git.py`, `AUDIT-LOG.md` | Auditoría de mantenimiento: archivos de contexto desactualizados, contradicciones, rutas rotas en `CLAUDE.md`, skills sin uso, archivos sueltos, errores que reincidieron y estado git. Arregla solo lo que no requiere tu criterio | El sistema se ordena solo y te deja únicamente las decisiones |
| `/video-scout` | `.claude/skills/video-scout/` | Analiza un video con transcripción y pantalla completas, lo guarda en la wiki y busca para qué te sirve en tus proyectos | "No aplica hoy" no se pierde: queda en la wiki para cruzarlo después |
| Wiki compartida | `scripts/nueva_wiki_compartida.sh` | Arma el esqueleto de una wiki que varias personas escriben por PR | Conocimiento común sin mezclar lo personal |
| Pruebas | `scripts/test_guards.py` | 47 pruebas de los guards, token-stop, la wiki y la portabilidad | Un guard sin pruebas termina bloqueando de más (y lo apagas) o de menos |

Extra recomendado, del mismo autor que AIS-OS: [roast-room](https://github.com/nateherkai/roast-room), un consejo de siete asesores que debate una decisión difícil. Se instala desde su repo; este kit no lo copia.

## Cuándo usar cada auditor

| Herramienta | Viene de | Úsala cuando | Qué te da |
|---|---|---|---|
| `/audit` | AIS-OS | Quieres saber qué tan maduro está tu AIOS o vas a migrar o comparar Claude con Codex | Puntaje de las Cuatro C, compatibilidad Claude/Codex, informe fechado en `audits/` |
| `/link` | AIS-OS | Agregaste un proyecto, carpeta o fuente nueva y quieres que Claude la encuentre | La ruta nueva conectada en `CLAUDE.md` o en el índice que corresponda |
| `/alignment-check` | Este kit | Mantenimiento de rutina (semanal, o diario si lo usas mucho), o cuando sientes el sistema desordenado | Lo desactualizado, roto, contradictorio o sin subir; arregla lo mecánico y te deja solo las decisiones en `AUDIT-LOG.md` |

Regla simple: `/link` al agregar, `/alignment-check` para mantener, `/audit` para medir.

## Instalación

| # | Paso | Para qué |
|---|---|---|
| 1 | Instalar AIS-OS y correr `/onboard` | El kit se monta sobre su estructura |
| 2 | `git clone` de este repo en cualquier carpeta (no dentro de tu AIOS) | Tener el kit a mano |
| 3 | `bash instalar.sh ~/ruta/a/tu-aios` | Copia todo sin pisar nada, crea `.claude/settings.json` si no tienes uno y corre las pruebas |
| 4 | Abrir Claude Code en tu AIOS y pegar el prompt de abajo | Fusiona los hooks si ya tenías settings, conecta las reglas en `CLAUDE.md` y `AGENTS.md`, y calibra token-stop |
| 5 | Reiniciar la sesión de Claude Code | Los hooks y las reglas se cargan al empezar una sesión |

### Prompt 1: terminar la instalación

```
Acabo de instalar aios-kit en este AIOS (instalar.sh ya copió los archivos). Termina la instalación:
1. Lee references/aios-kit.md, references/aios-kit-snippet.md y .claude/settings.example.json.
2. Si .claude/settings.json ya existía con otro contenido, fusiona el bloque "hooks" del ejemplo sin borrar lo que ya tengo. Muéstrame el diff antes de guardar.
3. Pega el bloque de references/aios-kit-snippet.md en CLAUDE.md y en AGENTS.md, después de "How you work with me", adaptado a mis carpetas reales.
4. Corre python3 .claude/hooks/token-stop.py --medir. Si hay 10 o más sesiones, ajusta los umbrales de token-stop en settings.json con los flags que sugiere; si no, deja los valores por defecto y dime cuándo volver a medir.
5. Corre python3 scripts/test_guards.py y python3 wiki/tools/wiki.py check, y dime el resultado.
6. Registra la instalación en decisions/log.md con fecha y qué se agregó.
No commitees ni subas nada sin mostrármelo antes.
```

### Prompt 2: primer uso

```
Corre /alignment-check por primera vez sobre este AIOS y explícame cada hallazgo en una línea: qué es, por qué importa y si lo arreglas tú o lo decido yo.
```

## Wiki compartida (varias personas, un repo)

Sirve cuando dos o más personas trabajan un mismo proyecto y quieren que su conocimiento se junte, cada una con su propio Claude.

| Wiki | Dónde vive | Qué va | Quién escribe |
|---|---|---|---|
| Privada | `wiki/` dentro de tu AIOS | Todo lo tuyo, incluido lo personal | Tú, directo |
| Compartida | Un repo privado aparte en GitHub, clonado en `~/wikis/<nombre>` | Solo conocimiento del proyecto común: proveedores, procesos, pruebas, aprendizajes, herramientas | Todos, por rama y PR |

Cómo funciona:

| Pieza | Detalle |
|---|---|
| Estructura | La misma que la wiki privada (`wiki/SCHEMA.md`, `wiki/tools/wiki.py`) más un archivo `.wiki-compartida` en la raíz |
| Privacidad | Con `.wiki-compartida`, `wiki.py capture` registra un original de fuera del repo solo por su nombre (`externo:archivo.md`): ninguna ruta de tu computador entra al repo. Antes de capturar, Claude revisa que el contenido no traiga datos personales |
| Escritura | Siempre `git switch -c wiki/<tema>`, commit, `git push -u origin HEAD` y `gh pr create`. Nunca directo a la rama principal. `guard-outward` te pregunta antes de abrir el PR |
| Lectura | `git pull` en `~/wikis/<nombre>` antes de consultarla |
| Revisión | Cada PR con `python3 wiki/tools/wiki.py check` en verde |

Quien la crea (el dueño, una sola vez):

```bash
bash scripts/nueva_wiki_compartida.sh ~/wikis/mi-proyecto "Wiki de mi proyecto"
```

El script imprime los tres comandos siguientes (crear el repo privado con `gh repo create`, subirlo e invitar a cada persona con permiso de escritura). Crear e invitar los hace el dueño a mano: invitar a alguien es un paso hacia un tercero.

### Prompt 3: conectarse a una wiki compartida

Para quien ya aceptó la invitación al repo de la wiki compartida. Reemplaza `<cuenta>/<repo>` por el repo que te pasaron.

```
Me invitaron a una wiki compartida en GitHub: <cuenta>/<repo>. Conéctala a mi AIOS:
1. Verifica que gh esté autenticado (gh auth status) y que tengo acceso al repo (gh repo view <cuenta>/<repo>).
2. Clónala en ~/wikis/<repo> (no dentro de mi AIOS).
3. Lee su README.md y wiki/SCHEMA.md, y confirma que tiene el archivo .wiki-compartida en la raíz.
4. Agrega a mi CLAUDE.md y AGENTS.md la tabla "Wiki compartida" de references/aios-kit-snippet.md con la ruta real, y esta regla: lo personal va solo a mi wiki privada (wiki/); a la compartida va solo conocimiento del proyecto común, siempre por rama y PR, nunca directo a la rama principal, y antes de capturar algo revisa que no traiga datos personales míos ni de nadie.
5. Corre python3 wiki/tools/wiki.py check dentro de la wiki compartida y dime qué hay en su index.md.
6. Registra la conexión en mi decisions/log.md.
No abras PRs ni subas nada sin mostrármelo antes.
```

## Calibrar token-stop

Los umbrales vienen como parámetros en `.claude/settings.json`:

```
python3 "$CLAUDE_PROJECT_DIR/.claude/hooks/token-stop.py" --aviso-m 30 --stop-m 60 --aviso-ctx 120000 --stop-ctx 160000
```

| Parámetro | Qué mide | Por defecto |
|---|---|---|
| `--aviso-m` / `--stop-m` | Millones de tokens acumulados en la sesión | 30 / 60 |
| `--aviso-ctx` / `--stop-ctx` | Tokens de contexto del último turno (lo que cuesta cada mensaje nuevo) | 120000 / 160000, pensado para una ventana de 200k |
| `--repetir-m` | No repetir el mismo aviso antes de N millones más | 15 |

`python3 .claude/hooks/token-stop.py --medir` lee tus sesiones de este proyecto y sugiere los flags: aviso en tu percentil 75, stop entre el 75 y el 90. Si tu plan tiene ventana de contexto de 1M, sube `--aviso-ctx` y `--stop-ctx`.

Cuando llega el STOP, Claude cierra con un resumen y deja la continuación lista: con la herramienta de tarea nueva de la app de escritorio si existe, o en `.claude/tmp/traspaso.md` si no.

## Activar guard-plan-decide (opcional)

Agregar dentro de `"PreToolUse"` en `.claude/settings.json`:

```json
{
  "matcher": "ExitPlanMode",
  "hooks": [
    {
      "type": "command",
      "command": "\"$CLAUDE_PROJECT_DIR/.claude/hooks/guard-plan-decide.sh\"",
      "timeout": 10
    }
  ]
}
```

## Pruebas

```bash
python3 scripts/test_guards.py
```

Corre todo en carpetas temporales, sin tocar tu repo. Si cambias un guard, agrega su prueba en las dos direcciones: lo que tiene que frenar y lo que tiene que dejar pasar.

## Créditos

[AIS-OS](https://github.com/nateherkai/AIS-OS) y [roast-room](https://github.com/nateherkai/roast-room) son de Nate Herk (AI Automation Society). Este kit no copia su código: se instala encima.
