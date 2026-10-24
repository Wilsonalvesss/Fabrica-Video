"""Agentes 8 (Agendamento) e 9 (API do YouTube).

O envio usa a YouTube Data API v3 oficial. O vídeo sobe como privado com
publishAt, então o próprio YouTube publica no horário agendado.
"""
import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from . import config, estado

ESCOPOS = ["https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/youtube"]


def proximo_horario(ignorar: str = "") -> datetime:
    """Primeiro horário de HORARIOS, a partir de 1 hora de agora, que nenhum vídeo válido ocupa."""
    fuso = ZoneInfo(config.FUSO)
    # vídeos com erro ou refeitos não seguram horário
    ocupados = {j.get("publicar_em") for j in estado.todos()
                if j.get("publicar_em") and j["id"] != ignorar and j.get("status") in ("revisao", "aprovado", "publicado")}
    agora = datetime.now(fuso)
    dia = agora.date()
    for _ in range(365):
        for h in config.HORARIOS:
            hh, mm = map(int, h.split(":"))
            slot = datetime(dia.year, dia.month, dia.day, hh, mm, tzinfo=fuso)
            if slot > agora + timedelta(hours=1) and slot.isoformat() not in ocupados:
                return slot
        dia += timedelta(days=1)
    raise RuntimeError("nenhum horário livre no próximo ano")


def agendar(job: dict) -> None:
    with estado.Etapa(job, "agenda") as e:
        e.atualizar(0.5, "escolhendo o melhor horário")
        job["publicar_em"] = proximo_horario(job["id"]).isoformat()
        e.atualizar(1, f"publicação em {job['publicar_em'][:16].replace('T', ' ')}")


def _servico():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    cred = None
    if config.YOUTUBE_TOKEN.exists():
        cred = Credentials.from_authorized_user_file(str(config.YOUTUBE_TOKEN), ESCOPOS)
    if not cred or not cred.valid:
        if cred and cred.expired and cred.refresh_token:
            cred.refresh(Request())
        else:
            if not config.YOUTUBE_CLIENT_SECRET.exists():
                raise RuntimeError(f"falta {config.YOUTUBE_CLIENT_SECRET.name} (ver README, seção YouTube)")
            fluxo = InstalledAppFlow.from_client_secrets_file(str(config.YOUTUBE_CLIENT_SECRET), ESCOPOS)
            cred = fluxo.run_local_server(port=0)
        config.YOUTUBE_TOKEN.write_text(cred.to_json(), encoding="utf-8")
    return build("youtube", "v3", credentials=cred)


def _enviar(yt, arquivo, titulo, descricao, tags, quando: datetime, progresso):
    from googleapiclient.http import MediaFileUpload

    corpo = {
        "snippet": {"title": titulo[:100], "description": descricao[:5000], "tags": tags[:30],
                    "categoryId": config.YOUTUBE_CATEGORIA, "defaultLanguage": config.IDIOMA},
        "status": {"privacyStatus": "private", "selfDeclaredMadeForKids": False,
                   "publishAt": quando.astimezone(ZoneInfo("UTC")).strftime("%Y-%m-%dT%H:%M:%S.000Z")},
    }
    req = yt.videos().insert(part="snippet,status", body=corpo,
                             media_body=MediaFileUpload(str(arquivo), chunksize=8 << 20, resumable=True))
    resp = None
    while resp is None:
        status, resp = req.next_chunk()
        if status:
            progresso(status.progress())
    return resp["id"]


def publicar(job: dict) -> None:
    base = estado.pasta(job["id"])
    r = json.loads((base / "roteiro.json").read_text(encoding="utf-8"))
    quando = datetime.fromisoformat(job["publicar_em"])
    with estado.Etapa(job, "api") as e:
        yt = _servico()
        e.atualizar(0.02, "enviando via API oficial")
        partes = 1 + len(r["shorts"])
        short = job.get("formato") == "short"
        titulo = f"{r['titulo'][:90]} #shorts" if short else r["titulo"]
        vid = _enviar(yt, base / "video.mp4", titulo, r["descricao"], r["tags"], quando,
                      lambda p: e.atualizar(p / partes, f"enviando o vídeo ({int(p * 100)}%)"))
        from googleapiclient.http import MediaFileUpload

        if not short:  # o YouTube não usa thumbnail personalizada em Shorts
            yt.thumbnails().set(videoId=vid, media_body=MediaFileUpload(str(base / "thumb.jpg"))).execute()
        job["youtube_id"] = vid
        job["shorts_ids"] = []
        for n, s in enumerate(r["shorts"], 1):
            e.atualizar(n / partes, f"enviando o short {n}")
            desc = f"{s['titulo']}\n\nVídeo completo: https://youtu.be/{vid}\n#shorts"
            sid = _enviar(yt, base / "shorts" / f"S{n:02d}.mp4", f"{s['titulo']} #shorts", desc,
                          r["tags"], quando + timedelta(hours=2 * n), lambda p: None)
            job["shorts_ids"].append(sid)
        job["status"] = "publicado"
        e.atualizar(1, f"agendado: youtu.be/{vid}")
