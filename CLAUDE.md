# Fábrica de vídeos

Este projeto produz vídeos de YouTube com 9 agentes em sequência:
Pauta → Roteiro → Narração → Cenas → Montagem → Shorts → Thumbnail → Agendamento → API do YouTube.
O código está em `fabrica/` e o painel em `web/index.html`.

## Quando o dono pedir um vídeo

O dono usa só o Claude (sem chave de API), então **você é o agente de Pauta e de Roteiro**:

1. Se ele não deu tema, escolha um tema com potencial de clique dentro do nicho em `.env` (`NICHO`).
2. Rode `python -m fabrica novo "<tema>"`. Ele cria `videos/Vxx/` e mostra o id.
3. Escreva `videos/Vxx/roteiro.json` no formato descrito no topo de `fabrica/roteiro.py`:
   - português do Brasil, falado, gancho forte nos primeiros 10 segundos;
   - cerca de 3 blocos por minuto (`DURACAO_ALVO_MIN` no `.env`), cada bloco com 2 a 4 frases;
   - `busca` de cada bloco: 2 a 4 palavras em inglês que achem uma cena boa no Pexels;
   - `thumb.linha1` até 14 letras e `thumb.linha2` até 10 letras, impacto máximo;
   - 2 a 4 `shorts` com os trechos mais fortes, cada um com no máximo 60 s (2 ou 3 blocos);
   - a descrição termina chamando para comentar.
4. Rode `python -m fabrica continuar Vxx`. Quando terminar, diga ao dono para abrir o painel
   (`python -m fabrica painel`, aba Revisão) e aprovar.

## Quando houver ajuste pendente

Se existir `videos/Vxx/AJUSTE_PENDENTE.txt`, aplique o pedido no `roteiro.json` desse vídeo,
apague o arquivo e rode `python -m fabrica continuar Vxx`.

## Regras

- Nunca aprove nem publique um vídeo sem o dono pedir: aprovar é com ele.
- Nunca suba `.env`, `client_secret*.json` ou `youtube_token.json` para o Git.
- Se uma etapa falhar, leia o erro em `videos/Vxx/job.json` (campo `msg` da etapa) e corrija.
