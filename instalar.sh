#!/bin/bash
# Copia las piezas del kit sobre un AIOS ya armado con AIS-OS. NUNCA pisa un archivo
# que ya existe: lo salta y lo avisa. Despues corre las pruebas en el destino.
#
#   bash instalar.sh ~/ruta/a/mi-aios
#
# Compatible con el bash 3.2 y las herramientas BSD que trae macOS.
set -euo pipefail

destino="${1:-}"
if [ -z "$destino" ] || [ ! -d "$destino" ]; then
  echo "Uso: bash instalar.sh <carpeta-de-tu-aios>   (la carpeta tiene que existir)" >&2
  exit 1
fi
destino="$(cd "$destino" && pwd)"
kit="$(cd "$(dirname "$0")" && pwd)"
if [ "$destino" = "$kit" ]; then
  echo "El destino es el kit mismo: apunta a la carpeta de tu AIOS." >&2
  exit 1
fi
if [ ! -f "$destino/CLAUDE.md" ]; then
  echo "Aviso: $destino no tiene CLAUDE.md. ¿Ya instalaste AIS-OS y corriste /onboard? Sigo igual."
fi

copiados=0
saltados=""
copiar() {  # copiar <ruta relativa al kit>
  local rel="$1"
  if [ -e "$destino/$rel" ]; then
    saltados="$saltados $rel"
    return
  fi
  mkdir -p "$(dirname "$destino/$rel")"
  cp -p "$kit/$rel" "$destino/$rel"
  copiados=$((copiados + 1))
}

# Reglas, hooks, skills, scripts y plantillas de logs.
for f in $(cd "$kit" && find .claude/rules .claude/hooks .claude/skills scripts -type f \
             ! -name '.DS_Store' ! -path '*/__pycache__/*' | sort); do
  copiar "${f#./}"
done
copiar .claude/settings.example.json

# El README y el bloque para CLAUDE.md quedan como referencia dentro del AIOS.
for par in "README.md:references/aios-kit.md" "CLAUDE-snippet.md:references/aios-kit-snippet.md"; do
  src="${par%%:*}"; dst="${par#*:}"
  if [ -e "$destino/$dst" ]; then
    saltados="$saltados $dst"
  else
    mkdir -p "$destino/references"
    cp -p "$kit/$src" "$destino/$dst"
    copiados=$((copiados + 1))
  fi
done
for f in LEARNING-LOG.md PATTERN-LOG.md AUDIT-LOG.md; do
  copiar "$f"
done

# La wiki va entera solo si el AIOS todavia no tiene una.
if [ -e "$destino/wiki" ]; then
  echo "Ya existe wiki/: copio solo wiki/tools/wiki.py y wiki/SCHEMA.md si faltan."
  copiar wiki/tools/wiki.py
  copiar wiki/SCHEMA.md
else
  for f in $(cd "$kit" && find wiki -type f ! -name '.manifest.lock' ! -name '.DS_Store' | sort); do
    copiar "$f"
  done
fi

# Hooks activos: settings.json solo se crea si no existe; si existe, se fusiona a mano.
if [ ! -e "$destino/.claude/settings.json" ]; then
  cp "$kit/.claude/settings.example.json" "$destino/.claude/settings.json"
  echo "Creado .claude/settings.json con los hooks del kit."
else
  echo "Ya tienes .claude/settings.json: fusiona a mano el bloque \"hooks\" de .claude/settings.example.json"
  echo "(o pidele a Claude: 'fusiona los hooks de .claude/settings.example.json en .claude/settings.json')."
fi

# .gitignore: agrega lo que falte, sin duplicar.
touch "$destino/.gitignore"
for linea in ".claude/tmp/" "__pycache__/" ".DS_Store" "wiki/.manifest.lock"; do
  grep -qxF "$linea" "$destino/.gitignore" || printf '%s\n' "$linea" >> "$destino/.gitignore"
done

chmod +x "$destino"/.claude/hooks/*.sh "$destino"/.claude/hooks/*.py "$destino"/scripts/*.py "$destino"/scripts/*.sh \
         "$destino"/wiki/tools/wiki.py "$destino"/.claude/skills/video-scout/scripts/*.py 2>/dev/null || true

echo
echo "Copiados: $copiados archivos."
if [ -n "$saltados" ]; then
  echo "Saltados porque ya existian (revisalos a mano):"
  for s in $saltados; do echo "  $s"; done
fi
echo
echo "Pruebas en el destino:"
cd "$destino" && /usr/bin/env python3 scripts/test_guards.py 2>&1 | tail -3
echo
echo "Falta un paso: abrir Claude Code en tu AIOS y pegar el Prompt 1 de references/aios-kit.md."
