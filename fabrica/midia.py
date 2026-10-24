"""Agentes 3 a 7: Narração, Cenas, Montagem, Shorts e Thumbnail.

Tudo roda com ffmpeg. O vídeo longo sai em 1920x1080 e os shorts em 1080x1920.
"""
import asyncio
import json
import random
import shutil
import subprocess
import textwrap
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFont

from . import config, estado

AMARELO = (255, 210, 63)
TINTA = (38, 41, 74)


# ---------- utilidades

def ffmpeg(*args: str) -> None:
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *args]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg falhou: {r.stderr.strip()[-400:]}")


def duracao(arquivo: Path) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(arquivo)],
        capture_output=True, text=True, check=True)
    return float(json.loads(r.stdout)["format"]["duration"])


def fonte(tamanho: int, negrito: bool = True) -> ImageFont.FreeTypeFont:
    nome = "DejaVu Sans:bold" if negrito else "DejaVu Sans"
    caminho = ""
    if shutil.which("fc-match"):
        caminho = subprocess.run(["fc-match", "-f", "%{file}", nome], capture_output=True, text=True).stdout
    for c in (caminho, "C:/Windows/Fonts/arialbd.ttf", "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"):
        if c and Path(c).exists():
            return ImageFont.truetype(c, tamanho)
    return ImageFont.load_default(tamanho)


def _srt_tempo(s: float) -> str:
    ms = int(round(s * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    seg, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{seg:02d},{ms:03d}"


def _legendas(texto: str, inicio: float, dur: float, palavras_por_linha: int = 7):
    """Divide a fala em pedaços e distribui o tempo pelo número de palavras."""
    palavras = texto.split()
    pedacos = [palavras[i:i + palavras_por_linha] for i in range(0, len(palavras), palavras_por_linha)]
    t = inicio
    for p in pedacos:
        d = dur * len(p) / max(1, len(palavras))
        yield t, t + d, " ".join(p)
        t += d


def _escrever_srt(itens, destino: Path) -> None:
    linhas = []
    for i, (a, b, txt) in enumerate(itens, 1):
        linhas += [str(i), f"{_srt_tempo(a)} --> {_srt_tempo(b)}", txt, ""]
    destino.write_text("\n".join(linhas), encoding="utf-8")


def _caminho_filtro(p: Path) -> str:
    # o filtro subtitles do ffmpeg precisa de ":" e "\" escapados (importante no Windows)
    return str(p.resolve()).replace("\\", "/").replace(":", r"\:")


# ---------- 3 · Narração

async def _edge(texto: str, destino: Path) -> None:
    import edge_tts

    await edge_tts.Communicate(texto, config.EDGE_VOZ).save(str(destino))


def _elevenlabs(texto: str, destino: Path) -> None:
    r = requests.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{config.ELEVENLABS_VOICE_ID}",
        headers={"xi-api-key": config.ELEVENLABS_API_KEY},
        json={"text": texto, "model_id": "eleven_multilingual_v2"},
        timeout=120)
    r.raise_for_status()
    destino.write_bytes(r.content)


def narracao(job: dict, r: dict) -> None:
    pasta = estado.pasta(job["id"]) / "audio"
    pasta.mkdir(exist_ok=True)
    with estado.Etapa(job, "narracao") as e:
        for i, b in enumerate(r["blocos"]):
            e.atualizar(i / len(r["blocos"]), f"gerando a voz bloco a bloco ({i + 1}/{len(r['blocos'])})")
            destino = pasta / f"{i:03d}.mp3"
            if config.VOZ_PROVEDOR == "elevenlabs" and config.ELEVENLABS_API_KEY:
                _elevenlabs(b["texto"], destino)
            else:
                asyncio.run(_edge(b["texto"], destino))


# ---------- 4 · Cenas

def _pexels(caminho: str, params: dict) -> dict:
    r = requests.get(f"https://api.pexels.com/{caminho}", params=params,
                     headers={"Authorization": config.PEXELS_API_KEY}, timeout=30)
    r.raise_for_status()
    return r.json()


def _baixar(url: str, destino: Path) -> None:
    with requests.get(url, stream=True, timeout=120) as r:
        r.raise_for_status()
        with open(destino, "wb") as f:
            for parte in r.iter_content(1 << 20):
                f.write(parte)


def _cartao(texto: str, destino: Path) -> None:
    """Cena reserva quando não há Pexels: cartão com a frase do bloco."""
    img = Image.new("RGB", (1920, 1080), (21, 26, 61))
    d = ImageDraw.Draw(img)
    f = fonte(64)
    linhas = textwrap.wrap(texto, 38)[:5]
    y = 540 - len(linhas) * 45
    for ln in linhas:
        d.text((960, y), ln, font=f, fill=(232, 234, 255), anchor="mt")
        y += 90
    img.save(destino)


def cenas(job: dict, r: dict) -> None:
    pasta = estado.pasta(job["id"]) / "cenas"
    pasta.mkdir(exist_ok=True)
    usados = set()
    with estado.Etapa(job, "cenas") as e:
        for i, b in enumerate(r["blocos"]):
            e.atualizar(i / len(r["blocos"]), f"buscando cena {i + 1}: {b.get('busca', '')}")
            if list(pasta.glob(f"{i:03d}.*")):
                continue
            if config.PEXELS_API_KEY and b.get("busca"):
                try:
                    vids = _pexels("videos/search", {"query": b["busca"], "orientation": "landscape", "per_page": 8})
                    for v in vids.get("videos", []):
                        if v["id"] in usados:
                            continue
                        arquivos = [a for a in v["video_files"] if a.get("width") and a["width"] >= 1280
                                    and a.get("file_type") == "video/mp4"]
                        if arquivos:
                            melhor = min(arquivos, key=lambda a: abs(a["width"] - 1920))
                            _baixar(melhor["link"], pasta / f"{i:03d}.mp4")
                            usados.add(v["id"])
                            break
                    else:
                        fotos = _pexels("v1/search", {"query": b["busca"], "orientation": "landscape", "per_page": 8})
                        livres = [p for p in fotos.get("photos", []) if p["id"] not in usados]
                        if livres:
                            _baixar(livres[0]["src"]["landscape"], pasta / f"{i:03d}.jpg")
                            usados.add(livres[0]["id"])
                except requests.RequestException as erro:
                    estado.registrar(job, f"Pexels falhou no bloco {i + 1}: {erro}")
            if not list(pasta.glob(f"{i:03d}.*")):
                _cartao(b["texto"], pasta / f"{i:03d}.png")


# ---------- 5 · Montagem

VF_LONGO = "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,fps=30,format=yuv420p"


def montagem(job: dict, r: dict) -> None:
    base = estado.pasta(job["id"])
    segs = base / "segmentos"
    segs.mkdir(exist_ok=True)
    with estado.Etapa(job, "montagem") as e:
        itens_srt, t, lista = [], 0.0, []
        for i, b in enumerate(r["blocos"]):
            e.atualizar(i / len(r["blocos"]) * 0.8, f"montando o bloco {i + 1}")
            audio = base / "audio" / f"{i:03d}.mp3"
            cena = next((base / "cenas").glob(f"{i:03d}.*"))
            dur = duracao(audio) + 0.25
            saida = segs / f"{i:03d}.mp4"
            entrada = ["-stream_loop", "-1", "-i", str(cena)] if cena.suffix == ".mp4" else ["-loop", "1", "-i", str(cena)]
            ffmpeg(*entrada, "-i", str(audio), "-t", f"{dur:.3f}", "-map", "0:v", "-map", "1:a",
                   "-vf", VF_LONGO, "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
                   "-c:a", "aac", "-ar", "44100", "-ac", "2", "-af", "apad", str(saida))
            real = duracao(saida)
            itens_srt += list(_legendas(b["texto"], t, real - 0.25))
            t += real
            lista.append(f"file '{saida.resolve().as_posix()}'")
        (base / "lista.txt").write_text("\n".join(lista), encoding="utf-8")
        _escrever_srt(itens_srt, base / "legendas.srt")

        e.atualizar(0.85, "juntando blocos e queimando legenda")
        bruto = base / "bruto.mp4"
        ffmpeg("-f", "concat", "-safe", "0", "-i", str(base / "lista.txt"), "-c", "copy", str(bruto))
        estilo = "FontName=DejaVu Sans,FontSize=20,Bold=1,Outline=2,Shadow=0,MarginV=40"
        vf = f"subtitles='{_caminho_filtro(base / 'legendas.srt')}':force_style='{estilo}'"
        musicas = list(config.MUSICA_DIR.glob("*.mp3"))
        if musicas:
            e.atualizar(0.9, "colocando trilha de fundo")
            ffmpeg("-i", str(bruto), "-stream_loop", "-1", "-i", str(random.choice(musicas)),
                   "-filter_complex", "[1:a]volume=0.10[m];[0:a][m]amix=inputs=2:duration=first[a]",
                   "-map", "0:v", "-map", "[a]", "-vf", vf, "-c:v", "libx264", "-preset", "veryfast",
                   "-crf", "21", "-c:a", "aac", "-shortest", str(base / "video.mp4"))
        else:
            ffmpeg("-i", str(bruto), "-vf", vf, "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
                   "-c:a", "copy", str(base / "video.mp4"))
        bruto.unlink(missing_ok=True)
        total = duracao(base / "video.mp4")
        job["duracao"] = f"{int(total // 60)}:{int(total % 60):02d}"
        job["cenas"] = len(r["blocos"])


# ---------- 6 · Shorts

def shorts(job: dict, r: dict) -> None:
    base = estado.pasta(job["id"])
    pasta = base / "shorts"
    pasta.mkdir(exist_ok=True)
    with estado.Etapa(job, "shorts") as e:
        for n, s in enumerate(r["shorts"], 1):
            e.atualizar((n - 1) / max(1, len(r["shorts"])), f"cortando o short {n}: {s['titulo']}")
            lista, itens, t = [], [], 0.0
            for i in range(s["de"], s["ate"] + 1):
                seg = base / "segmentos" / f"{i:03d}.mp4"
                lista.append(f"file '{seg.resolve().as_posix()}'")
                d = duracao(seg)
                itens += list(_legendas(r["blocos"][i]["texto"], t, d - 0.25, palavras_por_linha=4))
                t += d
            (pasta / f"S{n:02d}.txt").write_text("\n".join(lista), encoding="utf-8")
            _escrever_srt([i for i in itens if i[0] < 59], pasta / f"S{n:02d}.srt")
            (pasta / f"S{n:02d}_titulo.txt").write_text("\n".join(textwrap.wrap(s["titulo"].upper(), 18)), encoding="utf-8")
            estilo = "FontName=DejaVu Sans,FontSize=16,Bold=1,Outline=2,Shadow=0,MarginV=90"
            vf = ("scale=-2:1920,crop=1080:1920,"
                  f"subtitles='{_caminho_filtro(pasta / f'S{n:02d}.srt')}':force_style='{estilo}'")
            fonte_tit = getattr(fonte(10), "path", None)
            if isinstance(fonte_tit, str) and Path(fonte_tit).exists():
                tit = _caminho_filtro(pasta / f"S{n:02d}_titulo.txt")
                vf += (f",drawtext=fontfile='{_caminho_filtro(Path(fonte_tit))}':textfile='{tit}':"
                       "fontsize=72:fontcolor=white:borderw=6:bordercolor=0x26294a:"
                       "box=1:boxcolor=0xffd23f@1:boxborderw=24:line_spacing=10:x=(w-text_w)/2:y=220")
            ffmpeg("-f", "concat", "-safe", "0", "-i", str(pasta / f"S{n:02d}.txt"), "-t", "59",
                   "-vf", vf, "-c:v", "libx264", "-preset", "veryfast", "-crf", "22", "-c:a", "aac",
                   str(pasta / f"S{n:02d}.mp4"))


# ---------- 7 · Thumbnail

def _robo(d: ImageDraw.ImageDraw, x: int, y: int, s: int) -> None:
    d.rectangle([x, y, x + s, y + int(s * .82)], fill=AMARELO, outline=TINTA, width=max(4, s // 14))
    o = s // 6
    d.rectangle([x + o, y + s // 4, x + o + s // 6, y + s // 4 + s // 6], fill=TINTA)
    d.rectangle([x + s - o - s // 6, y + s // 4, x + s - o, y + s // 4 + s // 6], fill=TINTA)
    for k in range(3):  # vapor do café, como no mascote
        d.line([x + s // 4 + k * s // 4, y - 40, x + s // 4 + k * s // 4, y - 10], fill=TINTA, width=6)


def thumbnail(job: dict, r: dict) -> None:
    base = estado.pasta(job["id"])
    with estado.Etapa(job, "thumb") as e:
        e.atualizar(0.2, "pegando o quadro mais forte")
        quadro = base / "quadro.jpg"
        meio = duracao(base / "video.mp4") * 0.3
        ffmpeg("-ss", f"{meio:.2f}", "-i", str(base / "video.mp4"), "-frames:v", "1", str(quadro))

        e.atualizar(0.6, "desenhando a thumbnail")
        img = Image.new("RGB", (1280, 720), AMARELO)
        foto = Image.open(quadro).convert("RGB").resize((560, 315))
        moldura = Image.new("RGB", (576, 331), TINTA)
        moldura.paste(foto, (8, 8))
        img.paste(moldura.rotate(-3, expand=True, fillcolor=AMARELO), (660, 40))
        d = ImageDraw.Draw(img)
        d.text((56, 60), r["thumb"]["linha1"].upper(), font=fonte(78), fill=TINTA)
        linha2, tam = r["thumb"]["linha2"].upper(), 150
        while tam > 60 and d.textlength(linha2, font=fonte(tam)) > 600:  # não invade o print
            tam -= 6
        d.text((56, 170), linha2, font=fonte(tam), fill="white", stroke_width=10, stroke_fill=TINTA)
        _robo(d, 1020, 470, 170)
        d.text((60, 650), f"LONGO · {job['id']}", font=fonte(30), fill=TINTA)
        img.save(base / "thumb.jpg", quality=92)

        e.atualizar(0.9, "conferindo o vídeo")
        job["checks"] = checagens(job, r)


def checagens(job: dict, r: dict) -> dict:
    """Os 4 selos do card de revisão: Áudio, Pronúncia, Ordem e Legenda."""
    base = estado.pasta(job["id"])
    audios = [base / "audio" / f"{i:03d}.mp3" for i in range(len(r["blocos"]))]
    audio_ok = all(a.exists() and duracao(a) > 0.5 for a in audios)
    # Pronúncia: ritmo de fala fora de 1,5 a 4,5 palavras/s indica voz cortada ou embolada
    ritmo_ok = audio_ok and all(
        1.5 <= len(b["texto"].split()) / duracao(a) <= 4.5 for b, a in zip(r["blocos"], audios))
    segs = sorted((base / "segmentos").glob("*.mp4"))
    ordem_ok = [s.stem for s in segs] == [f"{i:03d}" for i in range(len(r["blocos"]))]
    srt = base / "legendas.srt"
    legenda_ok = srt.exists() and srt.stat().st_size > 0
    return {"Áudio": audio_ok, "Pronúncia": ritmo_ok, "Ordem": ordem_ok, "Legenda": legenda_ok}
