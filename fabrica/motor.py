"""Ponte com o MoneyPrinterTurbo, o motor que faz voz, cenas, legenda e montagem.

O motor fica em motor/MoneyPrinterTurbo, preso a uma versão testada. `instalar()`
baixa o código e as dependências, e `gerar_config()` escreve o config.toml dele a
partir do nosso .env: roteiro pela assinatura do Claude (provider claude_code),
voz pela ElevenLabs e cenas pelo Pexels.
"""
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

import requests

from . import config

REPO = "https://github.com/harry0703/MoneyPrinterTurbo"
VERSAO = "82bb4a7"  # commit testado com a Fábrica
PASTA = config.MOTOR_DIR


# ---------- instalação

def _rodar(*cmd, cwd=None):
    print("  $", " ".join(map(str, cmd)))
    subprocess.run(list(map(str, cmd)), cwd=cwd, check=True)


def instalar() -> None:
    if not shutil.which("git"):
        raise SystemExit("Instale o Git primeiro: https://git-scm.com/downloads")
    if not (PASTA / ".git").exists():
        PASTA.parent.mkdir(parents=True, exist_ok=True)
        _rodar("git", "clone", REPO, PASTA)
    _rodar("git", "fetch", "--quiet", "origin", cwd=PASTA)
    _rodar("git", "checkout", "--quiet", VERSAO, cwd=PASTA)
    _rodar(sys.executable, "-m", "pip", "install", "-r", PASTA / "requirements.txt")
    gerar_config()
    print("\nMotor instalado. Agora rode: python -m fabrica iniciar")


def _toml(valor) -> str:
    if isinstance(valor, bool):
        return "true" if valor else "false"
    if isinstance(valor, (int, float)):
        return str(valor)
    if isinstance(valor, list):
        return "[" + ", ".join(_toml(v) for v in valor) + "]"
    return '"' + str(valor).replace("\\", "\\\\").replace('"', '\\"') + '"'


def gerar_config() -> None:
    """Copia o config.example.toml do motor e troca só as chaves que a Fábrica usa."""
    exemplo = PASTA / "config.example.toml"
    if not exemplo.exists():
        raise SystemExit("Motor não instalado. Rode: python -m fabrica instalar")
    valores = {
        "": {"listen_host": "127.0.0.1", "listen_port": config.MOTOR_PORTA, "log_level": "INFO"},
        "app": {
            "pexels_api_keys": [config.PEXELS_API_KEY] if config.PEXELS_API_KEY else [],
            "pixabay_api_keys": [config.PIXABAY_API_KEY] if config.PIXABAY_API_KEY else [],
            "llm_provider": "anthropic" if config.ANTHROPIC_API_KEY else "claude_code",
            "max_concurrent_tasks": 2,
        },
        "elevenlabs": {"api_key": config.ELEVENLABS_API_KEY},
    }
    if config.ANTHROPIC_API_KEY:
        valores["app"]["anthropic_api_key"] = config.ANTHROPIC_API_KEY
    secao, saida, feitos = "", [], set()
    for linha in exemplo.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\s*\[([^\]]+)\]\s*$", linha)
        if m:
            secao = m.group(1).strip()
        chave = re.match(r"^\s*#?\s*([a-z_]+)\s*=", linha)
        if chave and chave.group(1) in valores.get(secao, {}) and (secao, chave.group(1)) not in feitos:
            nome = chave.group(1)
            linha = f"{nome} = {_toml(valores[secao][nome])}"
            feitos.add((secao, nome))
        saida.append(linha)
    (PASTA / "config.toml").write_text("\n".join(saida) + "\n", encoding="utf-8")


# ---------- execução

def url(caminho: str = "") -> str:
    return f"http://127.0.0.1:{config.MOTOR_PORTA}{caminho}"


def no_ar() -> bool:
    try:
        requests.get(url("/docs"), timeout=2)
        return True
    except requests.RequestException:
        return False


def iniciar() -> subprocess.Popen:
    """Sobe a API do motor em segundo plano e espera ela responder."""
    gerar_config()
    log = open(config.RAIZ / "motor.log", "a", encoding="utf-8")
    proc = subprocess.Popen([sys.executable, "main.py"], cwd=PASTA, stdout=log, stderr=subprocess.STDOUT)
    for _ in range(90):
        if proc.poll() is not None:
            raise SystemExit("O motor não subiu. Veja o arquivo motor.log")
        if no_ar():
            return proc
        time.sleep(1)
    raise SystemExit("O motor demorou demais para subir. Veja o arquivo motor.log")


def voz() -> str:
    if config.ELEVENLABS_API_KEY and config.ELEVENLABS_VOICE_ID:
        return f"elevenlabs:{config.ELEVENLABS_VOICE_ID}:{config.ELEVENLABS_VOICE_NOME}"
    return config.EDGE_VOZ


def _pixabay(termos: list, prefixo: str, quantos: int) -> list:
    """Cenas genéricas (controle, estádio, torcida...) do Pixabay, cortadas em trechos de 5 s."""
    import random

    if not config.PIXABAY_API_KEY or quantos <= 0:
        return []
    destino = PASTA / "storage" / "local_videos"
    urls = []
    for termo in termos:
        try:
            hits = requests.get("https://pixabay.com/api/videos/", timeout=30,
                                params={"key": config.PIXABAY_API_KEY, "q": termo, "per_page": 5}).json().get("hits", [])
        except (requests.RequestException, ValueError):
            continue
        urls += [h["videos"]["medium"]["url"] for h in hits if h.get("videos", {}).get("medium", {}).get("url")]
    random.shuffle(urls)
    nomes = []
    for k, u in enumerate(urls[:quantos]):
        nome = f"{prefixo}_px{k:02d}.mp4"
        r = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", u, "-t", "5", "-an",
                            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", str(destino / nome)])
        if r.returncode == 0:
            nomes.append(nome)
    return nomes


def _steam(jogo: str, prefixo: str, segundos: float, termos: list = ()) -> list:
    """Baixa screenshots (e, se ligado, trechos de trailer) oficiais do jogo na loja da Steam."""
    import random

    busca = requests.get("https://store.steampowered.com/api/storesearch/",
                         params={"term": jogo, "l": "brazilian", "cc": "BR"}, timeout=30).json()
    itens = busca.get("items") or []
    if not itens:
        return []
    appid = str(itens[0]["id"])
    dados = requests.get("https://store.steampowered.com/api/appdetails",
                         params={"appids": appid, "l": "brazilian"}, timeout=30).json()
    info = (dados.get(appid) or {}).get("data") or {}
    fotos = [s["path_full"] for s in info.get("screenshots", []) if s.get("path_full")]
    filmes = []
    for m in info.get("movies", []):
        u = (m.get("mp4") or {}).get("max") or m.get("hls_h264") or m.get("dash_h264")
        if u:
            filmes.append(u)
    destino = PASTA / "storage" / "local_videos"
    destino.mkdir(parents=True, exist_ok=True)
    for velho in destino.glob(f"{prefixo}_*"):
        velho.unlink(missing_ok=True)
    precisa = int(segundos // 4) + 3
    random.shuffle(fotos)
    nomes = []
    if not fotos and not filmes:
        return []
    genericas = _pixabay(list(termos)[:4], prefixo, precisa // 3)  # 1/3 de cenas genéricas de games
    if config.USAR_TRAILERS and filmes:
        for k in range(precisa // 2):
            nome = f"{prefixo}_tr{k:02d}.mp4"
            r = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                                "-ss", f"{random.uniform(3, 40):.1f}", "-i", random.choice(filmes), "-t", "5",
                                "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", str(destino / nome)])
            if r.returncode == 0:
                nomes.append(nome)
    for k, foto in enumerate(fotos[: precisa - len(nomes) - len(genericas)]):
        nome = f"{prefixo}_ss{k:02d}.jpg"
        baixar(foto, destino / nome)
        nomes.append(nome)
    nomes += genericas
    random.shuffle(nomes)
    return nomes


def criar_video(assunto: str, texto: str, termos: list, formato: str, prefixo: str = "fabrica",
                jogo: str = "") -> str:
    params = {
        "video_subject": assunto,
        "video_script": texto,
        "video_terms": termos,
        "video_aspect": formato,  # "16:9" ou "9:16"
        "match_materials_to_script": True,
        "video_source": "pexels" if config.PEXELS_API_KEY else "pixabay",
        "video_clip_duration": 5,
        "video_language": config.IDIOMA,
        "voice_name": voz(),
        "bgm_type": "random",
        "bgm_volume": 0.15,
        "subtitle_enabled": True,
        "subtitle_position": "bottom",
        "font_name": "MicrosoftYaHeiBold.ttc",
        "font_size": 60 if formato == "16:9" else 70,
        "stroke_width": 2,
        "n_threads": 4,
    }
    segundos = len(texto.split()) / 2.3
    locais = []
    if clipes():  # gameplay seu em clipes/ tem prioridade
        locais = _cortar_clipes(prefixo, segundos)
    elif jogo and config.USAR_STEAM:
        try:
            locais = _steam(jogo, prefixo, segundos, termos)
        except (requests.RequestException, ValueError, KeyError):
            locais = []  # Steam fora do ar: segue com o banco de imagens
    if locais:
        params["video_source"] = "local"
        params["match_materials_to_script"] = False
        params["video_concat_mode"] = "sequential"
        params["video_materials"] = [{"provider": "local", "url": n, "duration": 5} for n in locais]
    r = requests.post(url("/api/v1/videos"), json=params, timeout=60)
    r.raise_for_status()
    return r.json()["data"]["task_id"]


def acompanhar(task_id: str, ao_progredir) -> dict:
    """Espera a tarefa terminar chamando ao_progredir(0-100) a cada consulta."""
    while True:
        r = requests.get(url(f"/api/v1/tasks/{task_id}"), timeout=30)
        r.raise_for_status()
        t = r.json()["data"]
        ao_progredir(float(t.get("progress") or 0))
        if t.get("state") == 1:  # TASK_STATE_COMPLETE
            return t
        if t.get("state") == -1:  # TASK_STATE_FAILED
            raise RuntimeError(f"o motor falhou: {t.get('error') or t.get('message') or 'veja motor.log'}")
        time.sleep(3)


def baixar(uri: str, destino: Path) -> None:
    tmp = destino.with_suffix(destino.suffix + ".baixando")
    with requests.get(url(uri) if uri.startswith("/") else uri, stream=True, timeout=600) as r:
        r.raise_for_status()
        with open(tmp, "wb") as f:
            for parte in r.iter_content(1 << 20):
                f.write(parte)
    for _ in range(20):  # no Windows o player do painel pode estar segurando o arquivo antigo
        try:
            tmp.replace(destino)
            return
        except PermissionError:
            time.sleep(3)
    raise RuntimeError(f"{destino.name} está aberto em outro programa; feche o vídeo e tente de novo")


# ---------- cenas com os seus próprios clipes (gameplay)

VIDEO_EXT = {".mp4", ".mov", ".mkv", ".webm", ".avi"}


def clipes() -> list:
    pasta = config.CLIPES_DIR
    return sorted(p for p in pasta.glob("**/*") if p.suffix.lower() in VIDEO_EXT) if pasta.exists() else []


def _cortar_clipes(prefixo: str, segundos: float) -> list:
    """Corta trechos de 5 s de pontos aleatórios dos seus clipes e põe na pasta do motor."""
    import json as _json
    import random

    destino = PASTA / "storage" / "local_videos"
    destino.mkdir(parents=True, exist_ok=True)
    for velho in destino.glob(f"{prefixo}_*.mp4"):
        velho.unlink(missing_ok=True)
    fontes = clipes()
    nomes = []
    for k in range(int(segundos // 4) + 3):
        fonte = random.choice(fontes)
        info = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(fonte)],
                              capture_output=True, text=True)
        dur = float(_json.loads(info.stdout or "{}").get("format", {}).get("duration", 0) or 0)
        inicio = random.uniform(0, max(0.0, dur - 6))
        nome = f"{prefixo}_{k:02d}.mp4"
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", f"{inicio:.2f}", "-i", str(fonte),
                        "-t", "5", "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", str(destino / nome)],
                       check=True)
        nomes.append(nome)
    return nomes
