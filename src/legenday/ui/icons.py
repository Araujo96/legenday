"""Ícones desenhados em código (vetoriais, nítidos em qualquer tela)."""
import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap, QPolygonF


def _poly(*pts):
    return QPolygonF([QPointF(x, y) for x, y in pts])


def make_icon(kind: str, color: str = "#e8e8ee", size: int = 64) -> QIcon:
    """Desenha ícones vetoriais (grade 24x24), nítidos em qualquer tela."""
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.scale(size / 24, size / 24)
    c = QColor(color)
    p.setBrush(c)
    p.setPen(Qt.NoPen)
    if kind == "play":
        p.drawPolygon(_poly((7, 4), (20, 12), (7, 20)))
    elif kind == "pause":
        p.drawRoundedRect(QRectF(6, 4, 4, 16), 1, 1)
        p.drawRoundedRect(QRectF(14, 4, 4, 16), 1, 1)
    elif kind == "back":
        p.drawPolygon(_poly((12, 12), (21, 5), (21, 19)))
        p.drawPolygon(_poly((3, 12), (12, 5), (12, 19)))
    elif kind == "fwd":
        p.drawPolygon(_poly((12, 12), (3, 5), (3, 19)))
        p.drawPolygon(_poly((21, 12), (12, 5), (12, 19)))
    elif kind == "prev":
        p.drawRect(QRectF(4, 5, 3, 14))
        p.drawPolygon(_poly((20, 5), (20, 19), (8, 12)))
    elif kind == "next":
        p.drawRect(QRectF(17, 5, 3, 14))
        p.drawPolygon(_poly((4, 5), (4, 19), (16, 12)))
    elif kind == "folder":
        p.drawPolygon(_poly((3, 6), (10, 6), (12, 8.5), (21, 8.5), (21, 19), (3, 19)))
    elif kind == "subs":
        pen = QPen(c, 1.8)
        pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(QRectF(3, 5, 18, 14), 3, 3)
        p.drawLine(QPointF(7, 10.5), QPointF(12, 10.5))
        p.drawLine(QPointF(14, 10.5), QPointF(17, 10.5))
        p.drawLine(QPointF(7, 14.5), QPointF(10, 14.5))
        p.drawLine(QPointF(12, 14.5), QPointF(17, 14.5))
    elif kind == "volume":
        p.drawPolygon(_poly((3, 9), (7, 9), (12, 5), (12, 19), (7, 15), (3, 15)))
        pen = QPen(c, 1.8)
        pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        p.drawArc(QRectF(9, 8, 8, 8), -50 * 16, 100 * 16)
        p.drawArc(QRectF(7, 5, 14, 14), -50 * 16, 100 * 16)
    elif kind == "volume_off":                   # alto-falante com um X: mudo
        p.drawPolygon(_poly((3, 9), (7, 9), (12, 5), (12, 19), (7, 15), (3, 15)))
        pen = QPen(c, 1.9)
        pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen)
        p.drawLine(QPointF(15.5, 9.5), QPointF(20.5, 14.5))
        p.drawLine(QPointF(20.5, 9.5), QPointF(15.5, 14.5))
    elif kind == "sync":                         # relógio: o tempo da legenda
        pen = QPen(c, 1.9)
        pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(QPointF(12, 12), 8, 8)
        p.drawLine(QPointF(12, 12), QPointF(12, 7.5))
        p.drawLine(QPointF(12, 12), QPointF(15, 14))
    elif kind == "chevron":                      # setinha dos menus
        pen = QPen(c, 2.4)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        p.drawPolyline(_poly((6, 9.5), (12, 15.5), (18, 9.5)))
    elif kind == "audio":
        pen = QPen(c, 2)
        pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        p.drawArc(QRectF(4.5, 3.5, 15, 15), 0, 180 * 16)
        p.setPen(Qt.NoPen)
        p.setBrush(c)
        p.drawRoundedRect(QRectF(3, 11, 4.5, 8.5), 2, 2)
        p.drawRoundedRect(QRectF(16.5, 11, 4.5, 8.5), 2, 2)
    elif kind == "star":
        pts = []
        for i in range(10):
            r = 10 if i % 2 == 0 else 4.4
            a = -math.pi / 2 + i * math.pi / 5
            pts.append((12 + r * math.cos(a), 12.5 + r * math.sin(a)))
        p.drawPolygon(_poly(*pts))
    elif kind == "list":
        for y in (6, 12, 18):
            p.drawEllipse(QPointF(5, y), 1.8, 1.8)
            p.drawRoundedRect(QRectF(9, y - 1.5, 12, 3), 1.5, 1.5)
    elif kind == "repeat":                       # balão de fala com seta circular: "repita a frase"
        pen = QPen(c, 2)
        pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        p.drawArc(QRectF(4, 4, 16, 16), 40 * 16, 280 * 16)
        p.setPen(Qt.NoPen)
        p.setBrush(c)
        p.drawPolygon(_poly((15.5, 2.2), (21.5, 5.2), (15.8, 8.6)))
        p.drawEllipse(QPointF(12, 12), 2.2, 2.2)
    elif kind == "dual":                         # duas linhas de legenda, a de baixo mais curta
        p.drawRoundedRect(QRectF(3, 7, 18, 3.4), 1.7, 1.7)
        c2 = QColor(c)
        c2.setAlphaF(0.55)
        p.setBrush(c2)
        p.drawRoundedRect(QRectF(6, 14, 12, 3.4), 1.7, 1.7)
    elif kind == "cards":                        # cartões de revisão empilhados
        pen = QPen(c, 1.8)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(QRectF(7, 4, 13, 10), 2, 2)
        p.setBrush(c)
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(QRectF(4, 9, 13, 11), 2, 2)
    p.end()
    return QIcon(pm)


def toggle_icon(kind: str) -> QIcon:
    """Ícone de botão liga/desliga: claro quando desligado, escuro sobre o amarelo quando ligado."""
    icon = make_icon(kind)
    icon.addPixmap(make_icon(kind, "#111").pixmap(64, 64), QIcon.Normal, QIcon.On)
    return icon


def icon_file(kind: str, color: str = "#9a9aa6", size: int = 32) -> str:
    """Grava o ícone como PNG numa pasta temporária e devolve o caminho (o QSS só aceita imagens de arquivo,
    por exemplo a setinha dos menus e da caixa de velocidade)."""
    import tempfile
    from pathlib import Path

    folder = Path(tempfile.gettempdir()) / "legenday-ui"
    folder.mkdir(exist_ok=True)
    path = folder / f"{kind}-{color.strip('#')}-{size}.png"
    if not path.exists():
        make_icon(kind, color, size).pixmap(size, size).save(str(path))
    return path.as_posix()
