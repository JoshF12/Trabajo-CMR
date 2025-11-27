# main.py
import sys
from PySide6.QtWidgets import QApplication

from gui.config_dialogs import ensure_initial_config
from gui.main_window import MainWindow
from init_db import init_db  # para asegurarnos de que existan tablas
from backup import restaurar_si_no_existe


def main():
    app = QApplication(sys.argv)

    # 1) Asegurar carpeta de respaldo (solo la primera vez preguntará)
    ensure_initial_config()

    # 2) Si la base de datos NO existe pero hay un backup, restaurar automáticamente
    restaurar_si_no_existe()

    # 3) Asegurar que la base de datos SQLite y las tablas existan
    init_db()

    # 4) Lanzar ventana principal
    win = MainWindow()
    win.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
