#!/usr/bin/env bash
# PreToolUse (ExitPlanMode), OPCIONAL: un plan que cierra una decision sin
# declarar que decide, que opciones evaluo, que variable elige entre ellas y
# que restricciones ya puso el usuario. "Decide: ninguna" lo deja pasar para
# planes de pura ejecucion. Activarlo solo si te pasa que los planes cierran
# decisiones sin mostrar las alternativas.
set -uo pipefail
exec python3 "$(dirname "$0")/guards.py" plan-decide
