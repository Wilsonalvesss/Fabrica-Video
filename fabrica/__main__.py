"""Linha de comando da Fábrica.

  python -m fabrica instalar               baixa o motor (MoneyPrinterTurbo) e as dependências
  python -m fabrica iniciar                liga o motor e abre o painel em http://localhost:8000
  python -m fabrica conectar-youtube       autoriza a Fábrica a publicar no seu canal (uma vez)
  python -m fabrica produzir "tema"        produz um vídeo pelo terminal (motor precisa estar ligado)
  python -m fabrica continuar V03          retoma um vídeo que parou com erro
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
    if cmd == "instalar":
        from . import motor

        motor.instalar()
    elif cmd in ("iniciar", "painel"):
        import webbrowser

        from . import motor, painel

        proc = None
        if not motor.no_ar():
            print("Ligando o motor (MoneyPrinterTurbo)...")
            proc = motor.iniciar()
        try:
            webbrowser.open("http://localhost:8000")
            painel.rodar(8000)
        finally:
            if proc:
                proc.terminate()
    elif cmd == "conectar-youtube":
        from . import youtube

        canal = youtube._servico().channels().list(part="snippet", mine=True).execute()
        print("Conectado ao canal:", canal["items"][0]["snippet"]["title"])
    elif cmd == "produzir":
        job = esteira.produzir(" ".join(resto))
        print(f"{job['id']}: {job['status']}  (pasta videos/{job['id']})")
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
