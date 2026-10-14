#!/usr/bin/env python3
"""Dos chequeos de /alignment-check que se pueden medir sin criterio.

  python3 scripts/revisar.py rutas           # rutas citadas en CLAUDE.md y AGENTS.md que no existen
  python3 scripts/revisar.py skills [--dias 30]
        # cuantas veces se uso cada skill de .claude/skills/, leyendo los transcripts
        # de Claude Code de este proyecto (~/.claude/projects/<ruta-con-guiones>*/)

Solo lectura. Compatible con el python3 que trae macOS (3.9).
"""
import argparse
import glob
import json
import os
import re
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
EXTENSIONES = (".md", ".py", ".sh", ".json", ".jsonl", ".txt", ".html", ".yml", ".yaml")


def candidatos(texto):
    texto = re.sub(r"```.*?```", "", texto, flags=re.S)
    for m in re.finditer(r"`([^`\n]+)`", texto):
        yield m.group(1).strip()
    for m in re.finditer(r"\]\(([^)\s]+)\)", texto):
        yield m.group(1).strip().strip("<>")


def parece_ruta(c):
    if not c or " " in c or "://" in c or c.startswith(("#", "~", "$", "-", "/")):
        return False
    if any(x in c for x in ("<", ">", "{", "}", "*", "AAAA", "YYYY", "...")):
        return False
    return "/" in c or c.endswith(EXTENSIONES)


def rutas(raiz):
    rotas = []
    for nombre in ("CLAUDE.md", "AGENTS.md"):
        f = raiz / nombre
        if not f.exists():
            continue
        vistas = set()
        for c in candidatos(f.read_text(encoding="utf-8")):
            c = c.split("#")[0].rstrip("/")
            if not parece_ruta(c) or c in vistas:
                continue
            vistas.add(c)
            if (raiz / c).exists() or (raiz / ".claude" / c).exists():
                continue
            # Un nombre suelto ("team.md" junto a "context/me.md") vale si existe en alguna carpeta del repo.
            if "/" not in c and any(".git" not in p.parts for p in raiz.rglob(c)):
                continue
            rotas.append((nombre, c))
    if not rotas:
        print("Rutas: todas las citadas en CLAUDE.md y AGENTS.md existen.")
        return 0
    print("| Archivo | Ruta citada que no existe |\n|---|---|")
    for nombre, c in rotas:
        print("| %s | `%s` |" % (nombre, c))
    return 0


def skills(raiz, dias):
    nombres = sorted(p.parent.name for p in (raiz / ".claude" / "skills").glob("*/SKILL.md"))
    if not nombres:
        print("No hay skills en .claude/skills/.")
        return 0
    slug = re.sub(r"[^a-zA-Z0-9]", "-", str(raiz))
    carpetas = glob.glob(os.path.join(os.path.expanduser("~/.claude/projects"), slug + "*"))
    corte = time.time() - dias * 86400
    usos = {n: 0 for n in nombres}
    ultimo = {n: 0.0 for n in nombres}
    sesiones = 0
    for c in carpetas:
        for f in glob.glob(os.path.join(c, "*.jsonl")) + glob.glob(os.path.join(c, "*", "subagents", "*.jsonl")):
            mt = os.path.getmtime(f)
            if mt < corte:
                continue
            sesiones += 1
            with open(f, errors="ignore") as fh:
                for linea in fh:
                    if '"Skill"' not in linea and "command-name" not in linea:
                        continue
                    for n in nombres:
                        if ('"skill":"%s"' % n) in linea.replace(" ", "") or ("<command-name>/%s</command-name>" % n) in linea:
                            usos[n] += 1
                            ultimo[n] = max(ultimo[n], mt)
    if not carpetas:
        print("not_available: no hay transcripts de este proyecto en ~/.claude/projects (slug %s)" % slug)
        return 0
    print("Transcripts leidos: %d sesiones de los ultimos %d dias\n" % (sesiones, dias))
    print("| Skill | Usos | Ultimo uso |\n|---|---|---|")
    for n in sorted(nombres, key=lambda x: usos[x]):
        fecha = time.strftime("%Y-%m-%d", time.localtime(ultimo[n])) if ultimo[n] else "-"
        print("| %s | %d | %s |" % (n, usos[n], fecha))
    sin_uso = [n for n in nombres if not usos[n]]
    if sin_uso:
        print("\nSin uso en %d dias: %s. Sin uso no es inutil: revisar si su proyecto sigue vivo antes de archivar."
              % (dias, ", ".join(sin_uso)))
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("rutas")
    s = sub.add_parser("skills")
    s.add_argument("--dias", type=int, default=30)
    p.add_argument("--raiz", default=str(RAIZ))
    a = p.parse_args(argv)
    raiz = Path(a.raiz)
    return rutas(raiz) if a.cmd == "rutas" else skills(raiz, a.dias)


if __name__ == "__main__":
    sys.exit(main())
