# gui/main_window.py
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QLabel,
    QFileDialog, QMessageBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction

from import_excel import importar_excel
from backup import hacer_respaldo
from .clientes_dialog import ClientesDialog
from .pedidos_dialog import PedidosDialog
from .config_dialogs import change_backup_folder


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CRM Raíz Diseño")
        self.resize(1000, 600)

        # ---- Contenido central ----
        central = QWidget(self)
        layout = QVBoxLayout(central)
        label = QLabel("CRM Raíz Diseño\nSelecciona una opción en el menú.", central)
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)
        self.setCentralWidget(central)

        self._create_actions()
        self._create_menus()

        # ❌ No se llama a _create_toolbar(), porque eliminamos la toolbar.

    # ---------------------------
    # Menús y acciones
    # ---------------------------
    def _create_actions(self):
        # Archivo
        self.act_importar_excel = QAction("Importar desde Excel", self)
        self.act_importar_excel.triggered.connect(self.action_importar_excel)

        self.act_cambiar_carpeta = QAction("Cambiar carpeta de respaldo", self)
        self.act_cambiar_carpeta.triggered.connect(self.action_cambiar_carpeta)

        self.act_salir = QAction("Salir", self)
        self.act_salir.triggered.connect(self.close)

        # Gestión
        self.act_clientes = QAction("Clientes", self)
        self.act_clientes.triggered.connect(self.action_clientes)

        self.act_pedidos = QAction("Pedidos", self)
        self.act_pedidos.triggered.connect(self.action_pedidos)

    def _create_menus(self):
        menubar = self.menuBar()

        # ---- Menú Archivo ----
        menu_archivo = menubar.addMenu("Archivo")
        menu_archivo.addAction(self.act_importar_excel)
        menu_archivo.addAction(self.act_cambiar_carpeta)
        menu_archivo.addSeparator()
        menu_archivo.addAction(self.act_salir)

        # ---- Menú Gestión ----
        menu_gestion = menubar.addMenu("Gestión")
        menu_gestion.addAction(self.act_clientes)
        menu_gestion.addAction(self.act_pedidos)

    # ---------------------------
    # Acciones
    # ---------------------------
    def action_importar_excel(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar archivo Excel",
            "",
            "Archivos Excel (*.xlsx *.xls);;Todos los archivos (*.*)",
        )
        if not path:
            return
        try:
            importar_excel(path)
            QMessageBox.information(self, "Importación", "Importación desde Excel completada.")
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"Error al importar Excel:\n{exc}")

    def action_clientes(self):
        dlg = ClientesDialog(self)
        dlg.exec()

    def action_pedidos(self):
        dlg = PedidosDialog(self)
        dlg.exec()

    def action_cambiar_carpeta(self):
        change_backup_folder(self)

    # ---------------------------
    # Backup automático al cerrar
    # ---------------------------
    def closeEvent(self, event):
        try:
            hacer_respaldo()
        except Exception as exc:
            QMessageBox.warning(self, "Backup", f"No se pudo generar el respaldo al cerrar:\n{exc}")
        super().closeEvent(event)
