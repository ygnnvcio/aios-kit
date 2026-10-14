#!/usr/bin/env bash
# PreToolUse (Bash): varias sesiones de Claude sobre la misma copia del repo.
#
# `git add/commit <ruta>` sube el archivo entero, no solo las lineas propias.
# Solo actua cuando el comando trae un `git commit` en la raiz de este repo:
# cada linea agregada (de 25 caracteres o mas) tiene que aparecer en algo que
# esta sesion o sus subagentes mandaron a una herramienta. Lo que sale de un
# script de la sesion se commitea con el prefijo AJENO_OK=1. Sin transcript
# legible, deja pasar. Ademas frena `git stash` y `--autostash` en esta raiz.
set -uo pipefail
exec python3 "$(dirname "$0")/guards.py" commit-ajeno
