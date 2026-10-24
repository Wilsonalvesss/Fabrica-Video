"""Estado de cada vídeo, guardado em videos/<id>/job.json.

O painel lê esse arquivo, então tudo que um agente faz passa por aqui.
"""
import json
import threading
import time
from pathlib import Path

from . import config

ETAPAS = [
    ("pauta", "Pauta"),
    ("roteiro", "Roteiro"),
    ("narracao", "Narração"),
    ("cenas", "Cenas"),
    ("montagem", "Montagem"),
    ("shorts", "Shorts"),
    ("thumb", "Thumbnail"),
    ("agenda", "Agendamento"),
    ("api", "API do YouTube"),
]

_trava = threading.Lock()


def pasta(vid: str) -> Path:
    return config.VIDEOS_DIR / vid


def novo_id() -> str:
    nums = [int(p.name[1:]) for p in config.VIDEOS_DIR.glob("V*") if p.name[1:].isdigit()]
    return f"V{(max(nums) + 1 if nums else 1):02d}"


def criar(tema: str) -> dict:
    vid = novo_id()
    pasta(vid).mkdir(parents=True)
    job = {
        "id": vid,
        "tema": tema,
        "status": "produzindo",  # produzindo | revisao | aprovado | publicado | ajuste | erro
        "criado": time.time(),
        "etapas": {k: {"estado": "fila", "progresso": 0, "msg": ""} for k, _ in ETAPAS},
        "log": [],
    }
    salvar(job)
    return job


def ler(vid: str) -> dict:
    return json.loads((pasta(vid) / "job.json").read_text(encoding="utf-8"))


def salvar(job: dict) -> None:
    with _trava:
        destino = pasta(job["id"]) / "job.json"
        tmp = destino.with_suffix(".tmp")
        tmp.write_text(json.dumps(job, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(destino)


def todos() -> list:
    jobs = []
    for p in sorted(config.VIDEOS_DIR.glob("V*/job.json"), reverse=True):
        try:
            jobs.append(json.loads(p.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError):
            pass
    return jobs


class Etapa:
    """Contexto que marca uma etapa como trabalhando/feita/erro no job."""

    def __init__(self, job: dict, chave: str):
        self.job, self.chave = job, chave

    def __enter__(self):
        self.atualizar(0, "começando")
        self.job["etapas"][self.chave]["estado"] = "trabalhando"
        salvar(self.job)
        return self

    def atualizar(self, progresso: float, msg: str = ""):
        e = self.job["etapas"][self.chave]
        e["progresso"] = round(max(0.0, min(1.0, progresso)), 3)
        if msg:
            e["msg"] = msg
        salvar(self.job)

    def __exit__(self, tipo, erro, tb):
        e = self.job["etapas"][self.chave]
        nome = dict(ETAPAS)[self.chave]
        if erro:
            e["estado"], e["msg"] = "erro", str(erro)[:300]
            self.job["status"] = "erro"
            registrar(self.job, f"{nome} falhou: {erro}")
        else:
            e["estado"], e["progresso"] = "feito", 1
            registrar(self.job, f"{nome} terminou")
        salvar(self.job)
        return False


def registrar(job: dict, texto: str) -> None:
    job["log"].insert(0, {"t": time.time(), "texto": texto})
    del job["log"][80:]
    salvar(job)
