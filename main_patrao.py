import sys
from PySide6.QtWidgets import QApplication
from app.ui.main_window_patrao import MainWindowPatrao


def main():
    app = QApplication(sys.argv)
    win = MainWindowPatrao()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()