#!/usr/bin/env python3
"""Lo que quedo atras en el repo del AIOS: sin commitear, sin subir o solo en este equipo.

Mide en el repo y en cada uno de sus worktrees:
  - archivos sin commitear quietos hace mas de --horas (default 6): trabajo olvidado
  - commits que no estan en ningun remoto: si el disco muere, se pierden
  - ramas locales con commits que no estan en ningun remoto
  - ramas cuyo upstream ya no existe (": gone"), y si su trabajo ya esta en la rama principal

Uso:
  python3 scripts/estado_git.py              # hace git fetch antes de medir
  python3 scripts/estado_git.py --sin-fetch
  python3 scripts/estado_git.py --json

Solo lectura salvo `git fetch`. Nunca commitea, sube, borra ni mergea: eso lo decide
el usuario. Compatible con el python3 que trae macOS (3.9); no usa stat ni sed.
"""
import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def sh(args, cwd=None):
    r = subprocess.run(args, cwd=cwd, capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else ""


def git(repo, *args):
    return sh(["git", "-C", str(repo)] + list(args))


def rama_principal(repo):
    ref = git(repo, "symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD").strip()
    if ref:
        return ref
    for r in ("origin/main", "origin/master"):
        if git(repo, "rev-parse", "--verify", "--quiet", r).strip():
            return r
    return ""


def sin_remoto(repo, ref):
    return [l for l in git(repo, "rev-list", ref, "--not", "--remotes").splitlines() if l]


def medir(repo, horas, fetch):
    if fetch:
        git(repo, "fetch", "--quiet", "--prune")
    hallazgos, ahora = [], time.time()
    tiene_remoto = bool(git(repo, "remote").strip())
    principal = rama_principal(repo)
    out = git(repo, "worktree", "list", "--porcelain")
    arboles = [l[9:] for l in out.splitlines() if l.startswith("worktree ")]
    for arbol in arboles:
        if not os.path.isdir(arbol):
            hallazgos.append({"tipo": "worktree_perdido", "donde": arbol,
                              "texto": "worktree registrado pero la carpeta no existe (git worktree prune lo limpia)"})
            continue
        quietos = []
        for l in git(arbol, "status", "--porcelain", "-uall").splitlines():
            ruta = l[3:].strip().strip('"').split(" -> ")[-1]
            try:
                edad = (ahora - os.path.getmtime(os.path.join(arbol, ruta))) / 3600
            except OSError:
                edad = horas + 1  # borrado sin commitear
            if edad > horas:
                quietos.append(ruta)
        if quietos:
            hallazgos.append({"tipo": "sin_commitear", "donde": arbol,
                              "texto": "%d archivos sin commitear quietos hace mas de %d h (p. ej. %s)"
                                       % (len(quietos), horas, quietos[0])})
        if tiene_remoto:
            n = len(sin_remoto(arbol, "HEAD"))
            if n:
                rama = git(arbol, "rev-parse", "--abbrev-ref", "HEAD").strip()
                hallazgos.append({"tipo": "sin_subir", "donde": arbol,
                                  "texto": "%s: %d commits que no estan en ningun remoto" % (rama, n)})
    if not tiene_remoto:
        hallazgos.append({"tipo": "sin_remoto", "donde": str(repo),
                          "texto": "el repo no tiene remoto: todo vive solo en este equipo"})
        return hallazgos
    en_arbol = {l[18:] for l in out.splitlines() if l.startswith("branch refs/heads/")}
    for linea in git(repo, "for-each-ref", "refs/heads",
                     "--format=%(refname:short)\t%(upstream:track)").splitlines():
        rama, _, track = linea.partition("\t")
        if "[gone]" in track:
            contenida = bool(principal) and subprocess.run(
                ["git", "-C", str(repo), "merge-base", "--is-ancestor", rama, principal]).returncode == 0
            hallazgos.append({"tipo": "upstream_gone", "donde": rama,
                              "texto": "rama %s: su remoto ya no existe; %s" % (
                                  rama, "su trabajo ya esta en " + principal + " (se puede borrar)" if contenida
                                  else "su trabajo NO esta en la rama principal (no borrar sin revisar)")})
            continue
        if rama in en_arbol:
            continue
        n = len(sin_remoto(repo, rama))
        if n:
            hallazgos.append({"tipo": "rama_local", "donde": rama,
                              "texto": "rama %s: %d commits solo en este equipo" % (rama, n)})
    return hallazgos


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--repo", default=str(RAIZ))
    p.add_argument("--horas", type=int, default=6)
    p.add_argument("--sin-fetch", action="store_true")
    p.add_argument("--json", action="store_true")
    a = p.parse_args(argv)
    if not git(a.repo, "rev-parse", "--git-dir").strip():
        print("not_available: %s no es un repo de git" % a.repo)
        return 1
    hallazgos = medir(a.repo, a.horas, not a.sin_fetch)
    if a.json:
        print(json.dumps(hallazgos, ensure_ascii=False, indent=2))
        return 0
    if not hallazgos:
        print("Limpio: nada sin commitear, sin subir ni solo en este equipo.")
        return 0
    print("| Tipo | Donde | Detalle |\n|---|---|---|")
    for h in hallazgos:
        print("| %s | `%s` | %s |" % (h["tipo"], h["donde"].replace(str(Path.home()), "~"), h["texto"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
