#!/usr/bin/env python3
"""Wiki con fuentes: captura originales con SHA-256, registra su integracion y revisa la integridad.

Nunca llama a un LLM ni a una API externa. Las reglas de uso viven en wiki/SCHEMA.md.
Compatible con el python3 que trae macOS (3.9). Sin dependencias.

  python3 wiki/tools/wiki.py capture RUTA --title "Titulo"
  python3 wiki/tools/wiki.py integrate S01 --pages conceptos/x.md --scope "que se sintetizo"
  python3 wiki/tools/wiki.py integrate S02 --status reference --motivo "por que no aporta"
  python3 wiki/tools/wiki.py catalog
  python3 wiki/tools/wiki.py check
"""
import argparse
from contextlib import contextmanager
from datetime import date, datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[2]
WIKI = ROOT / 'wiki'
MANIFEST = WIKI / 'manifest.json'
KINDS = {'persona', 'proyecto', 'sistema', 'concepto', 'sintesis'}
# En una wiki compartida (archivo .wiki-compartida en la raiz) un original de fuera del repo se
# registra solo por su nombre: la ruta absoluta expondria la carpeta personal de quien capturo.
COMPARTIDA = (ROOT / '.wiki-compartida').exists()
EXTERNO = 'externo:'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def today():
    return date.today().isoformat()


def load():
    return json.loads(MANIFEST.read_text())


def save(data):
    """Escritura atómica y con el formato único del manifiesto. El manifiesto no se edita a mano."""
    tmp = MANIFEST.with_suffix('.json.tmp')
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    os.replace(tmp, MANIFEST)


@contextmanager
def locked():
    """Un solo escritor del manifiesto a la vez: leer, cambiar y guardar van dentro.

    Varias sesiones pueden cerrar juntas y escribir a la vez: sin candado, una pisa la
    lista `pages` de otra. flock se libera solo si el proceso muere."""
    with (WIKI / '.manifest.lock').open('w') as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def rel_link(path, parent=WIKI):
    return '<' + os.path.relpath(path, parent).replace(os.sep, '/') + '>'


def catalog(data):
    lines = ['# Fuentes de la wiki', '',
             'Snapshots exactos; la captura no cambia la fecha ni la certeza del contenido. '
             'El alcance indica qué se sintetizó, no una auditoría exhaustiva de cada documento.', '',
             '| ID | Fuente / original | Captura | Estado | Alcance |',
             '|---|---|---|---|---|']
    for s in data['sources']:
        origin = Path(s['origin'])
        live = origin if origin.is_absolute() else ROOT / origin
        if s['origin'].startswith(EXTERNO):
            live = ROOT / '.no-existe'
        title = s['title'].replace('|', '\\|').replace('\n', ' ')
        scope = s['scope'].replace('|', '\\|').replace('\n', ' ')
        # Original borrado o en un worktree que ya no existe: título sin enlace, el snapshot sigue.
        source_cell = f'[{title}]({rel_link(live)})' if live.is_file() else f'{title} (original no accesible)'
        lines.append(f'| {s["id"]} | {source_cell} | '
                     f'[{s["captured"]}]({rel_link(ROOT / s["snapshot"])}) | '
                     f'{s["status"]} | {scope} |')
    lines += ['', '## Integridad y procedencia', '',
              'El [manifiesto](manifest.json) conserva el SHA-256 completo, la ruta original, '
              'la revisión de git al capturar cuando corresponde y las páginas derivadas. '
              'Un original modificado genera un aviso; un snapshot alterado genera error.', '',
              'Los adjuntos externos pueden desaparecer: la copia cruda permanece. '
              'Leer el patrón aportado no implica abrir ni verificar los enlaces externos que menciona.', '',
              '[Índice](index.md) · [Esquema](SCHEMA.md) · [Historial](log.md)', '']
    (WIKI / 'sources.md').write_text('\n'.join(lines))


def capture(args):
    with locked():
        return _capture(args)


def integrate(args):
    """Marca una fuente como integrada o como referencia, sin editar el manifiesto a mano.

    `pages` se UNE a lo que ya haya: dos sesiones que integran la misma fuente en
    páginas distintas no se pisan. No escribe páginas: solo registra la derivación.

    `--quitar-pagina` es la única forma de deshacer: un SID escrito por error deja
    una arista falsa —la fuente dice sostener una página que no sostiene— y unir
    no la borra. Sigue valiendo que el manifiesto no se edita a mano: esto escribe
    con el mismo candado y formato."""
    pages = []
    for raw in args.pages or []:
        rel = raw if raw.startswith('wiki/') else f'wiki/{raw}'
        if not (ROOT / rel).is_file():
            raise ValueError(f'No existe la página: {rel}')
        pages.append(rel)
    quitar = []
    for raw in args.quitar_pagina or []:
        quitar.append(raw if raw.startswith('wiki/') else f'wiki/{raw}')
    if args.status == 'integrated' and not pages and not quitar:
        raise ValueError('integrated exige --pages; una fuente que no aporta va con --status reference --motivo')
    if args.status == 'reference' and not args.motivo:
        raise ValueError('reference exige --motivo')
    with locked():
        data = load()
        source = next((s for s in data['sources'] if s['id'] == args.id), None)
        if source is None:
            raise ValueError(f'No existe la fuente: {args.id}')
        antes = (source['status'], list(source['pages']))
        for page in pages:
            if page not in source['pages']:
                source['pages'].append(page)
        for page in quitar:
            if page in source['pages']:
                source['pages'].remove(page)
            else:
                raise ValueError(f'{args.id} no declara esa página: {page}')
        if quitar and not source['pages'] and source['status'] == 'integrated':
            raise ValueError(
                f'{args.id} quedaría integrada sin ninguna página. Pásale --status reference '
                '--motivo, o dale la página correcta con --pages en la misma llamada.')
        texto = args.scope or (f'Referencia, no integrada: {args.motivo}' if args.status == 'reference' else None)
        if texto:
            pendiente = source['status'] == 'pending' or source['scope'].startswith('Pendiente de lectura')
            if pendiente:
                source['scope'] = texto
            elif texto not in source['scope']:
                source['scope'] = f"{source['scope']} · {texto}"
        # Otra sesión pudo integrarla antes: integrated no baja a reference.
        if not (source['status'] == 'integrated' and args.status == 'reference'):
            source['status'] = args.status
        save(data)
        catalog(data)
    print(f"{args.id}: {antes[0]} -> {source['status']}; páginas: {', '.join(source['pages']) or 'ninguna'}")


def _capture(args):
    origin = Path(args.path).expanduser().resolve()
    if not origin.is_file():
        raise ValueError(f'No existe el archivo: {origin}')
    if origin.is_relative_to(WIKI) or origin.is_relative_to(ROOT / 'raw/llm-wiki'):
        raise ValueError('No ingerir la wiki o sus snapshots como evidencia de sí mismos.')
    data = load()
    content = origin.read_bytes()
    sha = hashlib.sha256(content).hexdigest()
    if origin.is_relative_to(ROOT):
        origin_name = str(origin.relative_to(ROOT))
    elif COMPARTIDA:
        origin_name = EXTERNO + origin.name
    else:
        origin_name = str(origin)
    for source in data['sources']:
        if source['origin'] == origin_name and source['sha256'] == sha:
            print(f'Ya capturada: {source["id"]} ({source["status"]}). Sin duplicar.')
            return
    num = max((int(s['id'][1:]) for s in data['sources']), default=0) + 1
    sid = f'S{num:02d}'
    safe_name = re.sub(r'[^a-zA-Z0-9._-]', '_', origin.name)
    target = ROOT / f'raw/llm-wiki/{today()}/{sid}-{sha[:12]}/{safe_name}'
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('xb') as handle:
        handle.write(content)
    source = dict(id=sid, title=args.title or origin.stem, origin=origin_name,
                  snapshot=str(target.relative_to(ROOT)), sha256=sha, captured=today(),
                  scope='Pendiente de lectura y síntesis por el agente', status='pending', pages=[])
    data['sources'].append(source)
    save(data)
    catalog(data)
    title = source['title'].replace('\n', ' ')
    with (WIKI / 'log.md').open('a') as handle:
        handle.write(f'\n## [{today()}] capture | {sid} · {title}\n\n'
                     'Fuente preservada con SHA-256. Pendiente de integración semántica.\n')
    print(f'{sid}: capturada. Pendiente de lectura, síntesis, enlaces y revisión.')


def metadata(text):
    if not text.startswith('---\n'):
        return {}
    result = {}
    for line in text.split('---', 2)[1].splitlines():
        if ':' in line:
            key, value = line.split(':', 1)
            result[key.strip()] = value.strip().strip('"')
    return result


def links(text, parent):
    # This wiki uses inline relative Markdown links (no wikilinks/reference links).
    text = re.sub(r'```.*?```', '', text, flags=re.S)
    for match in re.finditer(r'\[[^\]]*\]\((<[^>]+>|[^)]+)\)', text):
        target = match.group(1).strip().strip('<>')
        parsed = urlsplit(target)
        if parsed.scheme or target.startswith('#') or not parsed.path:
            continue
        yield (parent / unquote(parsed.path)).resolve()


def check(_args):
    data = load()
    errors, warnings = [], []
    sources = {s['id']: s for s in data['sources']}
    if len(sources) != len(data['sources']):
        errors.append('IDs de fuentes duplicados')
    latest = {}
    for s in data['sources']:
        latest[s['origin']] = s
        snapshot = ROOT / s['snapshot']
        if not snapshot.is_file() or digest(snapshot) != s['sha256']:
            errors.append(f'{s["id"]}: snapshot ausente o alterado')
        if s['status'] == 'pending':
            warnings.append(f'{s["id"]}: fuente pendiente de integrar')
        if s['status'] == 'integrated' and not s['pages']:
            errors.append(f'{s["id"]}: integrada sin páginas derivadas')
        for name in s['pages']:
            p = ROOT / name
            if not p.is_file():
                errors.append(f'{s["id"]}: página derivada ausente: {name}')
            elif s['id'] not in re.findall(r'S\d+', metadata(p.read_text()).get('sources', '')):
                errors.append(f'{s["id"]}: página no declara esta fuente: {name}')
    for s in latest.values():
        if s['origin'].startswith(EXTERNO):
            continue  # original fuera de la wiki compartida: solo cuenta la captura
        origin = Path(s['origin'])
        original = origin if origin.is_absolute() else ROOT / origin
        if not original.is_file():
            warnings.append(f'{s["id"]}: original no accesible; snapshot conservado')
        elif digest(original) != s['sha256']:
            warnings.append(f'{s["id"]}: original cambiado; revisar e ingerir nueva versión')
    paths = [p for p in WIKI.rglob('*.md') if 'templates' not in p.parts]
    contents = {p.resolve(): p.read_text() for p in paths}
    index_links = set(links((WIKI / 'index.md').read_text(), WIKI))
    knowledge = {p for p, t in contents.items() if metadata(t).get('type') in KINDS}
    inbound = {p: set() for p in knowledge}
    for p, text in contents.items():
        for target in links(text, p.parent):
            if not target.exists():
                # External original attachments can disappear without invalidating snapshots.
                if target.is_relative_to(ROOT):
                    errors.append(f'{p.relative_to(ROOT)}: enlace roto a {target.relative_to(ROOT)}')
                else:
                    warnings.append(f'{p.relative_to(ROOT)}: enlace externo local no disponible')
            if p in knowledge and target in knowledge and target != p:
                inbound[target].add(p)
        if p in knowledge:
            meta = metadata(text)
            for field in ('title', 'type', 'created', 'updated', 'evidence', 'sources'):
                if not meta.get(field):
                    errors.append(f'{p.name}: falta {field}')
            for field in ('created', 'updated'):
                try:
                    datetime.strptime(meta.get(field, ''), '%Y-%m-%d')
                except ValueError:
                    errors.append(f'{p.name}: fecha {field} inválida')
            ids = re.findall(r'S\d+', meta.get('sources', ''))
            if not ids:
                errors.append(f'{p.name}: sin fuentes')
            for sid in ids:
                if sid not in sources:
                    errors.append(f'{p.name}: fuente inexistente {sid}')
                elif str(p.relative_to(ROOT)) not in sources[sid]['pages']:
                    errors.append(f'{p.name}: falta derivación en manifiesto para {sid}')
            if p not in index_links:
                errors.append(f'{p.name}: no figura en índice')
    for p, refs in inbound.items():
        if not refs:
            warnings.append(f'{p.name}: sin enlaces entrantes de otras páginas de conocimiento')
    report = dict(pages=len(knowledge), sources=len(sources), errors=errors, warnings=warnings,
                  limitation='Comprueba estructura e integridad; no verdad semántica ni estado en vivo.')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if errors else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('check')
    sub.add_parser('catalog')
    cap = sub.add_parser('capture')
    cap.add_argument('path')
    cap.add_argument('--title')
    integ = sub.add_parser('integrate', help='marca una fuente como integrada o referencia')
    integ.add_argument('id')
    integ.add_argument('--pages', nargs='*', default=[])
    integ.add_argument('--scope')
    integ.add_argument('--quitar-pagina', nargs='*', dest='quitar_pagina',
                       help='quita una página mal registrada de esta fuente (corrige un SID tecleado por error)')
    integ.add_argument('--status', choices=['integrated', 'reference'], default='integrated')
    integ.add_argument('--motivo')
    args = parser.parse_args()
    if args.command == 'check':
        return check(args)
    if args.command == 'catalog':
        catalog(load())
        print('Catálogo actualizado.')
    elif args.command == 'integrate':
        integrate(args)
    else:
        capture(args)
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (ValueError, OSError, KeyError) as error:
        print(f'Error: {error}', file=sys.stderr)
        sys.exit(1)
