"""Janela de ajuda: primeiros passos, atalhos e sobre o app."""
from html import escape

from PySide6.QtWidgets import QApplication, QDialog, QHBoxLayout, QPushButton, QTabWidget, QTextBrowser, QVBoxLayout

from legenday import __version__
from legenday.branding import APP_NAME, REPO_URL, TAGLINE
from legenday.ui.style import DIALOG_STYLE

CSS = """
body { color:#e8e8ee; font-size:14px; }
h1 { color:#ffd54a; font-size:22px; }
h2 { color:#ffd54a; font-size:16px; margin-top:16px; margin-bottom:2px; }
p, li { color:#d4d4dc; }
.key { background-color:#3a3a46; color:#ffffff; font-weight:bold; }
.dim { color:#9a9aa6; }
td { padding:6px 14px 6px 0; color:#d4d4dc; }
a { color:#ffd54a; }
code { color:#ffd54a; }
"""


def key(*names: str) -> str:
    return " ou ".join(f'<span class="key">&nbsp;{escape(n)}&nbsp;</span>' for n in names)


def table(rows) -> str:
    return "<table>" + "".join(f"<tr><td>{k}</td><td>{d}</td></tr>" for k, d in rows) + "</table>"


START = """
<p class="dim">Prefere ver na tela para que serve cada botão? Clique em <b>Ver o tour guiado</b>, aqui embaixo.</p>
<h2>1. Abra um filme</h2>
<p class="dim">Em janelas mais estreitas, os botões da barra mostram só o ícone: passe o mouse para ver o nome.</p>
<p>Clique em <b>Vídeo</b> e escolha o arquivo (MP4, MKV, AVI...), ou <b>arraste o arquivo para a janela</b>.
Se existir uma legenda na mesma pasta com o mesmo nome (<code>Filme.srt</code> ou <code>Filme.en.srt</code>),
ela abre sozinha.</p>

<h2>2. Escolha a legenda</h2>
<p>No botão <b>Legenda</b> (ou arrastando o <code>.srt</code> para a janela) você abre um arquivo de legenda, ou
usa uma legenda que está <i>dentro</i> do vídeo (já vem pronto no programa baixado; rodando pelo código, precisa
do ffmpeg, veja o README). Se não houver legenda ao lado do vídeo, o app tenta carregar sozinho a faixa em inglês
embutida.</p>

<h2>Vídeo com mais de um áudio?</h2>
<p>O app já começa pela faixa em <b>inglês</b>, se o vídeo tiver. Para trocar (por exemplo, para o português),
use o botão <b>Áudio</b>.</p>

<h2>3. Clique nas palavras</h2>
<p>Clique numa palavra da legenda: o vídeo pausa e aparece a tradução, outros sentidos da palavra, a forma base, a
definição e a <b>fala inteira traduzida</b> (para você saber qual sentido o personagem usou). No 🔊 você ouve a
pronúncia gravada por uma pessoa de verdade.<br>
Para uma <b>expressão</b> (como <i>give up</i>), clique na primeira palavra e use <b>Shift + clique</b> na última.
Para a frase inteira, use o botão <b>Traduzir a frase</b>, logo abaixo da legenda (ou a tecla <b>F</b>).<br>
Para continuar assistindo, aperte <b>Espaço</b>, <b>Enter</b> ou <b>Esc</b>.</p>

<h2>4. Guarde e revise o que aprendeu</h2>
<p>No pop-up, clique em <b>Salvar no vocabulário</b>. Palavras salvas ficam <span style="color:#ffd54a">amarelas</span>
nas próximas legendas.<br>
Em <b>Palavras → Revisar</b> aparecem cartões com as palavras do dia: tente lembrar, aperte <b>Espaço</b> para ver a
resposta e diga se acertou (<b>1</b> errei, <b>2</b> acertei). O que você erra volta ainda hoje; o que acerta volta
daqui a alguns dias. Se o filme da palavra estiver aberto, <b>Ouvir a fala no filme</b> toca o trecho.<br>
Também dá para exportar tudo para o <b>Anki</b> (programa gratuito de cartões de estudo).</p>

<h2>Treine a fala e o ouvido</h2>
<ul>
<li><b>Modo repetir frase</b> (botão <b>Repetir</b> ou tecla <b>P</b>): o vídeo pausa no fim de cada fala para você
repetir em voz alta. <b>Espaço</b> continua; <b>R</b> ouve a fala de novo.</li>
<li><b>Legenda dupla</b> (botão <b>PT</b> ou tecla <b>T</b>): a fala em português aparece embaixo da inglesa. Se houver
uma legenda em português ao lado do vídeo (<code>Filme.pt-BR.srt</code>) ou aberta pelo menu <b>Legenda</b>, ela é
usada; senão, o app traduz cada fala na hora. A tradução automática usa a cota diária do serviço gratuito, então
prefira o arquivo .srt em filmes longos.</li>
</ul>

<h2>5. Legenda adiantada ou atrasada?</h2>
<p>Use os botões <b>−</b> e <b>+</b> ao lado do volume (ou as teclas <b>G</b> e <b>H</b>). O ajuste fica
guardado para essa legenda.<br>
Mais rápido: quando ouvir o <b>início de uma frase</b>, aperte <b>Y</b>. O app alinha a legenda mais próxima com esse
instante.</p>

<h2>Dicas para estudar</h2>
<ul>
<li>Deixe a velocidade em <b>0,75x</b> para treinar o ouvido em falas rápidas.</li>
<li>Use <b>R</b> para ouvir a frase de novo antes de clicar nas palavras.</li>
<li>Assista uma vez com a legenda dupla e depois, sem ela, no modo repetir frase.</li>
<li>Revise as palavras um pouco por dia: o app avisa quando há palavras para revisar.</li>
</ul>

<h2>Algo não funciona?</h2>
<ul>
<li><b>Erro sobre libmpv ao abrir:</b> coloque o arquivo <code>libmpv-2.dll</code> na pasta <code>libs</code>
(veja o README).</li>
<li><b>A tradução não aparece:</b> o app precisa de internet, a não ser que você instale o modelo offline.</li>
<li><b>Legenda embutida não aparece:</b> instale o ffmpeg com <code>pip install -e ".[embedded]"</code>.
Legendas em imagem (PGS/VobSub) não são suportadas.</li>
</ul>
"""

KEYS = (
    "<h2>Teclado</h2>" + table([
        (key("Espaço", "Enter"), "Pausar / continuar. Com o pop-up aberto, fecha o pop-up e continua o vídeo"),
        (key("Esc"), "Fechar o pop-up"),
        (key("R"), "Repetir a frase atual"),
        (key("←", "→"), "Voltar / avançar 5 segundos"),
        (key("G", "H"), "Adiantar / atrasar a legenda em 0,1 s (com <b>Shift</b>: 1 s)"),
        (key("Y"), "Alinhar a legenda com a fala: aperte quando ouvir o início de uma frase"),
        (key("P"), "Ligar/desligar o modo repetir frase (pausa no fim de cada fala)"),
        (key("T"), "Ligar/desligar a legenda em português (legenda dupla)"),
        (key("F"), "Traduzir a frase inteira (o mesmo que o botão Traduzir a frase)"),
        (key("F11"), "Tela cheia (ou o botão no canto direito da barra); Esc sai"),
        (key("F1"), "Abrir esta ajuda"),
    ]) + "<h2>Mouse</h2>" + table([
        ("Clique numa palavra", "Traduzir a palavra"),
        ("Shift + clique", "Selecionar uma expressão (da 1ª palavra até a clicada)"),
        ("Clique ou arraste na barra de tempo", "Pular para qualquer ponto do filme"),
        ("Botões de frase (anterior e próxima)", "Repetir / voltar uma frase / ir para a próxima frase"),
        ("Botões de 10 segundos (voltar e avançar)", "Voltar / avançar 10 segundos"),
        ("Botões − e + da sincronia", "Ajustar a legenda (Shift + clique: 1 s). Clique no valor para zerar"),
        ("🔊 no pop-up", "Ouvir a pronúncia da palavra"),
    ]) + "<h2>Revisão</h2>" + table([
        (key("Espaço"), "Mostrar a resposta"),
        (key("1", "2"), "Errei / acertei"),
    ])
)


def about_html(diagnostics: str) -> str:
    link = f'<p><a href="{escape(REPO_URL)}">{escape(REPO_URL)}</a></p>' if REPO_URL else ""
    return f"""
<h1>{escape(APP_NAME)} <span class="dim" style="font-size:14px">versão {escape(__version__)}</span></h1>
<p>{escape(TAGLINE)}. Software livre, licença MIT.</p>{link}

<h2>Privacidade</h2>
<p>Seus filmes e legendas ficam no seu computador e nunca são enviados. Para traduzir, o texto que você clica é
enviado ao serviço gratuito <b>MyMemory</b> (a menos que o modelo offline esteja instalado), a palavra ao
dicionário online <b>Free Dictionary API</b> e ao <b>Wikimedia Commons</b> (de onde vêm as gravações de pronúncia).
Com a legenda dupla ligada e sem legenda em português, cada fala também vai para o MyMemory.
Ao abrir, o app pergunta ao <b>GitHub</b> qual é a versão mais nova, para avisar quando houver atualização
(nada seu é enviado nessa consulta).
Suas palavras salvas ficam só no seu computador.</p>

<h2>Feito com</h2>
<p>mpv (reprodução), Qt/PySide6 (interface), pysubs2 (legendas), simplemma (forma base das palavras),
ffmpeg (legendas embutidas) e, opcionalmente, Argos Translate (tradução offline).</p>

<h2>Informações para suporte</h2>
<p class="dim">Se encontrar um problema, use o botão <b>Copiar informações para suporte</b> e cole no relato.</p>
<pre style="color:#d4d4dc">{escape(diagnostics)}</pre>
"""


class HelpDialog(QDialog):
    def __init__(self, parent, diagnostics: str, on_tour=None):
        super().__init__(parent)
        self._on_tour = on_tour
        self.diagnostics = diagnostics
        self.setWindowTitle(f"Ajuda · {APP_NAME}")
        self.resize(720, 600)
        self.setStyleSheet(DIALOG_STYLE)

        tabs = QTabWidget()
        for title, html in (("Primeiros passos", START), ("Atalhos", KEYS), ("Sobre", about_html(diagnostics))):
            view = QTextBrowser()
            view.setOpenExternalLinks(True)
            view.document().setDefaultStyleSheet(CSS)
            view.setHtml(html)
            tabs.addTab(view, title)

        self.copy_btn = QPushButton("Copiar informações para suporte")
        self.copy_btn.clicked.connect(self._copy)
        self.tour_btn = QPushButton("Ver o tour guiado")
        self.tour_btn.setObjectName("primary")
        self.tour_btn.clicked.connect(self._tour)
        self.tour_btn.setVisible(on_tour is not None)
        close = QPushButton("Fechar")
        close.clicked.connect(self.accept)
        row = QHBoxLayout()
        row.addWidget(self.copy_btn)
        row.addStretch()
        row.addWidget(self.tour_btn)
        row.addWidget(close)

        lay = QVBoxLayout(self)
        lay.addWidget(tabs, 1)
        lay.addLayout(row)

    def _tour(self):
        self.accept()                 # fecha a ajuda: o tour precisa da janela principal à vista
        self._on_tour()

    def _copy(self):
        QApplication.clipboard().setText(self.diagnostics)
        self.copy_btn.setText("Copiado ✓")
