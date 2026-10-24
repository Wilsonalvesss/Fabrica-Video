"""Agentes 1 (Pauta) e 2 (Roteiro).

O roteiro é um JSON em videos/<id>/roteiro.json com este formato:

{
  "titulo": "título do YouTube (até 100 caracteres)",
  "descricao": "descrição do YouTube",
  "tags": ["ia", "..."],
  "thumb": {"linha1": "DO REAL PRO", "linha2": "DESENHO"},
  "blocos": [
    {"texto": "fala narrada do bloco", "busca": "termo em inglês para achar imagem no Pexels"}
  ],
  "shorts": [
    {"titulo": "título do short", "de": 0, "ate": 2}
  ]
}

"de" e "ate" são índices de blocos (inclusivos) que viram um short de até 60 s.
Sem ANTHROPIC_API_KEY, o Claude Code escreve esse arquivo (ver CLAUDE.md).
"""
import json
import re

from . import config, estado

SISTEMA = f"""Você é o roteirista de um canal de YouTube brasileiro sobre {config.NICHO}.
Escreve em português do Brasil, falado, direto, sem enrolação, com gancho forte nos
primeiros 10 segundos. Cada bloco tem de 2 a 4 frases (cerca de 15 a 25 segundos narrados).
Responda SOMENTE com JSON válido, sem comentários e sem markdown."""

FORMATO = """{"titulo": str, "descricao": str, "tags": [str],
 "thumb": {"linha1": str (até 14 letras), "linha2": str (até 10 letras)},
 "blocos": [{"texto": str, "busca": str (2 a 4 palavras em inglês para banco de imagens)}],
 "shorts": [{"titulo": str, "de": int, "ate": int}]}"""


def _claude(prompt: str) -> str:
    import anthropic

    cliente = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    resp = cliente.messages.create(
        model=config.CLAUDE_MODEL,
        max_tokens=16000,
        system=SISTEMA,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(b.text for b in resp.content if b.type == "text")


def _json(texto: str) -> dict:
    texto = re.sub(r"^```(?:json)?|```$", "", texto.strip(), flags=re.M).strip()
    return json.loads(texto[texto.find("{"): texto.rfind("}") + 1])


def validar(r: dict) -> dict:
    for campo in ("titulo", "descricao", "blocos"):
        if not r.get(campo):
            raise ValueError(f"roteiro sem '{campo}'")
    r.setdefault("tags", [])
    r.setdefault("thumb", {})
    r["thumb"].setdefault("linha1", r["titulo"].split(":")[0][:14])
    r["thumb"].setdefault("linha2", "")
    n = len(r["blocos"])
    shorts = []
    for s in r.get("shorts", []):
        de, ate = int(s.get("de", 0)), int(s.get("ate", 0))
        if 0 <= de <= ate < n:
            shorts.append({"titulo": s.get("titulo", r["titulo"])[:90], "de": de, "ate": ate})
    r["shorts"] = shorts[:4]
    r["titulo"] = r["titulo"][:100]
    return r


def pauta(job: dict) -> None:
    with estado.Etapa(job, "pauta") as e:
        if job["tema"]:
            e.atualizar(1, f"tema definido: {job['tema']}")
            return
        if not config.ANTHROPIC_API_KEY:
            raise RuntimeError("sem tema e sem ANTHROPIC_API_KEY: passe um tema ou peça ao Claude Code")
        e.atualizar(0.3, "lendo o nicho e escolhendo o tema")
        ideia = _json(_claude(
            f'Sugira UM tema de vídeo longo para o canal, com potencial de clique. '
            f'Responda {{"tema": "..."}}'))
        job["tema"] = ideia["tema"]
        e.atualizar(1, f"tema: {job['tema']}")


def roteiro(job: dict, ajuste: str = "") -> dict:
    caminho = estado.pasta(job["id"]) / "roteiro.json"
    with estado.Etapa(job, "roteiro") as e:
        if caminho.exists() and not ajuste:
            e.atualizar(0.5, "usando o roteiro escrito pelo Claude Code")
            r = validar(json.loads(caminho.read_text(encoding="utf-8")))
        else:
            if not config.ANTHROPIC_API_KEY:
                raise RuntimeError("sem ANTHROPIC_API_KEY: peça ao Claude Code para escrever roteiro.json")
            minutos = config.DURACAO_ALVO_MIN
            prompt = (f"Tema: {job['tema']}\nDuração alvo: {minutos} minutos "
                      f"(cerca de {minutos * 3} blocos). Inclua de 2 a 4 shorts com os trechos mais fortes.\n"
                      f"Formato: {FORMATO}")
            if ajuste and caminho.exists():
                prompt = (f"Este é o roteiro atual:\n{caminho.read_text(encoding='utf-8')}\n\n"
                          f"Aplique este ajuste pedido pelo dono do canal: {ajuste}\n"
                          f"Devolva o roteiro completo no mesmo formato: {FORMATO}")
            e.atualizar(0.2, "escrevendo bloco a bloco")
            r = validar(_json(_claude(prompt)))
        caminho.write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
        job["titulo"] = r["titulo"]
        job["blocos"] = len(r["blocos"])
        job["n_shorts"] = len(r["shorts"])
        e.atualizar(1, f"{len(r['blocos'])} blocos")
        return r
