"""Agentes 3 a 7: Narração, Cenas, Montagem, Shorts e Thumbnail.

Voz, cenas, legenda e montagem são feitas pelo MoneyPrinterTurbo (motor.py).
O vídeo longo sai em 1920x1080 e os shorts em 1080x1920. A thumbnail é nossa.
"""
import json
import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from . import estado, motor

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


# ---------- 3, 4 e 5 · Narração, Cenas e Montagem (MoneyPrinterTurbo)

# Faixas de progresso de uma tarefa do motor (app/services/task.py do MoneyPrinterTurbo):
# 10-40 voz e legenda, 40-50 download das cenas, 50-100 montagem do vídeo.
FAIXAS = [("narracao", 0, 40, "gerando a voz bloco a bloco"),
          ("cenas", 40, 50, "baixando as cenas do Pexels"),
          ("montagem", 50, 100, "montando o vídeo e queimando a legenda")]


class _Faixas:
    """Traduz o progresso 0-100 do motor nas três mesas do escritório."""

    def __init__(self, job):
        self.job, self.abertas = job, {}

    def __call__(self, p: float):
        for chave, ini, fim, msg in FAIXAS:
            if p >= ini and chave not in self.abertas:
                self.abertas[chave] = estado.Etapa(self.job, chave).__enter__()
            e = self.abertas.get(chave)
            if e and self.job["etapas"][chave]["estado"] == "trabalhando":
                if p >= fim:
                    e.__exit__(None, None, None)
                else:
                    e.atualizar((p - ini) / (fim - ini), msg)

    def falhou(self, erro: Exception):
        for chave, e in self.abertas.items():
            if self.job["etapas"][chave]["estado"] == "trabalhando":
                e.__exit__(type(erro), erro, None)
                return
        e = estado.Etapa(self.job, "narracao").__enter__()
        e.__exit__(type(erro), erro, None)


def video_longo(job: dict, r: dict) -> None:
    base = estado.pasta(job["id"])
    faixas = _Faixas(job)
    faixas(0)
    try:
        tid = motor.criar_video(r["titulo"], "\n\n".join(b["texto"] for b in r["blocos"]),
                                [b["busca"] for b in r["blocos"]], "16:9")
        job["motor_tarefa"] = tid
        estado.registrar(job, f"motor recebeu a tarefa {tid}")
        t = motor.acompanhar(tid, faixas)
        motor.baixar(t["videos"][0], base / "video.mp4")
        if t.get("audio_file"):
            motor.baixar(t["audio_file"], base / "narracao.mp3")
        if t.get("subtitle_path"):
            motor.baixar(t["subtitle_path"], base / "legendas.srt")
        faixas(100)
    except Exception as erro:
        faixas.falhou(erro)
        raise
    total = duracao(base / "video.mp4")
    job["duracao"] = f"{int(total // 60)}:{int(total % 60):02d}"
    job["cenas"] = len(r["blocos"])
    job["audio_duracao"] = float(t.get("audio_duration") or 0)
    estado.salvar(job)


# ---------- 6 · Shorts (MoneyPrinterTurbo em 9:16)

def shorts(job: dict, r: dict) -> None:
    pasta = estado.pasta(job["id"]) / "shorts"
    pasta.mkdir(exist_ok=True)
    total = max(1, len(r["shorts"]))
    with estado.Etapa(job, "shorts") as e:
        for n, s in enumerate(r["shorts"], 1):
            blocos = r["blocos"][s["de"]: s["ate"] + 1]
            tid = motor.criar_video(s["titulo"], " ".join(b["texto"] for b in blocos),
                                    [b["busca"] for b in blocos], "9:16")
            t = motor.acompanhar(tid, lambda p: e.atualizar(
                ((n - 1) + p / 100) / total, f"cortando o short {n}: {s['titulo']}"))
            motor.baixar(t["videos"][0], pasta / f"S{n:02d}.mp4")


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
    narr = base / "narracao.mp3"
    audio = duracao(narr) if narr.exists() else job.get("audio_duracao", 0)
    palavras = sum(len(b["texto"].split()) for b in r["blocos"])
    # Pronúncia: ritmo fora de 1,5 a 4,5 palavras/s indica voz cortada ou embolada
    ritmo = palavras / audio if audio else 0
    video = duracao(base / "video.mp4")
    shorts_ok = all((base / "shorts" / f"S{n:02d}.mp4").exists() for n in range(1, len(r["shorts"]) + 1))
    srt = base / "legendas.srt"
    return {"Áudio": audio > 1, "Pronúncia": 1.5 <= ritmo <= 4.5,
            "Ordem": audio > 0 and video >= audio - 1 and shorts_ok,
            "Legenda": srt.exists() and srt.stat().st_size > 0}
