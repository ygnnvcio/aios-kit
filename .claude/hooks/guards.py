#!/usr/bin/env python3
"""Parser compartido de los guards de PreToolUse. Lo invocan los .sh de esta
carpeta (guard-outward.sh, guard-commit-ajeno.sh, guard-plan-decide.sh), que
existen para que .claude/settings.json declare una ruta por guard.

Compatible con el python3 que trae macOS (3.9). Sin dependencias.

POR QUE NO SE PARTE EL COMANDO CON sed/tr
-----------------------------------------
La forma ingenua separa el comando en segmentos cambiando `&&`, `||`, `|` y `;`
por saltos de linea. Eso ignora las comillas y produce dos fallas opuestas:

  falso positivo   echo 'primero cd /tmp && gh pr comment 5 -b x'
                   El && dentro del string genera un segmento que EMPIEZA con
                   `gh`, y una simple mencion se bloquea como si fuera una
                   invocacion. Un guard que bloquea de mas se termina
                   apagando, y un guard apagado no protege nada.

  falso negativo   cd /tmp && bash -c "gh pr merge 5"
                   El segmento empieza con `bash`, no con `gh`, y un merge real
                   pasa sin que nadie lo vea.

`shlex` con punctuation_chars respeta las comillas: lo que esta dentro de un
string queda como UN token y nunca produce una posicion de comando. Y para no
perder lo anidado, el contenido que sigue a `-c` o `eval` se vuelve a parsear.
"""
import json
import os
import re
import shlex
import subprocess
import sys

# Un string que viene despues de estos es codigo, no un dato: se vuelve a parsear.
ANIDAN = {"-c", "-lc", "-ic", "eval"}
HEREDOC = re.compile(r"<<-?[ \t]*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1[^\n]*\n")


def es_operador(t):
    """`;`, `&&`, `||`, `|`, `&`, parentesis, salto de linea, o una mezcla pegada (`;\n`)."""
    return bool(t) and set(t) <= set(";&|()\n")


def sin_heredocs(cmd):
    """Quita el cuerpo de cada heredoc: es texto que va a un archivo, no comandos.
    Sin esto, una linea del cuerpo que empieza con `gh pr merge` se leia como invocacion."""
    salida, pos = [], 0
    for m in HEREDOC.finditer(cmd):
        if m.start() < pos:
            continue
        fin = re.compile(r"^[ \t]*" + re.escape(m.group(2)) + r"[ \t]*$", re.M).search(cmd, m.end())
        salida.append(cmd[pos:m.end()])
        pos = fin.end() if fin else len(cmd)
    salida.append(cmd[pos:])
    return "".join(salida)


def invocaciones(cmd, profundidad=0):
    """Devuelve el argv de cada comando realmente invocado en `cmd`."""
    if profundidad > 3:
        return []
    cmd = sin_heredocs(cmd)
    try:
        # El salto de linea separa comandos igual que `;`: no puede contar como espacio,
        # o un merge en la segunda linea queda pegado al argv del primer comando.
        lex = shlex.shlex(cmd, posix=True, punctuation_chars="();<>|&\n")
        lex.whitespace = " \t\r"
        lex.whitespace_split = True
        tokens = list(lex)
    except ValueError:
        # Comillas sin cerrar: no se puede tokenizar. Se recurre al metodo ingenuo,
        # que ve de mas. Ver de mas es preferible a no ver nada, y es raro.
        crudo = cmd
        for op in ("&&", "||", "|", ";"):
            crudo = crudo.replace(op, "\n")
        return [t.split() for t in crudo.split("\n") if t.split()]

    salida, actual, inicio = [], [], True
    for i, t in enumerate(tokens):
        if es_operador(t):
            if actual:
                salida.append(actual)
            actual, inicio = [], True
            continue
        actual.append(t)
        if not inicio and tokens[i - 1] in ANIDAN:
            salida.extend(invocaciones(t, profundidad + 1))
        inicio = False
    if actual:
        salida.append(actual)
    return salida


def _decidir(decision, razon):
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": decision,
        "permissionDecisionReason": razon}}, ensure_ascii=False))
    sys.exit(0)


def deny(razon):
    _decidir("deny", razon)


def ask(razon):
    """Corta y pregunta, en vez de cortar y punto.

    Un deny incondicional sobre el merge lo vuelve imposible incluso cuando el
    usuario lo pide. Lo que se quiere es que se le pregunte: el dialogo de
    permiso ES esa pregunta.
    """
    _decidir("ask", razon)


def _git(repo, *args):
    r = subprocess.run(["git", "-C", repo] + list(args), capture_output=True, text=True, timeout=5)
    return r.stdout if r.returncode == 0 else ""


def _repo_de(argv, dir_actual):
    repo = dir_actual
    if "-C" in argv and argv.index("-C") + 1 < len(argv):
        repo = argv[argv.index("-C") + 1]
    return repo


def _raiz():
    """La raiz del repo del AIOS: dos carpetas arriba de este archivo, o GUARD_AJENO_RAIZ (pruebas)."""
    return os.path.realpath(os.environ.get("GUARD_AJENO_RAIZ") or
                            os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))


# ---------------------------------------------------------------------------
# guard-outward: actuar hacia afuera sin que el usuario lo confirme
# ---------------------------------------------------------------------------

RAZON_MERGE = (
    "guard-outward frena el merge para que lo confirmes. Antes de mergear: decir que PR es, que "
    "cambia y por que conviene. Si ya lo pediste, apruebalo y sigue sin mas vueltas. El permiso "
    "tecnico resuelve el 'puedo', no el 'debo'. Tampoco rodearlo por la API: una llamada a "
    "`gh api` que termine en /merge se frena igual.")
RAZON_HABLA = (
    "guard-outward frena la comunicacion hacia un tercero para que la confirmes. Lo que sale de "
    "esta cuenta habla como el usuario: para quien lo recibe, el mensaje es suyo. Redactar el "
    "texto completo, mostrarlo en el chat y publicar recien con el visto bueno. Commits y ramas "
    "propias no cuentan: eso es trabajo, no comunicacion.")

HABLA = {("pr", "comment"), ("pr", "review"), ("pr", "create"),
         ("issue", "create"), ("issue", "comment"), ("release", "create"),
         ("pr", "edit"), ("issue", "edit")}

# Sufijos de la API REST que publican algo que un tercero ve:
# `gh api repos/O/R/issues/3/comments -f body=...` comenta igual que `gh pr comment`.
API_HABLA = ("/comments", "/reviews")
ESCRIBEN = {"-f", "-F", "--field", "--raw-field", "--input", "--method"}
METODOS_ESCRITURA = {"POST", "PATCH", "PUT", "DELETE"}


def outward(cmd, _cwd):
    for argv in invocaciones(cmd):
        if argv[0] != "gh":
            continue
        par = tuple(argv[1:3])
        if par == ("pr", "merge"):
            ask(RAZON_MERGE)
        if par in HABLA:
            # ask y no deny: si el flujo exige abrir PR, un deny sobre `pr create`
            # seria un bloqueo mutuo. Se pregunta; el dialogo es el visto bueno.
            ask(RAZON_HABLA)
        # La via alternativa: `gh api .../pulls/N/merge --method PUT` mergea sin
        # pasar por `gh pr merge`. Cumplir la letra rompiendo la intencion no cuenta.
        if argv[1:2] == ["api"] and any(a.rstrip("/").endswith("/merge") for a in argv):
            ask(RAZON_MERGE)
        if argv[1:2] == ["api"]:
            toca_canal = any(a.rstrip("/").endswith(API_HABLA) for a in argv)
            escribe = bool(ESCRIBEN & set(argv)) or bool(
                METODOS_ESCRITURA & set(a.upper() for a in argv))
            # Sin flags de escritura es una lectura y pasa.
            if toca_canal and escribe:
                ask(RAZON_HABLA)


# ---------------------------------------------------------------------------
# guard-commit-ajeno: varias sesiones sobre la misma copia del repo
# ---------------------------------------------------------------------------

RAZON_STASH = (
    "guard-commit-ajeno frena `{que}` en el repo del AIOS. Si varias sesiones de Claude trabajan "
    "sobre esta misma copia, un stash (o --autostash) saca del arbol los cambios sin commitear de "
    "las OTRAS sesiones, y un rebase que queda a medias los puede dejar fuera. Para integrar el "
    "remoto: `git fetch` y `git merge origin/<rama>`, que no necesita stash si lo que llega no toca "
    "archivos sucios. Si de verdad hace falta, que el usuario lo pida explicitamente.")


def stash_raiz(cmd, cwd):
    """Guardar aparte (stash) un arbol que tambien es de otras sesiones."""
    if "stash" not in cmd:
        return
    raiz = _raiz()
    dir_actual = cwd
    for argv in invocaciones(cmd):
        if argv[0] == "cd" and len(argv) > 1:
            dir_actual = os.path.join(dir_actual, argv[1])
            continue
        if argv[0] != "git":
            continue
        top = _git(os.path.join(dir_actual, _repo_de(argv, dir_actual)), "rev-parse", "--show-toplevel").strip()
        if not top or os.path.realpath(top) != raiz:
            continue
        resto = [a for a in argv[1:] if not a.startswith("-")]
        if "--autostash" in argv:
            deny(RAZON_STASH.format(que="--autostash"))
            return
        if resto and resto[0] == "stash" and (len(resto) < 2 or resto[1] not in ("list", "show")):
            deny(RAZON_STASH.format(que="git " + " ".join(resto[:2])))
            return


RAZON_AJENO = (
    "guard-commit-ajeno frena este commit: trae lineas que esta sesion no escribio "
    "(no aparecen en ninguna llamada a herramienta de su transcript):\n{lineas}\n"
    "Cuando varias sesiones editan la misma copia, `git add/commit <ruta>` sube el archivo entero, "
    "no solo tus lineas. Si son de otra sesion: commitea solo lo tuyo (arma el archivo desde "
    "`git show HEAD:<ruta>` con tu edicion y subelo con `git update-index --cacheinfo`) o espera a "
    "que esa sesion commitee. Si salen de un script que corriste en esta sesion (un indice o un "
    "reporte generado), repite el comando con el prefijo `AJENO_OK=1` delante del git commit.")
VENTANA_AJENA, PASO_AJENO, MIN_LINEA = 30, 15, 25


def _texto_de_la_sesion(payload):
    """Todo lo que esta sesion y sus subagentes mandaron a herramientas, sin resultados."""
    from pathlib import Path
    ruta = payload.get("transcript_path") or ""
    if not ruta or not Path(ruta).exists():
        return None
    archivos = [Path(ruta)] + sorted(Path(ruta).with_suffix("").glob("subagents/*.jsonl"))
    partes = []

    def juntar(x):
        if isinstance(x, str):
            partes.append(x)
        elif isinstance(x, dict):
            for v in x.values():
                juntar(v)
        elif isinstance(x, list):
            for v in x:
                juntar(v)
    for f in archivos:
        try:
            for linea in f.open(errors="replace"):
                if '"tool_use"' not in linea:
                    continue
                try:
                    r = json.loads(linea)
                except ValueError:
                    continue
                for c in ((r.get("message") or {}).get("content") or []):
                    if isinstance(c, dict) and c.get("type") == "tool_use":
                        juntar(c.get("input"))
        except OSError:
            continue
    return " ".join(" ".join(p.split()) for p in partes)


def _es_propia(linea, texto):
    s = " ".join(linea.split())
    if len(s) < MIN_LINEA:
        return True
    if len(s) <= VENTANA_AJENA + PASO_AJENO:
        return s in texto
    return any(s[i:i + VENTANA_AJENA] in texto
               for i in range(0, len(s) - VENTANA_AJENA + 1, PASO_AJENO))


def commit_ajeno(cmd, cwd, payload):
    """Un commit en la raiz del AIOS que se lleva lineas de otra sesion."""
    if "commit" not in cmd or "AJENO_OK=1" in cmd:
        return
    raiz = _raiz()
    rutas, hay_commit, dir_actual, repo_ok = set(), False, cwd, None
    for argv in invocaciones(cmd):
        if argv[0] == "cd" and len(argv) > 1:
            dir_actual = os.path.join(dir_actual, argv[1])
            continue
        if argv[0] != "git":
            continue
        repo = os.path.join(dir_actual, _repo_de(argv, dir_actual))
        top = _git(repo, "rev-parse", "--show-toplevel").strip()
        if not top or os.path.realpath(top) != raiz:
            continue
        repo_ok = repo
        resto, saltar, tras_guiones = [], False, False
        for a in argv[1:]:
            if saltar:
                saltar = False
                continue
            if a == "--":
                tras_guiones = True
                continue
            if not tras_guiones and a in ("-C", "-m", "-F", "-c", "--author", "--date", "-t"):
                saltar = True
                continue
            if not tras_guiones and a.startswith("-"):
                # commit -a / -am, add -A / -u: entra todo lo versionado que cambio.
                if a in ("--all", "--update") or (not a.startswith("--") and a[1:].isalpha()
                                                  and set(a[1:]) & {"a", "A", "u"}):
                    resto.append(".")
                continue
            resto.append(a)
        if not resto or resto[0] not in ("add", "commit"):
            continue
        hay_commit |= resto[0] == "commit"
        for p in resto[1:]:
            rutas.update(_git(repo, "diff", "HEAD", "--name-only", "--", p).split())
    if not hay_commit or repo_ok is None:
        return
    # Lo que el comando agrega entra como esta en el arbol; lo ya indexado entra como
    # esta en el indice. Comparar el indice contra el arbol bloquearia el metodo que este
    # guard recomienda (armar el archivo desde HEAD y subirlo con update-index).
    indice = set(_git(raiz, "diff", "--cached", "--name-only").split()) - rutas
    if not rutas and not indice:
        return
    texto = _texto_de_la_sesion(payload)
    if texto is None:
        return
    ajenas = []
    for r in sorted(rutas | indice):
        base = ("diff", "HEAD") if r in rutas else ("diff", "--cached")
        for l in _git(raiz, *base, "-U0", "--no-color", "--", r).splitlines()[:400]:
            if l.startswith("+") and not l.startswith("+++") and not _es_propia(l[1:], texto):
                ajenas.append("  %s: %s" % (r, l[1:].strip()[:110]))
    if ajenas:
        extra = ["  ... y %d mas" % (len(ajenas) - 8)] if len(ajenas) > 8 else []
        deny(RAZON_AJENO.format(lineas="\n".join(ajenas[:8] + extra)))


# ---------------------------------------------------------------------------
# guard-plan-decide (opcional): un plan que cierra una decision sin nombrarla
# ---------------------------------------------------------------------------

ETIQUETAS_PLAN = ("decide:", "opciones evaluadas:", "variable que decide:",
                  "restricciones declaradas:")

RAZON_PLAN = (
    "guard-plan-decide bloquea el plan porque no declara: {faltantes}. Un plan que cierra una "
    "decision sin nombrar las opciones, la variable que elige entre ellas o una restriccion que el "
    "usuario ya declaro termina rechazado una y otra vez. Agregar al plan, en cualquier parte, las "
    "cuatro etiquetas: 'Decide: <que>', 'Opciones evaluadas: <lista>', 'Variable que decide: <cual, "
    "con su fuente>' (o 'not_available' con la razon), 'Restricciones declaradas: <las que el "
    "usuario ya puso, o \"ninguna\">'. Si el plan es de pura ejecucion, basta con 'Decide: ninguna'.")


def plan_decide(plan):
    texto = (plan or "").lower()
    if re.search(r"decide:\s*ninguna\b", texto):
        return
    faltantes = [e.rstrip(":") for e in ETIQUETAS_PLAN if e not in texto]
    if faltantes:
        deny(RAZON_PLAN.format(faltantes=", ".join(faltantes)))


def main():
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except ValueError:
        return
    entrada = payload.get("tool_input") or {}
    if sys.argv[1] == "plan-decide":
        plan_decide(entrada.get("plan") or "")
        return
    cmd = entrada.get("command") or ""
    cwd = payload.get("cwd") or entrada.get("cwd") or ""
    if not cmd:
        return
    if sys.argv[1] == "commit-ajeno":
        stash_raiz(cmd, cwd)
        commit_ajeno(cmd, cwd, payload)
        return
    if sys.argv[1] == "outward":
        outward(cmd, cwd)


if __name__ == "__main__":
    main()
