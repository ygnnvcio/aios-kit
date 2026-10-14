#!/usr/bin/env python3
"""Transcripcion de YouTube en bloques [mm:ss] de 15 s.

Uso: python3 transcript.py <URL> [--out DIR] [--block SEG]
Escribe DIR/meta.txt (titulo, canal) y DIR/t.txt. Sale con codigo 2 si el video
no tiene subtitulos en su idioma original (dato not_available, no se inventa) y
con 3 si no encuentra yt-dlp.

Requiere yt-dlp. En macOS: `brew install yt-dlp`. Busca, en orden: el comando
`yt-dlp` del PATH, `python3 -m yt_dlp` y `uvx yt-dlp`. Usa player_client=android:
la version web no devuelve subtitulos sin un token extra (ver SKILL.md).
Compatible con el python3 que trae macOS (3.9).
"""
import argparse
import json
import shutil
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path


def comando_ytdlp():
    if shutil.which("yt-dlp"):
        return [shutil.which("yt-dlp")]
    for py in (sys.executable, "python3"):
        if subprocess.run([py, "-c", "import yt_dlp"], capture_output=True).returncode == 0:
            return [py, "-m", "yt_dlp"]
    if shutil.which("uvx"):
        return [shutil.which("uvx"), "yt-dlp"]
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("--out", default=".")
    ap.add_argument("--block", type=int, default=15)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    try:
        q = urllib.parse.quote(a.url, safe="")
        d = json.load(urllib.request.urlopen("https://www.youtube.com/oembed?url=%s&format=json" % q, timeout=15))
        meta = "%s | %s\n" % (d.get("title"), d.get("author_name"))
    except Exception as e:
        meta = "not_available: oembed (%s)\n" % e

    base = comando_ytdlp()
    if not base:
        print("error: falta yt-dlp (brew install yt-dlp)", file=sys.stderr)
        sys.exit(3)
    base = base + ["--skip-download", "--extractor-args", "youtube:player_client=android"]
    subprocess.run(base + ["--write-auto-sub", "--sub-lang", "en-orig,es-orig", "--sub-format", "json3",
                           "-o", str(out / "vid"), a.url], capture_output=True, text=True)
    files = sorted(out.glob("vid.*-orig.json3"))
    if not files:
        (out / "meta.txt").write_text(meta + "captions: not_available (sin track -orig)\n")
        print("not_available: sin subtitulos -orig. Prueba --list-subs o Whisper local (ver SKILL.md)", file=sys.stderr)
        sys.exit(2)

    with open(files[0]) as fh:
        ev = json.load(fh)["events"]
    blocks, cur, buf = [], -1, ""
    step = a.block * 1000
    for e in ev:
        t = "".join(s.get("utf8", "") for s in e.get("segs", []))
        if not t.strip():
            continue
        b = e["tStartMs"] // step
        if b != cur:
            if buf:
                blocks.append(buf)
            s = b * a.block
            buf, cur = "[%02d:%02d] " % (s // 60, s % 60), b
        buf += t.replace("\n", " ") + " "
    blocks.append(buf)
    (out / "t.txt").write_text("\n".join(blocks))
    (out / "meta.txt").write_text(meta + "captions: %s, %d bloques\n" % (files[0].name, len(blocks)))
    print(meta + "%d bloques -> %s" % (len(blocks), out / "t.txt"))


if __name__ == "__main__":
    main()
