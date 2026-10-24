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


def criar_video(assunto: str, texto: str, termos: list, formato: str) -> str:
    params = {
        "video_subject": assunto,
        "video_script": texto,
        "video_terms": termos,
        "video_aspect": formato,  # "16:9" ou "9:16"
        "match_materials_to_script": True,
        "video_source": "pexels",
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
    with requests.get(url(uri) if uri.startswith("/") else uri, stream=True, timeout=600) as r:
        r.raise_for_status()
        with open(destino, "wb") as f:
            for parte in r.iter_content(1 << 20):
                f.write(parte)
