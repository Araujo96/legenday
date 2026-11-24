"""Cores e estilos (QSS) da janela principal e dos diálogos.

Botões seguem três formas, sempre com 36 px de altura:
  - pílula: um botão sozinho (Palavras, ajuda);
  - grupo segmentado: botões irmãos num trilho com fundo próprio (Vídeo|Legenda|Áudio, Repetir|PT, sincronia);
  - redondo: os controles de reprodução no centro (o play em amarelo).
"""

ACCENT = "#ffd54a"          # amarelo do app
ACCENT_HOVER = "#ffe17d"
ACCENT_PRESSED = "#e6bf3f"
BG = "#111114"              # fundo da janela e da legenda
BAR = "#16161b"             # barra de controles
SURFACE = "#202028"         # botões e trilhos
SURFACE_HOVER = "#2c2c36"
SURFACE_PRESSED = "#363642"
BORDER = "#2e2e39"
TEXT = "#ececf1"
MUTED = "#9a9aa6"
DIM = "#6f6f7a"


def main_style() -> str:
    """QSS da janela principal (chamar depois de criar o QApplication: gera a imagem da setinha)."""
    from .icons import icon_file
    chevron = icon_file("chevron", MUTED)
    chevron_dark = icon_file("chevron", "#111111")
    return f"""
QMainWindow, QWidget#root {{ background:{BG}; }}
QFrame#controls {{ background:qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #18181e, stop:1 #131317);
    border-top:1px solid #24242c; }}
#controls QLabel#time {{ color:#b4b4c0; font-size:12px; min-width:46px; }}
#controls QFrame#sep {{ background:#2a2a33; }}

/* controles de reprodução (redondos) */
#controls QToolButton {{ background:transparent; border:none; border-radius:20px; }}
#controls QToolButton:hover {{ background:{SURFACE_HOVER}; }}
#controls QToolButton:pressed {{ background:{SURFACE_PRESSED}; }}
#controls QToolButton#play {{ background:{ACCENT}; border-radius:24px; }}
#controls QToolButton#play:hover {{ background:{ACCENT_HOVER}; }}
#controls QToolButton#play:pressed {{ background:{ACCENT_PRESSED}; }}

/* pílula: botão sozinho */
#controls QPushButton#pill {{ background:{SURFACE}; color:{TEXT}; border:1px solid {BORDER};
    border-radius:10px; padding:0 14px; min-height:34px; max-height:34px; font-size:13px; }}
#controls QPushButton#pill:hover {{ background:{SURFACE_HOVER}; border-color:#3c3c48; }}
#controls QPushButton#pill:pressed {{ background:{SURFACE_PRESSED}; }}
#controls QPushButton#pill[badge="true"] {{ padding-right:40px; }}

/* grupo segmentado: um trilho com os botões irmãos dentro */
#controls QFrame#segment {{ background:{SURFACE}; border:1px solid {BORDER}; border-radius:11px; }}
#controls QFrame#segment QPushButton, #controls QFrame#segment QToolButton {{ background:transparent;
    color:{TEXT}; border:none; border-radius:8px; padding:0 11px; min-height:28px; max-height:28px;
    font-size:13px; }}
#controls QFrame#segment QPushButton:hover, #controls QFrame#segment QToolButton:hover {{
    background:{SURFACE_HOVER}; }}
#controls QFrame#segment QPushButton:pressed, #controls QFrame#segment QToolButton:pressed {{
    background:{SURFACE_PRESSED}; }}
#controls QFrame#segment QPushButton:checked {{ background:{ACCENT}; color:#111; font-weight:600; }}
#controls QFrame#segment QPushButton:checked:hover {{ background:{ACCENT_HOVER}; }}
#controls QFrame#segment QToolButton#step {{ font-size:17px; padding:0; min-width:28px; max-width:28px;
    color:{MUTED}; }}
#controls QFrame#segment QToolButton#step:hover {{ color:{TEXT}; }}
#controls QFrame#segment QToolButton#sync {{ color:#c8c8d2; font-size:12px; padding:0 8px; }}

/* setinha dos botões com menu (desenhada pelo app, no lugar da do sistema) */
#controls QPushButton::menu-indicator {{ image:url({chevron}); subcontrol-position:right center;
    subcontrol-origin:padding; width:12px; height:12px; right:8px; }}
#controls QFrame#segment QPushButton[hasMenu="true"] {{ padding-right:26px; }}

/* selo do contador de palavras */
#controls QLabel#badge {{ background:{ACCENT}; color:#111; border-radius:9px; font-size:11px;
    font-weight:bold; padding:0 5px; min-width:8px; }}

#controls QToolButton#help {{ background:{SURFACE}; border:1px solid {BORDER}; border-radius:17px;
    color:{ACCENT}; font-weight:bold; font-size:15px; }}
#controls QToolButton#help:hover {{ background:{SURFACE_HOVER}; border-color:#4a4636; }}
#controls QToolButton#donate {{ background:{SURFACE}; border:1px solid {BORDER}; border-radius:17px;
    color:#ff7a8a; font-size:16px; }}
#controls QToolButton#donate:hover {{ background:#3a2228; border-color:#ff7a8a; }}

/* aviso de versão nova, no rodapé */
QPushButton#update {{ background:{ACCENT}; color:#111; border:none; border-radius:9px; padding:3px 12px;
    margin:0 10px 6px 0; font-size:12px; font-weight:bold; }}
QPushButton#update:hover {{ background:{ACCENT_HOVER}; }}

/* velocidade */
#controls QComboBox {{ background:{SURFACE}; color:{TEXT}; border:1px solid {BORDER}; border-radius:10px;
    padding:0 26px 0 12px; min-height:34px; max-height:34px; min-width:34px; font-size:13px; }}
#controls QComboBox:hover {{ background:{SURFACE_HOVER}; border-color:#3c3c48; }}
#controls QComboBox::drop-down {{ border:none; width:22px; subcontrol-position:right center; }}
#controls QComboBox::down-arrow {{ image:url({chevron}); width:12px; height:12px; }}
#controls QComboBox QAbstractItemView {{ background:{SURFACE}; color:{TEXT}; border:1px solid {BORDER};
    selection-background-color:{ACCENT}; selection-color:#111; outline:0; padding:4px; }}

/* barras: tempo e volume */
#controls QSlider::groove:horizontal {{ height:5px; background:#34343e; border-radius:2px; }}
#controls QSlider::sub-page:horizontal {{ background:{ACCENT}; border-radius:2px; }}
#controls QSlider::handle:horizontal {{ background:#ffffff; width:14px; height:14px; margin:-5px 0;
    border-radius:7px; border:2px solid {ACCENT}; }}
#controls QSlider::handle:horizontal:hover {{ background:{ACCENT}; }}

QToolTip {{ background:{SURFACE}; color:{TEXT}; border:1px solid #3a3a46; padding:5px 9px; border-radius:6px; }}

QMenu {{ background:{SURFACE}; color:{TEXT}; border:1px solid #3a3a46; padding:5px; border-radius:8px; }}
QMenu::item {{ padding:8px 22px; border-radius:6px; }}
QMenu::item:selected {{ background:{ACCENT}; color:#111; }}
QMenu::item:disabled {{ color:{DIM}; background:transparent; }}
QMenu::separator {{ height:1px; background:#34343e; margin:5px 8px; }}
QMenu::right-arrow {{ image:url({chevron_dark}); }}
QStatusBar {{ background:{BG}; color:{TEXT}; font-size:14px; padding:2px 8px; }}
QStatusBar::item {{ border:none; }}
"""


DIALOG_STYLE = f"""
QDialog {{ background:{BAR}; }}
QLabel {{ color:{TEXT}; font-size:13px; }}
QTableWidget {{ background:#1c1c22; color:{TEXT}; border:1px solid #26262e; border-radius:10px; font-size:13px;
    selection-background-color:{ACCENT}; selection-color:#111; outline:0; }}
QTableWidget::item {{ padding:6px; border-bottom:1px solid #26262e; }}
QTableWidget::item:selected, QTableWidget::item:selected:focus {{ background:{ACCENT}; color:#111; border:none; }}
QTableWidget::item:focus {{ border:none; outline:none; }}
QHeaderView::section {{ background:{SURFACE}; color:{MUTED}; border:none; padding:7px; }}
QPushButton {{ background:{SURFACE}; color:{TEXT}; border:1px solid {BORDER}; border-radius:10px;
    padding:0 16px; min-height:34px; }}
QPushButton:hover {{ background:{SURFACE_HOVER}; border-color:#3c3c48; }}
QPushButton:pressed {{ background:{SURFACE_PRESSED}; }}
QPushButton:disabled {{ color:{DIM}; border-color:#26262e; }}
QPushButton#primary {{ background:{ACCENT}; color:#111; border-color:{ACCENT}; font-weight:bold; }}
QPushButton#primary:hover {{ background:{ACCENT_HOVER}; }}
QPushButton#primary:pressed {{ background:{ACCENT_PRESSED}; }}
QPushButton#primary:disabled {{ background:{SURFACE}; color:{DIM}; border-color:#26262e; font-weight:normal; }}
QTextBrowser {{ background:#1c1c22; border:1px solid #26262e; border-radius:10px; padding:10px;
    selection-background-color:{ACCENT}; selection-color:#111; }}
QScrollBar:vertical {{ background:transparent; width:12px; margin:2px; }}
QScrollBar::handle:vertical {{ background:#3a3a46; border-radius:5px; min-height:30px; }}
QScrollBar::handle:vertical:hover {{ background:#4a4a58; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height:0; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background:transparent; }}
QTabWidget::pane {{ border:none; top:8px; }}
QTabBar::tab {{ background:{SURFACE}; color:{MUTED}; padding:8px 18px; border-radius:8px; margin-right:6px; }}
QTabBar::tab:selected {{ background:{ACCENT}; color:#111; }}
QTabBar::tab:hover:!selected {{ background:{SURFACE_HOVER}; color:{TEXT}; }}
"""
