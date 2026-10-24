"""Configuração lida do arquivo .env na raiz do projeto."""
import os
from pathlib import Path

from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parent.parent
load_dotenv(RAIZ / ".env")


def _env(nome, padrao=""):
    return os.getenv(nome, padrao).strip()


# Pastas
VIDEOS_DIR = Path(_env("VIDEOS_DIR", str(RAIZ / "videos")))
MUSICA_DIR = RAIZ / "assets" / "musica"
WEB_DIR = RAIZ / "web"

# Canal
NICHO = _env("NICHO", "inteligência artificial na prática")
IDIOMA = _env("IDIOMA", "pt-BR")
DURACAO_ALVO_MIN = int(_env("DURACAO_ALVO_MIN", "8"))

# Roteiro (Claude). Sem chave, o Claude Code escreve o roteiro (ver CLAUDE.md).
ANTHROPIC_API_KEY = _env("ANTHROPIC_API_KEY")
CLAUDE_MODEL = _env("CLAUDE_MODEL", "claude-sonnet-5-5")

# Voz: "edge" (grátis) ou "elevenlabs"
VOZ_PROVEDOR = _env("VOZ_PROVEDOR", "edge")
EDGE_VOZ = _env("EDGE_VOZ", "pt-BR-AntonioNeural")
ELEVENLABS_API_KEY = _env("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = _env("ELEVENLABS_VOICE_ID")

# Cenas: banco de vídeos/fotos do Pexels (grátis)
PEXELS_API_KEY = _env("PEXELS_API_KEY")

# YouTube
YOUTUBE_CLIENT_SECRET = Path(_env("YOUTUBE_CLIENT_SECRET", str(RAIZ / "client_secret.json")))
YOUTUBE_TOKEN = RAIZ / "youtube_token.json"
YOUTUBE_CATEGORIA = _env("YOUTUBE_CATEGORIA", "28")  # Ciência e tecnologia
HORARIOS = [h.strip() for h in _env("HORARIOS", "18:00").split(",") if h.strip()]
FUSO = _env("FUSO", "America/Sao_Paulo")

VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
