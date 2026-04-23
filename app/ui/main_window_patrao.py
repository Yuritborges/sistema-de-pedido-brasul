from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QMainWindow
from app.ui.widgets.consulta_patrao_widget import ConsultaPatraoWidget
import os


class MainWindowPatrao(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Brasul Consulta Gerencial")
        self.resize(1500, 900)

        icon_path = os.path.join("assets", "iconebrasul2.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.setStyleSheet("""
            QMainWindow {
                background: #f3f5f8;
            }
        """)

        self.setCentralWidget(ConsultaPatraoWidget())