# main.py
import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont
from PySide6.QtCore import QSettings

from gui.config_dialogs import ensure_initial_config
from gui.main_window import MainWindow
from init_db import init_db
from backup import restaurar_si_no_existe

APP_ORG = "RaizDiseno"
APP_NAME = "CRM PyME"


def aplicar_zoom(app: QApplication, zoom: int):
    """
    Aplica el zoom a toda la aplicación modificando el tamaño de la fuente.
    zoom = 100 → tamaño normal
    zoom = 110 → 10% más grande
    zoom = 90  → 10% más pequeño
    """
    # Tamaño base que usas normalmente (ajusta si quieres)
    base_point_size = 9

    font = app.font()
    font.setPointSize(int(base_point_size * zoom / 100))
    app.setFont(font)


def main():
    app = QApplication(sys.argv)

    # QSettings para recordar preferencia de zoom
    settings_qt = QSettings(APP_ORG, APP_NAME)

    # Leer zoom guardado (por defecto 100%)
    zoom_guardado = settings_qt.value("ui/zoom", 100, type=int)
    aplicar_zoom(app, zoom_guardado)

    # 1) Asegurar configuración inicial (carpeta de backup, etc.)
    ensure_initial_config()

    # 2) Intentar restaurar la BD desde backup si no existe
    restaurar_si_no_existe()

    # 3) Asegurar que la base de datos y las tablas existan
    init_db()

    # 4) Lanzar ventana principal, pasando settings y función de zoom
    window = MainWindow(
        settings=settings_qt,
        apply_zoom_fn=lambda z: aplicar_zoom(app, z)
    )
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
