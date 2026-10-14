#!/usr/bin/env python3
"""Pantalla de un video: lo baja a 1080p, saca un fotograma cada N s y lo reparte en tramos para agentes.

Un video se analiza con pantalla y transcripcion completas: en tutoriales y demos lo que decide
suele estar en la pantalla, no en lo que se dice. transcript.py da la transcripcion; este script
da la pantalla.

  python3 .claude/skills/video-scout/scripts/pantalla.py "<URL>" --out .claude/tmp/vs [--cada 10] [--tramo 600]

Deja en --out: v.mp4, frames/f_NNN.jpg (f_N muestra el segundo (N-1)*cada + cada/2) y tramos.txt
(que fotogramas y que lineas de t.txt le tocan a cada agente). Un agente por tramo abre TODOS sus
fotogramas con la transcripcion de su tramo y devuelve texto; el agente principal no carga las imagenes.

Requiere yt-dlp y ffmpeg. En macOS: `brew install yt-dlp ffmpeg`.
Compatible con el python3 que trae macOS (3.9).
"""
import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path


def bajar(url, out):
    """yt-dlp del PATH, si no `python3 -m yt_dlp`, si no uvx. Si YouTube pide resolver JavaScript, reintenta con node."""
    formato = ["-f", "299/137/bestvideo[height<=1080]", "-o", str(out / "v.%(ext)s"), url]
    candidatos = []
    if shutil.which("yt-dlp"):
        candidatos.append([shutil.which("yt-dlp")])
    if subprocess.run([sys.executable, "-c", "import yt_dlp"], capture_output=True).returncode == 0:
        candidatos.append([sys.executable, "-m", "yt_dlp"])
    if shutil.which("uvx"):
        candidatos.append([shutil.which("uvx"), "--from", "yt-dlp[default]", "yt-dlp"])
    for base in candidatos:
        extras = [[]] + ([["--js-runtimes", "node"]] if shutil.which("node") else [])
        for extra in extras:
            r = subprocess.run(base + extra + formato)
            if r.returncode == 0 and (out / "v.mp4").exists():
                return True
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("--out", default=".claude/tmp/vs")
    ap.add_argument("--cada", type=int, default=10, help="segundos entre fotogramas")
    ap.add_argument("--tramo", type=int, default=600, help="segundos por agente")
    a = ap.parse_args()
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        sys.exit("Falta ffmpeg (brew install ffmpeg): la pantalla queda not_available y el analisis no es completo")
    out = Path(a.out)
    (out / "frames").mkdir(parents=True, exist_ok=True)
    video = out / "v.mp4"
    if not video.exists() and not bajar(a.url, out):
        sys.exit("No se pudo bajar el video (brew install yt-dlp, o brew upgrade yt-dlp): "
                 "la pantalla queda not_available y el analisis no es completo")
    for f in (out / "frames").glob("f_*.jpg"):
        f.unlink()
    subprocess.run([ffmpeg, "-loglevel", "error", "-i", str(video), "-vf", "fps=1/%d" % a.cada, "-q:v", "3",
                    str(out / "frames/f_%03d.jpg")], check=True)
    frames = sorted((out / "frames").glob("f_*.jpg"))
    lineas = (out / "t.txt").read_text().splitlines() if (out / "t.txt").exists() else []

    def seg(n):
        return (n - 1) * a.cada + a.cada // 2

    def mmss(s):
        return "%02d:%02d" % (s // 60, s % 60)

    txt = []
    por_tramo = max(1, a.tramo // a.cada)
    for i in range(0, len(frames), por_tramo):
        grupo = frames[i:i + por_tramo]
        n0, n1 = i + 1, i + len(grupo)
        desde, hasta = seg(n0) - a.cada // 2, seg(n1) + a.cada // 2
        nums = []
        for ln, linea in enumerate(lineas):
            m = re.match(r"\[(\d+):(\d+)\]", linea)
            if m and desde - 15 <= int(m.group(1)) * 60 + int(m.group(2)) < hasta:
                nums.append(ln)
        rango = "lineas %d-%d de t.txt" % (nums[0] + 1, nums[-1] + 1) if nums else "sin t.txt"
        txt.append("Tramo %d: %s a %s (%s a %s), %s" % (len(txt) + 1, grupo[0].name, grupo[-1].name,
                                                       mmss(seg(n0)), mmss(seg(n1)), rango))
    (out / "tramos.txt").write_text("\n".join(txt) + "\n")
    print("%d fotogramas cada %d s en %s" % (len(frames), a.cada, out / "frames"))
    print("\n".join(txt))


if __name__ == "__main__":
    main()
