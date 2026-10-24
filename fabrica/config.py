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
CLIPES_DIR = RAIZ / "clipes"  # coloque aqui gravações suas (gameplay etc.) para virar as cenas
WEB_DIR = RAIZ / "web"

# Canal
NICHO = _env("NICHO", "inteligência artificial na prática")
IDIOMA = _env("IDIOMA", "pt-BR")
DURACAO_ALVO_MIN = int(_env("DURACAO_ALVO_MIN", "8"))
# Formato padrão do botão Produzir vídeo: "short" (vertical) ou "longo" (16:9 + shorts)
FORMATO = _env("FORMATO", "short")
DURACAO_SHORT_S = int(_env("DURACAO_SHORT_S", "30"))

# Roteiro: pela assinatura do Claude (CLI `claude`) ou, se houver, pela API da Anthropic
ANTHROPIC_API_KEY = _env("ANTHROPIC_API_KEY")
CLAUDE_MODEL = _env("CLAUDE_MODEL")  # vazio = modelo padrão da sua conta
CLAUDE_CLI = _env("CLAUDE_CLI", "claude")

# Voz: ElevenLabs. Sem chave, cai na voz grátis da Microsoft (Edge)
ELEVENLABS_API_KEY = _env("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = _env("ELEVENLABS_VOICE_ID")
ELEVENLABS_VOICE_NOME = _env("ELEVENLABS_VOICE_NOME", "Narrador")
EDGE_VOZ = _env("EDGE_VOZ", "pt-BR-AntonioNeural-Male")

# Motor: MoneyPrinterTurbo
MOTOR_DIR = RAIZ / "motor" / "MoneyPrinterTurbo"
MOTOR_PORTA = int(_env("MOTOR_PORTA", "8080"))

# true = publica sozinho no YouTube sem passar pela aprovação
AUTO_PUBLICAR = _env("AUTO_PUBLICAR", "false").lower() in ("1", "true", "sim")

# Cenas: banco de vídeos do Pixabay ou do Pexels (os dois grátis)
PIXABAY_API_KEY = _env("PIXABAY_API_KEY")
PEXELS_API_KEY = _env("PEXELS_API_KEY")

# YouTube
YOUTUBE_CLIENT_SECRET = Path(_env("YOUTUBE_CLIENT_SECRET", str(RAIZ / "client_secret.json")))
YOUTUBE_TOKEN = RAIZ / "youtube_token.json"
YOUTUBE_CATEGORIA = _env("YOUTUBE_CATEGORIA", "28")  # Ciência e tecnologia
HORARIOS = [h.strip() for h in _env("HORARIOS", "18:00").split(",") if h.strip()]
FUSO = _env("FUSO", "America/Sao_Paulo")

VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
