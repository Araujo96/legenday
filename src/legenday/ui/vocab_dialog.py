"""Janela do vocabulário salvo: lista, exclusão e exportação para o Anki."""
from pathlib import Path

from PySide6.QtCore import QStandardPaths, Qt, Signal
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from legenday.ui.style import DIALOG_STYLE


class VocabDialog(QDialog):
    changed = Signal()

    def __init__(self, vocab, parent=None, on_review=None):
        super().__init__(parent)
        self.vocab = vocab
        self.on_review = on_review          # abre a revisão (a janela principal sabe tocar as cenas)
        self.setWindowTitle("Vocabulário")
        self.resize(820, 480)
        self.setStyleSheet(DIALOG_STYLE)

        lay = QVBoxLayout(self)
        self.info = QLabel()
        lay.addWidget(self.info)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Palavra", "Tradução", "Frase do filme"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setWordWrap(True)
        self.table.setShowGrid(False)
        head = self.table.horizontalHeader()
        head.setSectionResizeMode(0, QHeaderView.Interactive)
        head.setSectionResizeMode(1, QHeaderView.Interactive)
        head.setSectionResizeMode(2, QHeaderView.Stretch)
        pal = self.table.palette()  # texto escuro sobre o amarelo da seleção, em qualquer estado/célula
        pal.setColor(QPalette.Highlight, QColor("#ffd54a"))
        pal.setColor(QPalette.HighlightedText, QColor("#111111"))
        self.table.setPalette(pal)
        self.table.setColumnWidth(0, 170)
        self.table.setColumnWidth(1, 220)
        lay.addWidget(self.table, 1)

        row = QHBoxLayout()
        self.btn_review = QPushButton("Revisar")
        self.btn_review.setObjectName("primary")          # botão principal, em amarelo (estilo em style.py)
        self.btn_review.clicked.connect(self.review)
        row.addWidget(self.btn_review)
        self.btn_export = QPushButton("Exportar para o Anki…")
        self.btn_export.clicked.connect(self.export)
        self.btn_delete = QPushButton("Excluir selecionadas")
        self.btn_delete.clicked.connect(self.delete_selected)
        close = QPushButton("Fechar")
        close.clicked.connect(self.accept)
        for b in (self.btn_export, self.btn_delete):
            row.addWidget(b)
        row.addStretch()
        row.addWidget(close)
        lay.addLayout(row)
        self.reload()

    def reload(self):
        words = self.vocab.all()
        self.table.setRowCount(len(words))
        for r, w in enumerate(words):
            term = w.term + (f"  ({w.lemma})" if w.lemma and w.lemma != w.term.lower() else "")
            for c, text in enumerate((term, w.translation, w.sentence)):
                item = QTableWidgetItem(text)
                item.setData(Qt.UserRole, w.id)
                self.table.setItem(r, c, item)
        self.table.resizeRowsToContents()
        n = len(words)
        self.info.setText(f"{n} palavra(s) salva(s)" if n else
                          "Nenhuma palavra salva ainda. Clique numa palavra da legenda e use “Salvar no vocabulário”.")
        self.btn_export.setEnabled(n > 0)
        self.btn_delete.setEnabled(n > 0)
        due = self.vocab.due_count()
        self.btn_review.setText(f"Revisar ({due})" if due else "Revisar")
        self.btn_review.setToolTip("Cartões com as palavras que estão no dia de revisar" if due else
                                   "Nada para revisar agora: as palavras voltam no dia certo")
        self.btn_review.setEnabled(n > 0 and self.on_review is not None)

    def review(self):
        if self.on_review is not None:
            self.on_review(self)
            self.reload()
            self.changed.emit()

    def delete_selected(self):
        ids = {self.table.item(i.row(), 0).data(Qt.UserRole) for i in self.table.selectedIndexes()}
        if not ids:
            QMessageBox.information(self, "Vocabulário", "Selecione as palavras que quer excluir.")
            return
        if QMessageBox.question(self, "Excluir", f"Excluir {len(ids)} palavra(s) do vocabulário?") == QMessageBox.Yes:
            self.vocab.delete(ids)
            self.reload()
            self.changed.emit()

    def export(self):
        # sugere a pasta Documentos (só o nome do arquivo faria o Windows salvar na pasta do programa)
        docs = QStandardPaths.writableLocation(QStandardPaths.DocumentsLocation) or str(Path.home())
        path, _ = QFileDialog.getSaveFileName(self, "Exportar para o Anki", str(Path(docs) / "legenday_anki.txt"),
                                              "Texto (*.txt)")
        if not path:
            return
        try:
            n = self.vocab.export_anki(path)
        except OSError as exc:
            QMessageBox.warning(self, "Exportar para o Anki", f"Não foi possível gravar o arquivo:\n{exc}")
            return
        QMessageBox.information(
            self, "Exportado",
            f"{n} palavra(s) exportada(s).\n\nNo Anki: Arquivo → Importar e escolha o arquivo. "
            "Os campos (frente, verso e tags) são reconhecidos automaticamente.")
