"""app/ui/widgets/historico_widget.py — Placeholder Sprint 2"""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt

class HistoricoWidget(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        lbl = QLabel("Histórico de Pedidos\n\nEm construção — Sprint 2")
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet("font-size: 18px; color: #556080;")
        layout.addWidget(lbl)
