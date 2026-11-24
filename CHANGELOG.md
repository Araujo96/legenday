# Changelog

## 0.5.0
- **Tour guiado na primeira vez:** a janela escurece e um destaque amarelo passa por cada parte (Vídeo,
  Legenda, a área da legenda, controles, Repetir/PT, Palavras, sincronia e ajuda), com uma explicação curta em
  cada passo. Setas ou Enter avançam, Esc pula. Dá para rever pelo botão **?** → **Ver o tour guiado**.
  Deixa claro, por exemplo, que a legenda aparece embaixo do vídeo, e não em cima.
- O tour substitui a janela de ajuda que abria sozinha na primeira vez (a ajuda completa continua no **?**).

## 0.4.0

### Novidades para estudar
- **Pronúncia:** botão 🔊 no pop-up toca a gravação da palavra feita por uma pessoa (Wikimedia Commons, sotaque
  americano quando houver). Sem gravação da palavra, usa a da forma base.
- **Modo repetir frase** (botão **Repetir** ou tecla **P**): o vídeo pausa no fim de cada fala para você repetir
  em voz alta; **Espaço** continua e **R** ouve a fala de novo.
- **Legenda dupla** (botão **PT** ou tecla **T**): a fala em português aparece embaixo da inglesa. Usa uma legenda
  em português ao lado do vídeo (`Filme.pt-BR.srt`) ou aberta pelo menu **Legenda**; sem ela, traduz cada fala na
  hora (e já adianta a próxima).
- **Revisão dentro do app** (**Palavras → Revisar**): cartões com as palavras do dia, em revisão espaçada (errou,
  volta hoje; acertou, o intervalo cresce: 1, 3, 7, 16, 35 dias). **Ouvir a fala no filme** toca a cena em que a
  palavra apareceu e pausa no fim. O app avisa ao abrir quando há palavras para revisar.
- **Arrastar e soltar:** solte um vídeo na janela para abri-lo (a legenda ao lado vem junto) ou um `.srt` para
  trocar a legenda.
- Palavras salvas guardam o início da fala (antes: o instante do clique), para a revisão tocar a frase inteira.

### Visual
- Barra de controles redesenhada: botões em grupos segmentados ([Vídeo | Legenda | Áudio], [Repetir | PT] e a
  sincronia [− | +0,0s | +]), contador de palavras num selo amarelo, setinhas de menu desenhadas pelo app, brilho
  no botão de play e separadores entre os grupos. Todos os botões com a mesma altura e cantos arredondados.
- Botão de volume silencia e volta o som (com ícone de mudo).
- Pop-up, vocabulário e revisão com o mesmo padrão de botões; o botão principal de cada janela fica em amarelo e
  o "salvo" do pop-up fica verde.
- Cores reunidas numa paleta só (`ui/style.py`).

### Por dentro
- Código organizado em camadas: `core` (sem interface e sem internet), `services` (internet), `playback` (mpv) e
  `ui` (Qt). A janela principal foi dividida em partes menores, e o mpv fica atrás de um invólucro que nunca
  derruba a interface. Os testes seguem a mesma divisão (`tests/core`, `tests/services`, `tests/ui`).
- `player_ui.py` virou `ui/icons.py` + `ui/style.py`; `offsets.py` foi incorporado a `core/settings.py`;
  `audio.py` virou `core/audio_tracks.py` (para não confundir com a pronúncia).
- O autoteste do executável mostra de onde veio cada falha.
- Prints da documentação em JPG (13,7 MB → 2,7 MB).
- **Testes de interface** com pytest-qt e um player falso (clique na palavra, pop-up, atalhos, modo repetir,
  legenda dupla, revisão). O CI roda lint (ruff) e os testes no Linux e no Windows.
- Release com versões fixas do libmpv e do ffmpeg, conferidas por SHA-256.
- Pacote do Windows mais leve (162 → 146 MB): fora as partes do Qt que o app não usa (OpenGL por software,
  Quick/QML, Pdf). O `.zip` traz um `LEIA-ME.txt` para quem não é da área (inclusive o aviso azul do Windows).
- Versão definida num lugar só (`legenday/__init__.py`).
- O libmpv não é mais procurado na pasta de onde o app foi aberto (evita carregar uma DLL estranha).
- README com GIF e vídeo de demonstração, resumo em inglês e mapa do código.

### Tradução e correções
- **Tradução com contexto:** ao clicar numa palavra ou expressão, o pop-up também mostra a fala inteira
  traduzida ("na frase: Seja gentil com ela.") e os outros sentidos da palavra ("broke": falido · também:
  rompeu, quebrou). Se um dos sentidos aparece na fala traduzida, ele passa a ser o principal.
- Traduções de palavras mais limpas: a que só repete o inglês ("remind" → "remind") deixa de ser a principal
  (agora "lembrar"); somem sugestões de qualidade zero, rótulos de programa ("ENVIAR") e o ponto final em
  palavra solta ("mudou." → "mudou").
- Corrige legenda de outro episódio carregada sozinha (`Show S01E1.mkv` pegava `Show S01E10.en.srt`).
- Cache de tradução não mistura mais siglas com palavras comuns ("US" = EUA, "us" = nós).
- Atalhos (setas, Espaço, Enter...) não roubam mais as teclas da janela de vocabulário; Enter agora também
  fecha o pop-up e continua o vídeo, como diz a ajuda.
- Se o modelo offline (Argos) falhar, a tradução online é usada; mensagens de erro dizem a causa real
  (sem internet, erro do servidor ou limite diário).
- O pop-up abre acima da legenda inteira (não cobre mais a 1ª linha em falas de duas linhas) e o da frase
  inteira fica centralizado sobre a legenda.
- Traduções limpas: some o travessão que o MyMemory às vezes inventa ("- Há uma lição") e a maiúscula
  indevida em palavras comuns ("heart" → "coração", não "Coração").
- Erro ao gravar a exportação do Anki mostra um aviso em vez de falhar em silêncio; palavras com apóstrofo
  curvo (`don’t`) ficam em negrito no cartão.

## 0.3.3
- **Executável para Windows:** fluxo automático do GitHub (`release.yml`) que monta o `legenDay.exe` com o
  libmpv e um ffmpeg LGPL, testa o resultado (`--selftest`) e publica o `.zip` na página de Releases.
  Receita em `packaging/`; avisos de licença em `THIRD_PARTY_NOTICES.md`.
- Projeto organizado para publicação: o ícone agora é um arquivo fixo (`assets/icon.png` e `icon.ico`);
  removido o código que gerava a imagem.
- **Tradução ao clicar numa palavra muito mais rápida:** a tradução aparece assim que chega e a forma base,
  a pronúncia e a definição entram logo depois (antes, o pop-up esperava 3 a 4 consultas de rede em fila).
  O dicionário usa tempo limite menor e, se estiver fora do ar, não atrasa os cliques seguintes.
  O app também resolve o endereço dos serviços ao abrir, para o primeiro clique não esperar.
- **Legenda fiel ao mpv:** falas que acontecem ao mesmo tempo (diálogo sobreposto, letreiros longos com falas
  curtas dentro) agora aparecem todas, empilhadas; antes só uma era mostrada. Medido contra o mpv: de 16-26%
  de divergência nesses casos para 0%. Falas de duração zero são ignoradas e as invertidas duram até a
  próxima, exatamente como no mpv.
- **Legenda aparece mais cedo:** o relógio da legenda passou de 100 ms para 40 ms (atraso médio de 85 ms para 16 ms).
- Nova tecla **Y**: alinha a legenda com a fala (aperte ao ouvir o início de uma frase).

## 0.3.2
- **Escolha do áudio:** novo botão **Áudio** lista as faixas do vídeo (idioma, codec, canais) e permite trocar.
  Em vídeos com mais de uma faixa (por exemplo, dublado em português + original em inglês), o app agora
  começa pela faixa em **inglês** em vez da padrão do arquivo, e avisa qual áudio está tocando.
- A barra de controles se adapta: em janelas estreitas os botões da esquerda mostram só o ícone.
- A janela abre num tamanho que cabe na tela do usuário.

## 0.3.1
- O app agora se chama **legenDay** (antes: Legendário). O pacote passa a ser `legenday` (`python -m legenday`).
- Quem já usou o app mantém o vocabulário: a pasta de dados antiga (`~/.legendario`) é migrada sozinha para
  `~/.legenday`. A variável de ambiente `LEGENDARIO_MPV_DIR` (e as demais `LEGENDARIO_*`) agora são `LEGENDAY_*`.
- Cartões do Anki exportados agora usam o baralho e a tag `legenDay`/`legenday`.

## 0.3.0
- Ajuda dentro do app: botão **?** (ou tecla **F1**) com primeiros passos, atalhos, privacidade e informações
  para suporte (com botão para copiá-las e colar em um relato de problema).
- A ajuda aparece sozinha na primeira vez que o app é aberto.
- Texto de orientação na área da legenda enquanto falta abrir o vídeo ou a legenda.

## 0.2.3
Correções da bateria de testes de robustez:
- Legendas em UTF-16 agora abrem; arquivos inválidos mostram uma mensagem clara em português.
- Entidades HTML (`&amp;`, `&lt;`...) e `\h` de legendas ASS são convertidos corretamente.
- Falas sem duração na legenda agora aparecem (por 2s) em vez de ficarem invisíveis.
- Reconhece legendas ao lado do vídeo nomeadas como `Filme.en.srt` / `Filme.English.srt`.
- Faixas embutidas "forçadas" ou só de letreiros não são mais carregadas automaticamente.
- Banco de dados corrompido não impede mais o app de abrir nem a tradução de funcionar (guarda uma cópia
  `*.corrompido-<hora>` e recomeça); falha ao gravar vocabulário ou sincronia não derruba o app.
- Tradução: textos de aviso do MyMemory (limite diário) não são mais mostrados como se fossem a tradução.
- Leitura do dicionário tolera respostas malformadas.

## 0.2.2
- Avisos grandes sobre o vídeo (topo, centralizados, também em tela cheia): sincronia da legenda,
  extração de legenda embutida, legenda carregada, velocidade, pulos e navegação entre frases.
  Sem vídeo em reprodução, o aviso aparece no rodapé, agora com letra maior.

## 0.2.1
- Corrige texto invisível na linha selecionada da janela de vocabulário.


## 0.2.0
- Vocabulário: salvar palavras com a frase do filme, janela de gerenciamento e exportação para o Anki.
- Pop-up com dicionário: forma base (lematização offline com simplemma), pronúncia e definições.
- Palavras salvas ficam destacadas na legenda (inclusive outras formas da mesma palavra).
- Legendas embutidas (MKV/MP4) via ffmpeg, com carregamento automático da faixa em inglês.
- Ajuste de sincronia da legenda (G/H, botões), lembrado por arquivo.

## 0.1.0
- Primeira versão: player com mpv, legenda clicável e tradução em pop-up.
