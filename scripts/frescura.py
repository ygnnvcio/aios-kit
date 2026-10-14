#!/usr/bin/env python3
"""Frescura medida: compara la fecha que un archivo declara con su ultimo commit.

POR QUE EXISTE
--------------
Las cabeceras "Ultima actualizacion: AAAA-MM-DD" se escriben a mano y mienten
sin que nadie lo note: un archivo de contexto puede declarar una fecha de hace un
mes mientras su ultimo commit es de ayer. Si la fecha la corrige Claude por su
cuenta, deja de ser la senal que dice si confiar en el contenido.

Esta pieza no escribe ninguna fecha. Solo mide. Una afirmacion vale mientras su
comprobacion sea posterior al ultimo cambio de aquello de lo que depende.

CUATRO ESTADOS, NUNCA DOS
-------------------------
  SOSTENIDA        la fecha declarada es igual o posterior al ultimo commit
  DESACTUALIZADA   el archivo cambio en un commit posterior a la fecha declarada
  SIN COMMITEAR    tiene cambios en el arbol de trabajo: la medicion no es estable
  NO COMPROBABLE   no declara fecha, no esta en git, o no existe

NO COMPROBABLE no se colapsa en SOSTENIDA: no saber no es saber que esta bien.

Uso:
  python3 scripts/frescura.py                 # STATUS.md, context/*.md e imports @ de CLAUDE.md
  python3 scripts/frescura.py context/me.md   # archivos puntuales
  python3 scripts/frescura.py --json

Solo lectura. Compatible con el python3 que trae macOS (3.9).
"""
import argparse
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
CABECERA = re.compile(r"(ltima (actualizaci|revisi)|last (updated|reviewed))", re.IGNORECASE)
FECHA = re.compile(r"\d{4}-\d{2}-\d{2}")
IMPORT = re.compile(r"^@(\S+)\s*$", re.MULTILINE)

SOSTENIDA = "SOSTENIDA"
DESACTUALIZADA = "DESACTUALIZADA"
SIN_COMMITEAR = "SIN COMMITEAR"
NO_COMPROBABLE = "NO COMPROBABLE"


def fecha_declarada(texto, lineas=40):
    """Primera fecha de la primera linea de cabecera, dentro de las primeras lineas."""
    for linea in texto.splitlines()[:lineas]:
        if CABECERA.search(linea):
            m = FECHA.search(linea)
            if m:
                return m.group(0)
    return None


def _git(raiz, *args):
    r = subprocess.run(["git", "-C", str(raiz)] + list(args), capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else None


def archivos_por_defecto(raiz):
    salida = []
    if (raiz / "STATUS.md").exists():
        salida.append("STATUS.md")
    contexto = raiz / "context"
    if contexto.is_dir():
        salida += sorted(str(p.relative_to(raiz)) for p in contexto.glob("*.md"))
    claude = raiz / "CLAUDE.md"
    if claude.exists():
        salida += [i for i in IMPORT.findall(claude.read_text(encoding="utf-8")) if i not in salida]
    return salida


def medir(raiz, relativo):
    ruta = raiz / relativo
    fila = {"archivo": relativo, "declarada": None, "ultimo_commit": None,
            "dias": None, "estado": NO_COMPROBABLE, "razon": None}
    if not ruta.exists():
        fila["razon"] = "no existe"
        return fila
    fila["declarada"] = fecha_declarada(ruta.read_text(encoding="utf-8"))
    fila["ultimo_commit"] = _git(raiz, "log", "-1", "--format=%cs", "--", relativo) or None
    if _git(raiz, "status", "--porcelain", "--", relativo):
        fila["estado"], fila["razon"] = SIN_COMMITEAR, "cambios sin commitear"
        return fila
    if not fila["declarada"]:
        fila["razon"] = "sin cabecera de fecha"
        return fila
    if not fila["ultimo_commit"]:
        fila["razon"] = "sin historia en git"
        return fila
    dias = (date.fromisoformat(fila["ultimo_commit"]) - date.fromisoformat(fila["declarada"])).days
    fila["dias"] = dias
    fila["estado"] = DESACTUALIZADA if dias > 0 else SOSTENIDA
    return fila


def tabla(filas):
    out = ["| Archivo | Declara | Ultimo commit | Dias de deriva | Estado |",
           "|---|---|---|---|---|"]
    for f in filas:
        dias = f["dias"] if f["dias"] is not None else (f["razon"] or "-")
        out.append("| `{}` | {} | {} | {} | {} |".format(
            f["archivo"], f["declarada"] or "-", f["ultimo_commit"] or "-", dias, f["estado"]))
    return "\n".join(out)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("archivos", nargs="*", help="rutas relativas a la raiz")
    p.add_argument("--json", action="store_true")
    p.add_argument("--raiz", default=str(RAIZ))
    a = p.parse_args(argv)
    raiz = Path(a.raiz)
    filas = [medir(raiz, r) for r in (a.archivos or archivos_por_defecto(raiz))]
    if a.json:
        print(json.dumps(filas, ensure_ascii=False, indent=2))
    else:
        print(tabla(filas))
        n = sum(1 for f in filas if f["estado"] == DESACTUALIZADA)
        print("\n{} de {} con deriva.".format(n, len(filas)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
