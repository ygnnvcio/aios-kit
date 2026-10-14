#!/bin/bash
# Arma en una carpeta local el esqueleto de una wiki COMPARTIDA (un repo aparte que
# varias personas leen y escriben por PR). No crea nada en GitHub ni invita a nadie:
# eso lo hace el dueno a mano (ver README del kit, seccion "Wiki compartida").
#
#   bash scripts/nueva_wiki_compartida.sh ~/wikis/mi-negocio "Wiki de mi negocio"
#
# Compatible con el bash 3.2 de macOS.
set -euo pipefail

destino="${1:-}"
titulo="${2:-Wiki compartida}"
if [ -z "$destino" ]; then
  echo "Uso: bash scripts/nueva_wiki_compartida.sh <carpeta-destino> [\"Titulo\"]" >&2
  exit 1
fi
kit="$(cd "$(dirname "$0")/.." && pwd)"
if [ -e "$destino/wiki" ]; then
  echo "Ya existe $destino/wiki: no se pisa nada." >&2
  exit 1
fi

# Solo las herramientas y el esquema: nunca las paginas de la wiki privada de quien lo corre.
mkdir -p "$destino/wiki/tools" "$destino/wiki/templates" "$destino/raw/llm-wiki"
cp "$kit/wiki/tools/wiki.py" "$destino/wiki/tools/wiki.py"
cp "$kit/wiki/SCHEMA.md" "$destino/wiki/SCHEMA.md"
cp "$kit/wiki/templates/pagina.md" "$destino/wiki/templates/pagina.md"
for d in personas proyectos sistemas conceptos sintesis; do
  mkdir -p "$destino/wiki/$d"
  touch "$destino/wiki/$d/.gitkeep"
done
printf '{\n  "sources": []\n}\n' > "$destino/wiki/manifest.json"
printf '# Indice de la wiki\n\nToda pagina de conocimiento aparece aqui. Reglas: [Esquema](SCHEMA.md) - Fuentes: [catalogo](sources.md) - Historial: [log](log.md)\n\n## Conceptos\n\n## Sistemas y herramientas\n\n## Proyectos\n\n## Personas\n\n## Sintesis\n' > "$destino/wiki/index.md"
printf '# Log de la wiki\n\nAppend-only. Cada captura, ingesta y consulta guardada deja una linea.\n' > "$destino/wiki/log.md"
touch "$destino/.wiki-compartida"
touch "$destino/raw/llm-wiki/.gitkeep"
printf '__pycache__/\n.DS_Store\nwiki/.manifest.lock\n' > "$destino/.gitignore"

cat > "$destino/README.md" <<EOF
# $titulo

Wiki compartida: conocimiento del proyecto común, con sus fuentes. La leen y la escriben
varias personas, cada una con su propio Claude. Reglas de contenido e ingesta: [wiki/SCHEMA.md](wiki/SCHEMA.md).

## Reglas de esta wiki

| Regla | Por qué |
|---|---|
| Solo conocimiento del proyecto común | Lo personal (datos médicos, finanzas propias, identidad, familia) vive en la wiki privada de cada uno, nunca aquí |
| Se escribe por rama y PR, nunca directo a la rama principal | Cada aporte queda revisable y nadie pisa el trabajo del otro |
| Un PR = una fuente o un tema | Es fácil de revisar y de revertir |
| Los originales de fuera del repo se registran solo por nombre | El archivo \`.wiki-compartida\` de la raíz activa eso en \`wiki.py\`: ninguna ruta personal entra al repo |
| \`python3 wiki/tools/wiki.py check\` en verde antes de abrir el PR | Un manifiesto roto se lo come el que viene después |

## Flujo para aportar

\`\`\`bash
git pull
git switch -c wiki/<tema-corto>
python3 wiki/tools/wiki.py capture <archivo> --title "Título"
# leer, sintetizar, editar páginas, index.md y log.md (wiki/SCHEMA.md § Ingestar)
python3 wiki/tools/wiki.py integrate SNN --pages <carpeta>/<pagina>.md --scope "qué se sintetizó"
python3 wiki/tools/wiki.py catalog && python3 wiki/tools/wiki.py check
git add -A && git commit -m "wiki: <tema>"
git push -u origin HEAD
gh pr create --fill
\`\`\`
EOF

echo "Listo: $destino"
echo "Siguiente (lo hace el dueno, a mano):"
echo "  cd \"$destino\" && git init -b main && git add -A && git commit -m 'wiki compartida: esqueleto'"
echo "  gh repo create <cuenta>/<nombre> --private --source . --push"
echo "  invitar a cada persona: gh api -X PUT repos/<cuenta>/<nombre>/collaborators/<usuario> -f permission=push"
