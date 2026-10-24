"""A esteira: roda os agentes em ordem e deixa o vídeo na fila de aprovação.

Os agentes 1 a 8 produzem. O agente 9 (API do YouTube) roda depois que você
aprova no painel, ou na hora se AUTO_PUBLICAR=true no .env.
"""
import json

from . import config, estado, midia, roteiro, youtube


def produzir(tema: str = "", vid: str = "") -> dict:
    job = estado.ler(vid) if vid else estado.criar(tema)
    estado.registrar(job, f"{job['id']} entrou na esteira")
    try:
        if job["etapas"]["pauta"]["estado"] != "feito":
            roteiro.pauta(job)
        r = roteiro.roteiro(job)
        midia.video_longo(job, r)
        midia.shorts(job, r)
        midia.thumbnail(job, r)
        youtube.agendar(job)
    except Exception:
        return job  # o erro já ficou registrado no job pela etapa que falhou
    if config.AUTO_PUBLICAR:
        estado.registrar(job, f"{job['id']} pronto: publicando sem aprovação (AUTO_PUBLICAR)")
        return aprovar(job["id"])
    job["status"] = "revisao"
    estado.registrar(job, f"{job['id']} foi pra fila de aprovação")
    return job


def aprovar(vid: str) -> dict:
    job = estado.ler(vid)
    job["status"] = "aprovado"
    estado.registrar(job, f"{vid} aprovado")
    try:
        youtube.publicar(job)
    except Exception:
        pass
    return job


def ajustar(vid: str, pedido: str) -> dict:
    """Refaz o roteiro com o pedido e roda a esteira de novo a partir dele."""
    job = estado.ler(vid)
    job["status"] = "produzindo"
    job["ajustes"] = job.get("ajustes", []) + [pedido]
    for k, _ in estado.ETAPAS[1:]:
        job["etapas"][k] = {"estado": "fila", "progresso": 0, "msg": ""}
    estado.registrar(job, f"ajuste pedido: {pedido}")
    base = estado.pasta(vid)
    for arq in [*(base / "shorts").glob("*"), base / "video.mp4", base / "narracao.mp3", base / "legendas.srt"]:
        arq.unlink(missing_ok=True)
    try:
        roteiro.roteiro(job, ajuste=pedido)
    except Exception:
        return job  # o erro ficou registrado na mesa do Roteiro
    return produzir(vid=vid)


def resumo(job: dict) -> dict:
    """Formato que o painel usa nos cards de revisão."""
    base = estado.pasta(job["id"])
    r = {}
    if (base / "roteiro.json").exists():
        r = json.loads((base / "roteiro.json").read_text(encoding="utf-8"))
    return {
        **{k: job.get(k) for k in ("id", "status", "tema", "titulo", "duracao", "publicar_em",
                                   "youtube_id", "checks", "etapas", "log")},
        "blocos": len(r.get("blocos", [])),
        "cenas": job.get("cenas", 0),
        "thumb": r.get("thumb", {}),
        "shorts": [{"titulo": s["titulo"], "arquivo": f"S{n:02d}.mp4"} for n, s in enumerate(r.get("shorts", []), 1)],
        "roteiro": [b["texto"] for b in r.get("blocos", [])],
    }
