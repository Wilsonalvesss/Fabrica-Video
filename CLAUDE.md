# Fábrica de vídeos

Produz vídeos de YouTube com 9 agentes: Pauta → Roteiro → Narração → Cenas → Montagem → Shorts →
Thumbnail → Agendamento → API do YouTube. O código está em `fabrica/`, o painel em `web/index.html`
e o motor de vídeo (MoneyPrinterTurbo) é baixado em `motor/` por `python -m fabrica instalar`.

- `fabrica/roteiro.py`: pauta e roteiro pelo CLI `claude` (assinatura) ou pela API, se houver chave.
- `fabrica/motor.py`: instala o MoneyPrinterTurbo, gera o config.toml dele e chama a API dele.
- `fabrica/midia.py`: vídeo longo e shorts pelo motor; thumbnail e os 4 selos são nossos.
- `fabrica/youtube.py`: agendamento e envio pela YouTube Data API v3.
- `fabrica/esteira.py`: a ordem dos agentes, aprovação e ajustes.

Regras:
- Nunca aprove nem publique um vídeo sem o dono pedir.
- Nunca suba `.env`, `client_secret*.json`, `youtube_token.json`, `videos/` ou `motor/` para o Git.
- Se uma etapa falhar, o erro está em `videos/Vxx/job.json` (campo `msg` da etapa) e no `motor.log`.
