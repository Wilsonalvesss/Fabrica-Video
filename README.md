# Fábrica de vídeos

Seu agente de produção para YouTube. Você digita o tema, aperta **Produzir vídeo** e a Fábrica faz o resto.

Nove agentes trabalham em sequência num escritório pixel art:

| # | Agente | O que faz | Ferramenta |
|---|---|---|---|
| 1 | Pauta | escolhe o tema, se você não mandar um | Claude (sua assinatura) |
| 2 | Roteiro | escreve o vídeo em blocos, título, descrição, tags, thumb e shorts | Claude (sua assinatura) |
| 3 | Narração | gera a voz e a legenda | MoneyPrinterTurbo + ElevenLabs |
| 4 | Cenas | baixa um vídeo de banco para cada bloco, na ordem do roteiro | MoneyPrinterTurbo + Pixabay (ou Pexels) |
| 5 | Montagem | junta tudo em 1920x1080 com legenda e trilha | MoneyPrinterTurbo |
| 6 | Shorts | faz os shorts 9:16 dos melhores trechos | MoneyPrinterTurbo |
| 7 | Thumbnail | desenha a thumb amarela e confere Áudio, Pronúncia, Ordem e Legenda | Fábrica |
| 8 | Agendamento | escolhe o próximo horário livre | Fábrica |
| 9 | API do YouTube | sobe vídeo, thumb e shorts agendados | YouTube Data API oficial |

O motor é o [MoneyPrinterTurbo](https://github.com/harry0703/MoneyPrinterTurbo) (licença MIT), baixado
pelo instalador numa versão testada. A Fábrica cuida do roteiro, do painel, da thumbnail e da publicação.

## 1. Instalar (uma vez)

Você precisa de:
- [Python 3.11 ou mais novo](https://www.python.org/downloads/) (no Windows, marque "Add Python to PATH")
- [Git](https://git-scm.com/downloads)
- [ffmpeg](https://ffmpeg.org/download.html) (Windows: `winget install ffmpeg`; Mac: `brew install ffmpeg`)
- [Claude Code](https://claude.com/claude-code). Depois de instalar, rode `claude` uma vez e faça login com a sua conta do Claude.

Na pasta do projeto:

```
git clone https://github.com/Wilsonalvesss/fabrica-video
cd fabrica-video
python -m venv .venv
.venv\Scripts\python.exe -m pip install --upgrade pip   (Windows; use .venv\Scripts\python.exe no lugar de python)  ou  source .venv/bin/activate  (Mac/Linux)
pip install -r requirements.txt
copy .env.example .env          (Windows)  ou  cp .env.example .env       (Mac/Linux)
python -m fabrica instalar
```

## 2. Chaves (uma vez)

Abra o `.env` e preencha:
- `ELEVENLABS_API_KEY` e `ELEVENLABS_VOICE_ID`: em elevenlabs.io, *Settings → API Keys*; o ID da voz fica na biblioteca de vozes.
- `PIXABAY_API_KEY`: crie uma conta grátis no [Pixabay](https://pixabay.com/accounts/register/) e, logado, abra
  [pixabay.com/api/docs](https://pixabay.com/api/docs/#api_search_images): a chave aparece em "Parameters → key".
  (O Pexels também funciona, mas parou de liberar chaves novas.)
- `NICHO`: o assunto do canal, usado quando você não manda tema.

## 3. Conectar o YouTube (uma vez)

1. Entre em [console.cloud.google.com](https://console.cloud.google.com) com a conta do canal e crie um projeto (ex.: "Fabrica").
2. Em *APIs e serviços → Biblioteca*, procure **YouTube Data API v3** e clique em **Ativar**.
3. Em *APIs e serviços → Tela de consentimento OAuth*: tipo **Externo**, preencha nome e e-mail, e em
   *Usuários de teste* adicione o e-mail do seu canal.
4. Em *APIs e serviços → Credenciais → Criar credenciais → ID do cliente OAuth*: tipo **App para computador**.
   Baixe o JSON e salve na pasta do projeto com o nome `client_secret.json`.
5. Rode `python -m fabrica conectar-youtube`. O navegador abre, você escolhe o canal e autoriza.
   Fica salvo em `youtube_token.json` e não pede de novo.

Limites do Google que valem para todo mundo:
- Enquanto o app estiver em modo de teste, o login expira a cada 7 dias. Para não expirar, publique o app
  em *Tela de consentimento → Publicar app* (não precisa de revisão para uso próprio, só aparece um aviso de "app não verificado" que você aceita).
- A cota grátis é de 10.000 unidades por dia; cada envio gasta cerca de 1.600. Dá uns 6 envios por dia
  (1 vídeo longo + 4 shorts = 5 envios).
- **Importante:** o Google trava como *privado* todo vídeo enviado por um projeto de API que ainda não passou
  pela auditoria. Até lá, os vídeos sobem e ficam agendados, mas não viram públicos sozinhos: você abre o
  YouTube Studio e muda para público (ou programa) com um clique. Para tirar essa trava, peça a auditoria
  grátis no formulário [YouTube API Services Audit](https://support.google.com/youtube/contact/yt_api_form)
  dizendo que é uma ferramenta própria para publicar no seu canal. Costuma levar algumas semanas.

## 4. Usar

```
python -m fabrica iniciar
```

Isso liga o motor e abre o painel em http://localhost:8000. Digite o tema (ou deixe em branco) e aperte
**Produzir vídeo**. Os robôs trabalham na aba **Fábrica**; quando terminar, o vídeo aparece na aba
**Revisão** com **Aprovar**, **Revisar** (assistir e ler os blocos) e **Pedir um ajuste**. Ao aprovar,
o agente 9 sobe o vídeo, a thumbnail e os shorts já agendados.

**Cenas de jogo buscadas na web:** quando o vídeo é sobre um jogo, o roteiro informa o nome dele e a Fábrica
busca sozinha na Steam as screenshots e os trailers oficiais, corta trechos de 5 segundos e mistura com cenas
genéricas de games do Pixabay (controle, estádio, torcida). Os trailers são da EA/da produtora: o Content ID
pode reivindicar o Short. Para usar só screenshots, coloque `USAR_TRAILERS=false` no `.env`.

**Cenas do seu jogo:** banco de imagens grátis não tem gameplay de EA FC nem de outros jogos. Crie a pasta
`clipes` dentro da Fábrica e jogue lá as suas gravações (mp4). Quando houver vídeos nessa pasta, a Fábrica
corta trechos aleatórios de 5 segundos delas para montar as cenas, no lugar do Pixabay. Para voltar ao banco
de imagens, é só esvaziar a pasta.

**Pelo celular:** no `.env`, coloque `PAINEL_HOST=0.0.0.0` e uma senha em `PAINEL_SENHA`. Ao iniciar, a janela
mostra o endereço para o celular (algo como `http://192.168.0.10:8000`). Funciona com o celular no mesmo
Wi-Fi do notebook. Na primeira vez, o Windows pergunta se libera o acesso: marque "Redes privadas" e permita.

Quer 100% automático, sem revisão? Coloque `AUTO_PUBLICAR=true` no `.env`: ao terminar, ele já publica.

Outros comandos: `python -m fabrica ajuda`. Se algo travar, o erro aparece embaixo do escritório e o
log do motor fica em `motor.log`.
