# gui/clientes_dialog.py
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget,
    QTableWidgetItem, QPushButton, QMessageBox,
    QFormLayout, QLineEdit, QComboBox, QLabel
)
from PySide6.QtCore import QRegularExpression
from PySide6.QtGui import QRegularExpressionValidator

from db import SessionLocal
from models import Cliente
from .pedidos_dialog import (
    HistorialClienteDialog,
    COMUNAS_SANTIAGO,
    crear_validador_telefono,
    configurar_combo_comuna,
)


class EditClienteDialog(QDialog):
    """Diálogo para editar datos de un cliente."""

    def __init__(self, cliente, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Editar cliente")
        self.resize(400, 250)
        self._cliente = cliente

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.ed_nombre = QLineEdit(cliente.nombre or "")
        self.ed_telefono = QLineEdit(cliente.telefono or "")
        self.ed_telefono.setValidator(crear_validador_telefono(self))
        self.ed_correo = QLineEdit(cliente.correo or "")
        self.ed_direccion = QLineEdit(cliente.direccion or "")

        self.cb_comuna = QComboBox()
        configurar_combo_comuna(self.cb_comuna, cliente.comuna or None)

        form.addRow("Nombre:", self.ed_nombre)
        form.addRow("Teléfono:", self.ed_telefono)
        form.addRow("Correo:", self.ed_correo)
        form.addRow("Dirección:", self.ed_direccion)
        form.addRow("Comuna:", self.cb_comuna)

        layout.addLayout(form)

        hb = QHBoxLayout()
        hb.addStretch()
        btn_ok = QPushButton("Guardar")
        btn_cancel = QPushButton("Cancelar")
        hb.addWidget(btn_ok)
        hb.addWidget(btn_cancel)
        layout.addLayout(hb)

        btn_ok.clicked.connect(self.guardar)
        btn_cancel.clicked.connect(self.reject)

    def guardar(self):
        nombre = self.ed_nombre.text().strip()
        if not nombre:
            QMessageBox.warning(self, "Editar cliente", "El nombre no puede estar vacío.")
            return

        self._cliente.nombre = nombre
        self._cliente.telefono = self.ed_telefono.text().strip() or None
        self._cliente.correo = self.ed_correo.text().strip() or None
        self._cliente.direccion = self.ed_direccion.text().strip() or None
        comuna_txt = self.cb_comuna.currentText().strip()
        self._cliente.comuna = comuna_txt or None

        self.accept()


class ClientesDialog(QDialog):
    """Listado y gestión de clientes."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Clientes - Raíz Diseño")
        self.resize(800, 450)

        layout = QVBoxLayout(self)

        # ---- Barra de búsqueda ----
        search_layout = QHBoxLayout()
        lbl_buscar = QLabel("Buscar cliente:")
        self.ed_buscar_cliente = QLineEdit()
        self.ed_buscar_cliente.setPlaceholderText("Nombre del cliente...")
        self.btn_buscar_cliente = QPushButton("Buscar")
        self.btn_limpiar_cliente = QPushButton("Limpiar")
        search_layout.addWidget(lbl_buscar)
        search_layout.addWidget(self.ed_buscar_cliente)
        search_layout.addWidget(self.btn_buscar_cliente)
        search_layout.addWidget(self.btn_limpiar_cliente)
        layout.addLayout(search_layout)

        # ---- Tabla ----
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            ["ID", "Nombre", "Teléfono", "Correo", "Dirección", "Comuna"]
        )
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.table)

        # ---- Botones ----
        hb = QHBoxLayout()
        self.btn_add = QPushButton("Nuevo cliente")
        self.btn_edit = QPushButton("Editar")
        self.btn_delete = QPushButton("Eliminar")
        self.btn_historial = QPushButton("Ver historial")
        self.btn_close = QPushButton("Cerrar")

        hb.addWidget(self.btn_add)
        hb.addWidget(self.btn_edit)
        hb.addWidget(self.btn_delete)
        hb.addWidget(self.btn_historial)
        hb.addStretch()
        hb.addWidget(self.btn_close)
        layout.addLayout(hb)

        # Conexión de señales
        self.btn_add.clicked.connect(self.add_cliente)
        self.btn_edit.clicked.connect(self.edit_cliente)
        self.btn_delete.clicked.connect(self.delete_cliente)
        self.btn_historial.clicked.connect(self.ver_historial)
        self.btn_close.clicked.connect(self.accept)

        self.btn_buscar_cliente.clicked.connect(self.aplicar_busqueda_clientes)
        self.btn_limpiar_cliente.clicked.connect(self.limpiar_busqueda_clientes)
        self.ed_buscar_cliente.returnPressed.connect(self.aplicar_busqueda_clientes)

        # Datos en memoria para búsqueda
        self._datos_clientes = []
        self.cargar()

    # -------------------------------------------------
    # Rellenar tabla desde una lista de dicts
    # -------------------------------------------------
    def _llenar_tabla(self, datos):
        self.table.setRowCount(len(datos))
        for row, d in enumerate(datos):
            self.table.setItem(row, 0, QTableWidgetItem(str(d["id"])))
            self.table.setItem(row, 1, QTableWidgetItem(d["nombre"] or ""))
            self.table.setItem(row, 2, QTableWidgetItem(d["telefono"] or ""))
            self.table.setItem(row, 3, QTableWidgetItem(d["correo"] or ""))
            self.table.setItem(row, 4, QTableWidgetItem(d["direccion"] or ""))
            self.table.setItem(row, 5, QTableWidgetItem(d["comuna"] or ""))
        self.table.resizeColumnsToContents()

    # -------------------------------------------------
    # Utilidad: obtener id del cliente seleccionado
    # -------------------------------------------------
    def _cliente_seleccionado_id(self):
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        if not item:
            return None
        try:
            return int(item.text())
        except ValueError:
            return None

    # -------------------------------------------------
    # Crear cliente (pide TODOS los datos)
    # -------------------------------------------------
    def add_cliente(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Nuevo cliente")
        dlg.resize(400, 250)

        vbox = QVBoxLayout(dlg)
        form = QFormLayout()

        ed_nombre = QLineEdit()

        ed_telefono = QLineEdit()
        ed_telefono.setValidator(crear_validador_telefono(dlg))

        ed_correo = QLineEdit()
        ed_direccion = QLineEdit()

        cb_comuna = QComboBox()
        configurar_combo_comuna(cb_comuna)

        form.addRow("Nombre:", ed_nombre)
        form.addRow("Teléfono:", ed_telefono)
        form.addRow("Correo:", ed_correo)
        form.addRow("Dirección:", ed_direccion)
        form.addRow("Comuna:", cb_comuna)

        vbox.addLayout(form)

        hb = QHBoxLayout()
        hb.addStretch()
        btn_ok = QPushButton("Guardar")
        btn_cancel = QPushButton("Cancelar")
        hb.addWidget(btn_ok)
        hb.addWidget(btn_cancel)
        vbox.addLayout(hb)

        btn_ok.clicked.connect(dlg.accept)
        btn_cancel.clicked.connect(dlg.reject)

        if dlg.exec() != QDialog.Accepted:
            return

        nombre = ed_nombre.text().strip()
        telefono = ed_telefono.text().strip() or None
        correo = ed_correo.text().strip() or None
        direccion = ed_direccion.text().strip() or None
        comuna = cb_comuna.currentText().strip() or None

        if not nombre:
            QMessageBox.warning(self, "Nuevo cliente", "El nombre no puede estar vacío.")
            return

        session = SessionLocal()
        try:
            c = Cliente(
                nombre=nombre,
                telefono=telefono,
                correo=correo,
                direccion=direccion,
                comuna=comuna,
            )
            session.add(c)
            session.commit()
        except Exception as exc:
            session.rollback()
            QMessageBox.critical(self, "Error", str(exc))
        finally:
            session.close()

        self.cargar()

    # -------------------------------------------------
    # Editar cliente
    # -------------------------------------------------
    def edit_cliente(self):
        cliente_id = self._cliente_seleccionado_id()
        if not cliente_id:
            QMessageBox.information(
                self, "Editar", "Selecciona un cliente para editar."
            )
            return

        session = SessionLocal()
        try:
            cliente = session.query(Cliente).get(cliente_id)
            if not cliente:
                QMessageBox.warning(self, "Editar", "Cliente no encontrado.")
                return

            dlg = EditClienteDialog(cliente, self)
            if dlg.exec() == QDialog.Accepted:
                try:
                    session.commit()
                except Exception as exc:
                    session.rollback()
                    QMessageBox.critical(self, "Error", str(exc))
        finally:
            session.close()

        self.cargar()

    # -------------------------------------------------
    # Eliminar cliente
    # -------------------------------------------------
    def delete_cliente(self):
        cliente_id = self._cliente_seleccionado_id()
        if not cliente_id:
            QMessageBox.information(
                self, "Eliminar", "Selecciona un cliente para eliminar."
            )
            return

        r = QMessageBox.question(
            self,
            "Eliminar",
            "¿Eliminar este cliente? (No se eliminan los pedidos ya registrados)",
        )
        if r != QMessageBox.Yes:
            return

        session = SessionLocal()
        try:
            cliente = session.query(Cliente).get(cliente_id)
            if cliente:
                session.delete(cliente)
                session.commit()
        except Exception as exc:
            session.rollback()
            QMessageBox.critical(self, "Error", str(exc))
        finally:
            session.close()

        self.cargar()

    # -------------------------------------------------
    # Cargar tabla de clientes
    # -------------------------------------------------
    def cargar(self):
        session = SessionLocal()
        try:
            clientes = session.query(Cliente).order_by(Cliente.id).all()
            self._datos_clientes = []
            for c in clientes:
                self._datos_clientes.append({
                    "id": c.id,
                    "nombre": c.nombre or "",
                    "telefono": c.telefono or "",
                    "correo": c.correo or "",
                    "direccion": c.direccion or "",
                    "comuna": c.comuna or "",
                })
        finally:
            session.close()

        self.ed_buscar_cliente.clear()
        self._llenar_tabla(self._datos_clientes)

    # -------------------------------------------------
    # Búsqueda por nombre de cliente
    # -------------------------------------------------
    def aplicar_busqueda_clientes(self):
        texto = self.ed_buscar_cliente.text().strip().lower()
        if not texto:
            self._llenar_tabla(self._datos_clientes)
            return

        filtrados = []
        for d in self._datos_clientes:
            if texto in (d["nombre"] or "").lower():
                filtrados.append(d)

        self._llenar_tabla(filtrados)

    def limpiar_busqueda_clientes(self):
        self.ed_buscar_cliente.clear()
        self._llenar_tabla(self._datos_clientes)

    # -------------------------------------------------
    # Ver historial de compras del cliente
    # -------------------------------------------------
    def ver_historial(self):
        cliente_id = self._cliente_seleccionado_id()
        if not cliente_id:
            QMessageBox.information(
                self, "Historial", "Selecciona un cliente para ver el historial."
            )
            return
        dlg = HistorialClienteDialog(cliente_id, self)
        dlg.exec()
