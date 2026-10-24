"""Servidor do painel: http://localhost:8000"""
import threading

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import config, esteira, estado, motor

app = FastAPI(title="Fábrica")
app.mount("/midia", StaticFiles(directory=config.VIDEOS_DIR), name="midia")
_ocupada = threading.Lock()


def _rodar(func, *args):
    def alvo():
        with _ocupada:  # um vídeo por vez na esteira
            try:
                func(*args)
            except Exception as erro:
                vid = next((a for a in args if isinstance(a, str) and a.startswith("V")), "")
                if vid:
                    job = estado.ler(vid)
                    job["status"] = "erro"
                    estado.registrar(job, f"falhou: {erro}")
                raise
    threading.Thread(target=alvo, daemon=True).start()


@app.get("/")
def index():
    return FileResponse(config.WEB_DIR / "index.html")


@app.get("/api/estado")
def ver_estado():
    jobs = [esteira.resumo(j) for j in estado.todos()]
    return {"ocupada": _ocupada.locked(), "etapas": [{"id": k, "nome": n} for k, n in estado.ETAPAS], "videos": jobs}


class Pedido(BaseModel):
    texto: str = ""
    formato: str = ""


@app.post("/api/produzir")
def produzir(p: Pedido):
    if _ocupada.locked():
        raise HTTPException(409, "A esteira já está produzindo um vídeo.")
    if not motor.no_ar():
        raise HTTPException(503, "O motor está desligado. Feche e abra de novo com: python -m fabrica iniciar")
    job = estado.criar(p.texto.strip(), p.formato)
    _rodar(esteira.produzir, "", job["id"])
    return {"id": job["id"]}


@app.post("/api/videos/{vid}/aprovar")
def aprovar(vid: str):
    _rodar(esteira.aprovar, vid)
    return {"ok": True}


@app.post("/api/videos/{vid}/ajuste")
def ajuste(vid: str, p: Pedido):
    if not p.texto.strip():
        raise HTTPException(400, "Escreva o que deve mudar.")
    _rodar(esteira.ajustar, vid, p.texto.strip())
    return {"ok": True}


def rodar(porta: int = 8000):
    import uvicorn

    print(f"Painel da Fábrica em http://localhost:{porta}")
    uvicorn.run(app, host="127.0.0.1", port=porta, log_level="warning")
