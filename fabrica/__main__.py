"""Linha de comando da Fábrica.

  python -m fabrica painel                 abre o painel em http://localhost:8000
  python -m fabrica produzir "tema"        produz um vídeo (sem tema, a pauta escolhe)
  python -m fabrica novo "tema"            cria a pasta do vídeo para o Claude Code escrever o roteiro
  python -m fabrica continuar V03          roda a esteira de um vídeo que já tem roteiro.json
  python -m fabrica aprovar V03            aprova e agenda no YouTube
  python -m fabrica ajustar V03 "pedido"   refaz o vídeo com um ajuste
  python -m fabrica status                 lista os vídeos
"""
import sys

from . import esteira, estado


def main(args):
    if not args or args[0] in ("-h", "--help", "ajuda"):
        print(__doc__)
        return
    cmd, resto = args[0], args[1:]
    if cmd == "painel":
        from . import painel

        painel.rodar(int(resto[0]) if resto else 8000)
    elif cmd == "produzir":
        job = esteira.produzir(" ".join(resto))
        print(f"{job['id']}: {job['status']}  (pasta videos/{job['id']})")
    elif cmd == "novo":
        job = estado.criar(" ".join(resto))
        print(f"{job['id']} criado. Escreva videos/{job['id']}/roteiro.json e rode: python -m fabrica continuar {job['id']}")
    elif cmd == "continuar":
        job = esteira.produzir(vid=resto[0])
        print(f"{job['id']}: {job['status']}")
    elif cmd == "aprovar":
        job = esteira.aprovar(resto[0])
        print(f"{job['id']}: {job['status']} {job.get('youtube_id', '')}")
    elif cmd == "ajustar":
        job = esteira.ajustar(resto[0], " ".join(resto[1:]))
        print(f"{job['id']}: {job['status']}")
    elif cmd == "status":
        for j in estado.todos():
            print(f"{j['id']}  {j['status']:<11} {j.get('titulo') or j['tema']}")
    else:
        print(f"Comando desconhecido: {cmd}\n{__doc__}")
        sys.exit(1)


if __name__ == "__main__":
    main(sys.argv[1:])
