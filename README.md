# Fábrica de vídeos

Seu agente de produção para YouTube. Você decide, o agente executa.

Nove agentes trabalham em sequência num escritório pixel art:

| # | Agente | O que faz |
|---|---|---|
| 1 | Pauta | escolhe o tema (ou usa o que você mandou) |
| 2 | Roteiro | escreve o vídeo em blocos, com os trechos que viram shorts |
| 3 | Narração | gera a voz bloco a bloco (Edge TTS grátis ou ElevenLabs) |
| 4 | Cenas | busca um vídeo ou foto no Pexels para cada bloco |
| 5 | Montagem | junta cena + voz, queima a legenda e põe trilha (ffmpeg) |
| 6 | Shorts | corta os melhores trechos em 9:16 com título |
| 7 | Thumbnail | desenha a thumb amarela e confere Áudio, Pronúncia, Ordem e Legenda |
| 8 | Agendamento | escolhe o próximo horário livre |
| 9 | API do YouTube | depois que você aprova, sobe o vídeo, a thumb e os shorts agendados |

O roteiro pode ser escrito pelo **Claude Code** (sem custo extra além da sua assinatura)
ou pela API da Anthropic, se você colocar uma chave no `.env`.

## Instalação (uma vez)

1. Instale o [Python 3.11+](https://www.python.org/downloads/) e o [ffmpeg](https://ffmpeg.org/download.html)
   (no Windows: `winget install ffmpeg`; no Mac: `brew install ffmpeg`).
2. Na pasta do projeto:
   ```
   python -m venv .venv
   .venv\Scripts\activate        (Windows)   ou   source .venv/bin/activate   (Mac/Linux)
   pip install -r requirements.txt
   copy .env.example .env        (Windows)   ou   cp .env.example .env        (Mac/Linux)
   ```
3. Crie uma chave grátis em [pexels.com/api](https://www.pexels.com/api/) e cole em `PEXELS_API_KEY` no `.env`.
   Sem ela, cada cena vira um cartão com a frase do bloco.
4. (Opcional) Coloque músicas sem direitos autorais em `assets/musica/*.mp3` para a trilha de fundo.

## YouTube (uma vez)

1. Entre em [console.cloud.google.com](https://console.cloud.google.com), crie um projeto e ative a **YouTube Data API v3**.
2. Em *Tela de consentimento OAuth*, escolha "Externo" e adicione seu e-mail como usuário de teste.
3. Em *Credenciais*, crie um **ID do cliente OAuth** do tipo "App para computador", baixe o JSON e salve como
   `client_secret.json` na pasta do projeto.
4. Na primeira aprovação, o navegador abre para você autorizar o canal. Depois disso fica salvo em `youtube_token.json`.

Contas novas da API só podem publicar como privado até o Google auditar o app. O vídeo sobe agendado
(privado com data de publicação), que é exatamente o fluxo da Fábrica.

## Uso

Abra o Claude Code na pasta e peça: **"produz um vídeo sobre &lt;tema&gt;"**. Ele segue o `CLAUDE.md`:
escreve o roteiro e roda a esteira. Depois:

```
python -m fabrica painel
```

Abra http://localhost:8000. Na aba **Fábrica** você vê os robôs trabalhando; na aba **Revisão**,
cada vídeo tem **Aprovar**, **Revisar** (assistir e ler os blocos) e **Pedir um ajuste**.

Outros comandos: `python -m fabrica ajuda`.

## Créditos

A abordagem de montagem (tema → roteiro → voz → banco de imagens → legenda → vídeo) segue a ideia do
[MoneyPrinterTurbo](https://github.com/harry0703/MoneyPrinterTurbo). O código aqui foi escrito do zero.
