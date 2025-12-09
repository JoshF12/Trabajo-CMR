from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QLabel,
    QFileDialog,
    QMessageBox,
    QToolBar,
)
from PySide6.QtCore import Qt
    # noqa
from PySide6.QtGui import QAction, QIcon
import os

from import_excel import importar_excel
from backup import hacer_respaldo, importar_respaldo
from .clientes_dialog import ClientesDialog
from .pedidos_dialog import PedidosDialog
from .config_dialogs import change_backup_folder


class MainWindow(QMainWindow):
    def __init__(self, settings=None, apply_zoom_fn=None, parent=None):
        """
        settings: instancia de QSettings para guardar preferencias (zoom, etc.).
        apply_zoom_fn: función que aplica el zoom a la app (la pasa main.py).
        """
        super().__init__(parent)

        self.settings = settings
        self.apply_zoom_fn = apply_zoom_fn

        # ====== ICONO DE LA VENTANA ======
        # Ruta relativa: /gui/main_window.py → sube un nivel (..) → icon.png
        ruta_icono = os.path.join(os.path.dirname(__file__), "..", "icon.png")
        if os.path.exists(ruta_icono):
            self.setWindowIcon(QIcon(ruta_icono))
        # ================================

        # Zoom actual (por defecto 100%)
        if self.settings is not None:
            self.current_zoom = self.settings.value("ui/zoom", 100, type=int)
        else:
            self.current_zoom = 100

        self.setWindowTitle("CRM Raíz Diseño")
        self.resize(1000, 600)

        # ---- Contenido central simple ----
        central = QWidget(self)
        layout = QVBoxLayout(central)
        label = QLabel("CRM Raíz Diseño\nSelecciona una opción en el menú.", central)
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)
        self.setCentralWidget(central)

        # Crear menús, acciones y barra de herramientas
        self._create_actions()
        self._create_menus()
        self._create_toolbars()

    # ==========================
    # Menús y acciones
    # ==========================
    def _create_actions(self):
        # ----- Menú Archivo -----
        self.act_importar_excel = QAction("Importar desde Excel", self)
        self.act_importar_excel.triggered.connect(self.action_importar_excel)

        # NUEVO: importar respaldo .db
        self.act_importar_backup = QAction("Importar respaldo (.db)", self)
        self.act_importar_backup.triggered.connect(self.action_importar_backup)

        self.act_cambiar_carpeta = QAction("Cambiar carpeta de respaldo", self)
        self.act_cambiar_carpeta.triggered.connect(self.action_cambiar_carpeta)

        self.act_salir = QAction("Salir", self)
        self.act_salir.triggered.connect(self.close)

        # ----- Menú Gestión -----
        self.act_clientes = QAction("Clientes", self)
        self.act_clientes.triggered.connect(self.action_clientes)

        self.act_pedidos = QAction("Pedidos", self)
        self.act_pedidos.triggered.connect(self.action_pedidos)

        # ----- Menú Ver / Zoom -----
        self.act_zoom_mas = QAction("Aumentar zoom", self)
        self.act_zoom_mas.setShortcut("Ctrl++")
        self.act_zoom_mas.triggered.connect(self.zoom_in)

        self.act_zoom_menos = QAction("Disminuir zoom", self)
        self.act_zoom_menos.setShortcut("Ctrl+-")
        self.act_zoom_menos.triggered.connect(self.zoom_out)

        self.act_zoom_reset = QAction("Restablecer zoom", self)
        self.act_zoom_reset.setShortcut("Ctrl+0")
        self.act_zoom_reset.triggered.connect(self.zoom_reset)

    def _create_menus(self):
        menubar = self.menuBar()

        # ---- Menú Archivo ----
        menu_archivo = menubar.addMenu("Archivo")
        menu_archivo.addAction(self.act_importar_excel)
        menu_archivo.addAction(self.act_importar_backup)   # ← NUEVO
        menu_archivo.addAction(self.act_cambiar_carpeta)
        menu_archivo.addSeparator()
        menu_archivo.addAction(self.act_salir)

        # ---- Menú Gestión ----
        menu_gestion = menubar.addMenu("Gestión")
        menu_gestion.addAction(self.act_clientes)
        menu_gestion.addAction(self.act_pedidos)

        # ---- Menú Ver (Zoom) ----
        menu_ver = menubar.addMenu("Ver")
        menu_ver.addAction(self.act_zoom_mas)
        menu_ver.addAction(self.act_zoom_menos)
        menu_ver.addAction(self.act_zoom_reset)

    def _create_toolbars(self):
        """
        Crea una barra de herramientas con botones para controlar el zoom.
        """
        toolbar = QToolBar("Zoom", self)
        toolbar.setMovable(False)
        self.addToolBar(Qt.TopToolBarArea, toolbar)

        # Botón Aumentar zoom
        btn_zoom_mas = QAction("A+", self)
        btn_zoom_mas.setToolTip("Aumentar zoom")
        btn_zoom_mas.triggered.connect(self.zoom_in)
        toolbar.addAction(btn_zoom_mas)

        # Botón Disminuir zoom
        btn_zoom_menos = QAction("A−", self)
        btn_zoom_menos.setToolTip("Disminuir zoom")
        btn_zoom_menos.triggered.connect(self.zoom_out)
        toolbar.addAction(btn_zoom_menos)

        # Botón Reset zoom
        btn_zoom_reset = QAction("100%", self)
        btn_zoom_reset.setToolTip("Restablecer zoom a 100%")
        btn_zoom_reset.triggered.connect(self.zoom_reset)
        toolbar.addAction(btn_zoom_reset)

    # ==========================
    # Acciones de menú
    # ==========================
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

    def action_importar_backup(self):
        """Permite al usuario importar información desde un archivo .db de respaldo."""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar archivo de respaldo",
            "",
            "Base de datos SQLite (*.db);;Todos los archivos (*.*)",
        )
        if not path:
            return

        try:
            resultado = importar_respaldo(path)
            QMessageBox.information(
                self,
                "Importar respaldo",
                (
                    "Importación completada.\n\n"
                    f"Clientes nuevos: {resultado['clientes_nuevos']}\n"
                    f"Pedidos nuevos: {resultado['pedidos_nuevos']}\n"
                    f"Ítems nuevos: {resultado['items_nuevos']}"
                ),
            )
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Error",
                f"No se pudo importar el respaldo:\n{exc}",
            )

    def action_clientes(self):
        dlg = ClientesDialog(self)
        dlg.exec()

    def action_pedidos(self):
        dlg = PedidosDialog(self)
        dlg.exec()

    def action_cambiar_carpeta(self):
        change_backup_folder(self)

    # ==========================
    # Backup automático al cerrar
    # ==========================
    def closeEvent(self, event):
        try:
            hacer_respaldo()
        except Exception as exc:
            QMessageBox.warning(self, "Backup", f"No se pudo generar el respaldo al cerrar:\n{exc}")
        super().closeEvent(event)

    # ==========================
    # Lógica de ZOOM
    # ==========================
    def set_zoom(self, zoom: int):
        """
        Cambia el nivel de zoom, lo guarda y lo aplica a la aplicación.
        """
        # Limitamos el rango para que no se descontrole
        zoom = max(80, min(160, zoom))  # entre 80% y 160%

        self.current_zoom = zoom

        # Guardar en QSettings si está disponible
        if self.settings is not None:
            self.settings.setValue("ui/zoom", zoom)

        # Aplicar a la app completa (QApplication) mediante la función que nos pasa main.py
        if self.apply_zoom_fn is not None:
            self.apply_zoom_fn(zoom)

    def zoom_in(self):
        """Aumentar zoom (+10%)."""
        self.set_zoom(self.current_zoom + 10)

    def zoom_out(self):
        """Disminuir zoom (-10%)."""
        self.set_zoom(self.current_zoom - 10)

    def zoom_reset(self):
        """Restablecer zoom al 100%."""
        self.set_zoom(100)
