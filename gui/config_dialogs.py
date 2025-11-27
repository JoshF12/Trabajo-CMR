# gui/config_dialogs.py
import os
import sys

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QHBoxLayout,
    QLineEdit, QPushButton, QFileDialog, QMessageBox
)

from config import load_settings, save_settings, get_backup_folder


class ConfigInicialDialog(QDialog):
    """Diálogo para elegir carpeta de respaldo de la base de datos."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configuración de respaldo - Raíz Diseño")
        self.resize(500, 180)

        layout = QVBoxLayout(self)
        txt = QLabel(
            "Selecciona la carpeta donde se guardarán los respaldos "
            "de la base de datos (idealmente una carpeta de OneDrive)."
        )
        txt.setWordWrap(True)
        layout.addWidget(txt)

        hl = QHBoxLayout()
        self.ed_folder = QLineEdit()
        self.btn_browse = QPushButton("Buscar carpeta")
        hl.addWidget(self.ed_folder)
        hl.addWidget(self.btn_browse)
        layout.addLayout(hl)

        btns = QHBoxLayout()
        btns.addStretch()
        self.btn_ok = QPushButton("Guardar")
        self.btn_cancel = QPushButton("Cancelar")
        btns.addWidget(self.btn_ok)
        btns.addWidget(self.btn_cancel)
        layout.addLayout(btns)

        self.btn_browse.clicked.connect(self._browse)
        self.btn_ok.clicked.connect(self.accept)
        self.btn_cancel.clicked.connect(self.reject)

        # Si ya hay una carpeta, mostrarla
        actual = get_backup_folder()
        if actual:
            self.ed_folder.setText(actual)

    def _browse(self):
        carpeta = QFileDialog.getExistingDirectory(
            self, "Elegir carpeta de respaldo", ""
        )
        if carpeta:
            self.ed_folder.setText(carpeta)

    def get_folder(self) -> str:
        return self.ed_folder.text().strip()


def ensure_initial_config(parent=None):
    """Se asegura de que exista una carpeta de backup configurada,
    si no, muestra el diálogo y obliga a elegir una.
    """
    folder = get_backup_folder()
    if folder and os.path.isdir(folder):
        return

    dlg = ConfigInicialDialog(parent)
    while True:
        res = dlg.exec()
        if res != QDialog.Accepted:
            QMessageBox.warning(
                parent,
                "Configuración requerida",
                "Debes seleccionar una carpeta de respaldo para continuar."
            )
            sys.exit(0)

        folder = dlg.get_folder()
        if not folder:
            QMessageBox.warning(parent, "Error", "Debes elegir una carpeta válida.")
            continue

        if not os.path.isdir(folder):
            try:
                os.makedirs(folder, exist_ok=True)
            except Exception as exc:
                QMessageBox.critical(
                    parent,
                    "Error al crear carpeta",
                    str(exc)
                )
                continue

        settings = load_settings()
        settings["backup_folder"] = folder
        save_settings(settings)
        break


def change_backup_folder(parent=None):
    """Permite cambiar la carpeta de backup desde el menú Configuración."""
    dlg = ConfigInicialDialog(parent)
    res = dlg.exec()
    if res != QDialog.Accepted:
        return False

    folder = dlg.get_folder()
    if not folder:
        QMessageBox.warning(parent, "Error", "Debes elegir una carpeta válida.")
        return False

    if not os.path.isdir(folder):
        try:
            os.makedirs(folder, exist_ok=True)
        except Exception as exc:
            QMessageBox.critical(
                parent, "Error al crear carpeta", str(exc)
            )
            return False

    settings = load_settings()
    settings["backup_folder"] = folder
    save_settings(settings)
    QMessageBox.information(parent, "Configuración", "Carpeta de respaldo actualizada.")
    return True
