#!/usr/bin/env python3
"""UserPromptSubmit: stop de tokens.

Mide la sesion viva leyendo su transcript y le inyecta a Claude la orden de abrir
(o cerrar) la respuesta con un AVISO o un STOP. No bloquea el mensaje: bloquearlo
lo borraria.

Dos medidas, la que llegue primero:
  - tokens acumulados de la sesion (entrada + cache + salida de cada turno), en millones
  - contexto del ultimo turno (lo que cuesta cada mensaje nuevo), en tokens

Umbrales como parametro (ver .claude/settings.example.json):
  python3 token-stop.py --aviso-m 30 --stop-m 60 --aviso-ctx 120000 --stop-ctx 160000

Los valores por defecto sirven para una ventana de contexto de 200k. Para
calibrarlos con tus propias sesiones:
  python3 .claude/hooks/token-stop.py --medir
imprime la mediana, p75 y p90 de tus sesiones de este proyecto y los flags
sugeridos (AVISO en tu p75, STOP entre p75 y p90).

Para no gastar tokens avisando, repite solo cada --repetir-m millones. Falla en
silencio: un hook de medicion roto no puede frenar el trabajo.

Compatible con el python3 que trae macOS (3.9).
"""
import argparse
import glob
import json
import os
import re
import sys

TMP = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tmp")
RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def argumentos(argv=None):
    p = argparse.ArgumentParser(description="Aviso y stop de tokens por sesion")
    p.add_argument("--aviso-m", type=float, default=30, help="millones acumulados para el AVISO")
    p.add_argument("--stop-m", type=float, default=60, help="millones acumulados para el STOP")
    p.add_argument("--aviso-ctx", type=int, default=120_000, help="contexto por turno para el AVISO")
    p.add_argument("--stop-ctx", type=int, default=160_000, help="contexto por turno para el STOP")
    p.add_argument("--repetir-m", type=float, default=15, help="no repetir el mismo nivel antes de +N millones")
    p.add_argument("--medir", action="store_true", help="calibrar con las sesiones de este proyecto y salir")
    return p.parse_args(argv)


def medir(path):
    total = ctx = turnos = maximo = 0
    with open(path, errors="ignore") as fh:
        for linea in fh:
            if '"usage"' not in linea:
                continue
            try:
                d = json.loads(linea)
                if d.get("type") != "assistant":
                    continue
                u = d["message"]["usage"]
            except Exception:
                continue
            c = (u.get("input_tokens", 0) + u.get("cache_read_input_tokens", 0)
                 + u.get("cache_creation_input_tokens", 0))
            total += c + u.get("output_tokens", 0)
            ctx = c
            maximo = max(maximo, c)
            turnos += 1
    return total / 1e6, ctx, turnos, maximo


def percentil(valores, p):
    v = sorted(valores)
    if not v:
        return 0
    k = (len(v) - 1) * p
    i = int(k)
    j = min(i + 1, len(v) - 1)
    return v[i] + (v[j] - v[i]) * (k - i)


def calibrar():
    """Distribucion de las sesiones de este proyecto (y sus worktrees)."""
    slug = re.sub(r"[^a-zA-Z0-9]", "-", RAIZ)
    carpetas = glob.glob(os.path.join(os.path.expanduser("~/.claude/projects"), slug + "*"))
    totales, maximos = [], []
    for c in carpetas:
        for f in glob.glob(os.path.join(c, "*.jsonl")):
            t, _, turnos, mx = medir(f)
            if turnos >= 3:
                totales.append(t)
                maximos.append(mx)
    if len(totales) < 10:
        print("Hay %d sesiones medibles de este proyecto; con menos de 10 los percentiles no dicen mucho. "
              "Usa los valores por defecto y vuelve a medir en unas semanas." % len(totales))
        if not totales:
            return
    print("Sesiones medidas: %d" % len(totales))
    print("| Medida | Mediana | p75 | p90 |")
    print("|---|---|---|---|")
    print("| Millones acumulados | %.0f | %.0f | %.0f |" % tuple(percentil(totales, p) for p in (.5, .75, .9)))
    print("| Contexto maximo (k) | %.0f | %.0f | %.0f |" % tuple(percentil(maximos, p) / 1000 for p in (.5, .75, .9)))
    p75, p90 = percentil(totales, .75), percentil(totales, .9)
    c75, c90 = percentil(maximos, .75), percentil(maximos, .9)
    print("\nFlags sugeridos (AVISO en tu p75, STOP a mitad de camino entre p75 y p90):")
    print("--aviso-m %.0f --stop-m %.0f --aviso-ctx %d --stop-ctx %d"
          % (max(p75, 1), max((p75 + p90) / 2, p75 + 1), int(round(c75, -3)), int(round((c75 + c90) / 2, -3))))


def main():
    a = argumentos()
    if a.medir:
        calibrar()
        return
    try:
        ev = json.load(sys.stdin)
        path = ev.get("transcript_path") or ""
        if not os.path.isfile(path):
            return
        total_m, ctx, turnos, _ = medir(path)
        if total_m >= a.stop_m or ctx >= a.stop_ctx:
            nivel = "STOP"
        elif total_m >= a.aviso_m or ctx >= a.aviso_ctx:
            nivel = "AVISO"
        else:
            return

        os.makedirs(TMP, exist_ok=True)
        estado = os.path.join(TMP, "token-stop-%s.json" % ev.get("session_id", "x"))
        previo = {}
        if os.path.isfile(estado):
            try:
                with open(estado) as fh:
                    previo = json.load(fh)
            except Exception:
                previo = {}
        if previo.get("nivel") == nivel and total_m - previo.get("total_m", 0) < a.repetir_m:
            return
        with open(estado, "w") as fh:
            json.dump({"nivel": nivel, "total_m": total_m}, fh)

        costo_turno = ctx / 1000
        if nivel == "STOP":
            orden = ("STOP DE TOKENS. Abre tu respuesta con una linea que diga exactamente: "
                     "'STOP de tokens: esta sesion lleva %.0f M en %d turnos y cada mensaje nuevo cuesta ~%.0fk.' "
                     "Despues, en 3 lineas maximo, el resumen (que se resolvio, que falta, archivos tocados). "
                     "Si queda trabajo: commitea y sube lo necesario y deja la continuacion a un clic. Si tienes la "
                     "herramienta spawn_task (mcp__ccd_session__spawn_task, app de escritorio de Claude), usala con un "
                     "prompt autosuficiente (rutas, commits, estado y que entregar). Si no la tienes, escribe ese mismo "
                     "prompt en .claude/tmp/traspaso.md y di la ruta. Nunca le pidas al usuario que reconstruya el "
                     "contexto a mano. Si el pedido actual es corto y cerrarlo aca es mas barato que recargar "
                     "contexto, respondelo y pon el STOP al final."
                     % (total_m, turnos, costo_turno))
        else:
            orden = ("AVISO DE TOKENS. Cierra tu respuesta con una sola linea: "
                     "'Aviso de tokens: %.0f M en %d turnos, ~%.0fk por mensaje. Si cambias de tema, chat nuevo o /clear; "
                     "si sigues en este, /compact.' No agregues nada mas sobre el tema."
                     % (total_m, turnos, costo_turno))
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "UserPromptSubmit",
                                                 "additionalContext": orden}}))
    except Exception:
        return


if __name__ == "__main__":
    main()
