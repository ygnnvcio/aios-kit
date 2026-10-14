#!/usr/bin/env bash
# PreToolUse (Bash): actuar hacia afuera sin que el usuario lo confirme.
# Pregunta antes de mergear un PR, comentar, abrir PR o issue, o publicar un
# release, tambien si se intenta por `gh api`. El permiso tecnico resuelve el
# "puedo"; no resuelve el "debo". Logica y razones en guards.py.
set -uo pipefail
exec python3 "$(dirname "$0")/guards.py" outward
