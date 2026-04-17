"""app/ui/widgets/cotacao_widget.py — Placeholder Sprint 3"""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt

class CotacaoWidget(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        lbl = QLabel("Módulo de Cotação\n\nEm construção — Sprint 3")
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet("font-size: 18px; color: #556080;")
        layout.addWidget(lbl)
