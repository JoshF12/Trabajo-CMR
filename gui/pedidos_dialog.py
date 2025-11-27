# gui/pedidos_dialog.py
from datetime import datetime

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget,
    QTableWidgetItem, QPushButton, QMessageBox,
    QFormLayout, QComboBox, QDateEdit, QLineEdit, QLabel
)
from PySide6.QtCore import Qt, QDate, QRegularExpression
from PySide6.QtGui import QRegularExpressionValidator

from db import SessionLocal
from models import Cliente, Pedido, ItemPedido


# ===================================================
# ========== UTILIDADES COMUNAS Y VALIDADORES ========
# ===================================================

COMUNAS_SANTIAGO = [
    "Santiago",
    "Cerrillos",
    "Cerro Navia",
    "Conchalí",
    "El Bosque",
    "Estación Central",
    "Huechuraba",
    "Independencia",
    "La Cisterna",
    "La Florida",
    "La Granja",
    "La Pintana",
    "La Reina",
    "Las Condes",
    "Lo Barnechea",
    "Lo Espejo",
    "Lo Prado",
    "Macul",
    "Maipú",
    "Ñuñoa",
    "Pedro Aguirre Cerda",
    "Peñalolén",
    "Providencia",
    "Pudahuel",
    "Quilicura",
    "Quinta Normal",
    "Recoleta",
    "Renca",
    "San Joaquín",
    "San Miguel",
    "San Ramón",
    "Vitacura",
]


ESTADOS_PEDIDO = [
    "Pendiente",
    "Preparación",
    "Listo para despacho",
    "En despacho",
    "Entregado",
    "Cancelado",
]


def crear_validador_telefono(parent=None):
    """
    Solo permite dígitos 0-9 (vacío también es válido).
    """
    regex = QRegularExpression(r"^[0-9]*$")
    return QRegularExpressionValidator(regex, parent)


def configurar_combo_comuna(combo, valor_actual=None):
    """
    Deja el combo editable con una lista base de comunas de Santiago
    pero permitiendo escribir otras (para regiones).
    """
    combo.setEditable(True)
    combo.clear()
    for c in COMUNAS_SANTIAGO:
        combo.addItem(c)
    if valor_actual:
        combo.setCurrentText(valor_actual)
    else:
        combo.setCurrentIndex(-1)


# ===================================================
# ========== GENERACIÓN NÚMERO DE PEDIDO ============
# ===================================================

def _generar_codigo_pedido(fecha, correlativo):
    """
    Genera un código del tipo PYYYYMMDD-XXX.
    """
    return "P" + fecha.strftime("%Y%m%d") + f"-{correlativo:03d}"


def generar_numero_pedido_db(session, fecha=None):
    """
    Genera un número de pedido único consultando la BD.
    Busca el último número del día y suma 1.
    """
    if fecha is None:
        fecha = datetime.now()

    prefijo = "P" + fecha.strftime("%Y%m%d")

    ultimo = (
        session.query(Pedido)
        .filter(Pedido.numero_pedido.like(f"{prefijo}-%"))
        .order_by(Pedido.numero_pedido.desc())
        .first()
    )

    if not ultimo:
        correlativo = 1
    else:
        try:
            parte_final = ultimo.numero_pedido.split("-")[-1]
            correlativo = int(parte_final) + 1
        except Exception:
            correlativo = 1

    return _generar_codigo_pedido(fecha, correlativo)


# ===================================================
# ================ ITEMS DEL PEDIDO =================
# ===================================================

class ItemsPedidoDialog(QDialog):
    """Muestra y permite editar los ítems de un pedido."""

    def __init__(self, pedido_id, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ítems del pedido")
        self.resize(600, 300)
        self._pedido_id = pedido_id

        layout = QVBoxLayout(self)
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(
            ["ID", "Producto", "Cantidad", "Precio unitario"]
        )
        layout.addWidget(self.table)

        hb = QHBoxLayout()
        self.btn_add = QPushButton("Agregar ítem")
        self.btn_delete = QPushButton("Eliminar ítem")
        self.btn_save = QPushButton("Guardar cambios")
        self.btn_close = QPushButton("Cerrar")
        hb.addWidget(self.btn_add)
        hb.addWidget(self.btn_delete)
        hb.addStretch()
        hb.addWidget(self.btn_save)
        hb.addWidget(self.btn_close)
        layout.addLayout(hb)

        self.btn_add.clicked.connect(self.add_item_row)
        self.btn_delete.clicked.connect(self.delete_item_row)
        self.btn_save.clicked.connect(self.save_items)
        self.btn_close.clicked.connect(self.accept)

        self.load_items()

    def load_items(self):
        session = SessionLocal()
        try:
            items = session.query(ItemPedido).filter_by(pedido_id=self._pedido_id).all()

            rows = []
            for it in items:
                rows.append({
                    "id": it.id,
                    "producto": it.producto or "",
                    "cantidad": it.cantidad or 0,
                    "precio": it.precio_unitario or 0
                })
        finally:
            session.close()

        self.table.setRowCount(len(rows))

        for r, d in enumerate(rows):
            self.table.setItem(r, 0, QTableWidgetItem(str(d["id"])))
            self.table.setItem(r, 1, QTableWidgetItem(d["producto"]))
            self.table.setItem(r, 2, QTableWidgetItem(str(d["cantidad"])))
            self.table.setItem(r, 3, QTableWidgetItem(str(d["precio"])))

        self.table.resizeColumnsToContents()

    def add_item_row(self):
        r = self.table.rowCount()
        self.table.insertRow(r)
        self.table.setItem(r, 0, QTableWidgetItem(""))  # ID vacío (nuevo)
        self.table.setItem(r, 1, QTableWidgetItem(""))
        self.table.setItem(r, 2, QTableWidgetItem("1"))
        self.table.setItem(r, 3, QTableWidgetItem("0"))

    def delete_item_row(self):
        row = self.table.currentRow()
        if row >= 0:
            self.table.removeRow(row)

    def save_items(self):
        session = SessionLocal()

        try:
            existentes = {
                it.id: it
                for it in session.query(ItemPedido)
                .filter_by(pedido_id=self._pedido_id).all()
            }

            for r in range(self.table.rowCount()):
                id_item = self.table.item(r, 0)
                prod_item = self.table.item(r, 1)
                cant_item = self.table.item(r, 2)
                prec_item = self.table.item(r, 3)

                if not prod_item:
                    continue

                producto = prod_item.text().strip()
                if not producto:
                    continue

                try:
                    cantidad = int(cant_item.text()) if cant_item else 0
                except Exception:
                    cantidad = 0

                try:
                    precio = float(prec_item.text()) if prec_item else 0.0
                except Exception:
                    precio = 0.0

                if id_item and id_item.text().strip():
                    iid = int(id_item.text())
                    it = existentes.pop(iid, None)
                    if it:
                        it.producto = producto
                        it.cantidad = cantidad
                        it.precio_unitario = precio
                        it.total_item = cantidad * precio
                else:
                    it = ItemPedido(
                        producto=producto,
                        cantidad=cantidad,
                        precio_unitario=precio,
                        total_item=cantidad * precio,
                        pedido_id=self._pedido_id
                    )
                    session.add(it)

            # Eliminar ítems que ya no están en la tabla
            for it in existentes.values():
                session.delete(it)

            session.commit()
            QMessageBox.information(self, "Ítems", "Cambios guardados.")
            self.load_items()

        except Exception as exc:
            session.rollback()
            QMessageBox.critical(self, "Error", str(exc))
        finally:
            session.close()


# ===================================================
# =================== FORMULARIO ====================
# ===================================================

class PedidoFormDialog(QDialog):
    """Formulario para crear o editar un pedido."""

    def __init__(self, pedido=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Pedido")
        self.resize(450, 260)
        self._pedido = pedido

        layout = QVBoxLayout(self)
        form = QFormLayout()

        # Combo de clientes + botón "Nuevo cliente"
        self.cb_cliente = QComboBox()
        self._clientes_ids = []
        self.btn_nuevo_cliente = QPushButton("Nuevo cliente")
        self.cargar_clientes()

        # Widget para agrupar combo + botón en la misma fila del formulario
        hb_cliente = QHBoxLayout()
        hb_cliente.addWidget(self.cb_cliente)
        hb_cliente.addWidget(self.btn_nuevo_cliente)

        self.dt_fecha = QDateEdit()
        self.dt_fecha.setCalendarPopup(True)
        self.dt_fecha.setDate(QDate.currentDate())

        self.ed_numero = QLineEdit()
        self.ed_canal = QLineEdit()
        self.ed_forma_pago = QLineEdit()
        self.ed_tipo_doc = QLineEdit()
        self.ed_monto = QLineEdit()
        self.ed_saldo = QLineEdit()

        # Despacho: solo 2 opciones
        self.cb_despacho = QComboBox()
        self.cb_despacho.addItems([
            "Retiro en tienda",
            "Despacho al domicilio",
        ])

        # Estado como combo con opciones fijas
        self.cb_estado = QComboBox()
        self.cb_estado.addItems(ESTADOS_PEDIDO)

        form.addRow("Cliente:", hb_cliente)
        form.addRow("Fecha:", self.dt_fecha)
        form.addRow("N° Pedido:", self.ed_numero)
        form.addRow("Canal:", self.ed_canal)
        form.addRow("Forma de pago:", self.ed_forma_pago)
        form.addRow("Documento:", self.ed_tipo_doc)
        form.addRow("Monto pagado:", self.ed_monto)
        form.addRow("Saldo:", self.ed_saldo)
        form.addRow("Despacho:", self.cb_despacho)
        form.addRow("Estado:", self.cb_estado)

        layout.addLayout(form)

        hb = QHBoxLayout()
        hb.addStretch()
        btn_ok = QPushButton("Guardar")
        btn_cancel = QPushButton("Cancelar")
        hb.addWidget(btn_ok)
        hb.addWidget(btn_cancel)
        layout.addLayout(hb)

        btn_ok.clicked.connect(self.accept)
        btn_cancel.clicked.connect(self.reject)
        self.btn_nuevo_cliente.clicked.connect(self.crear_nuevo_cliente)

        # --- Comportamiento según sea nuevo o edición ---
        if self._pedido:
            # Editar pedido existente
            self.cargar_pedido()
            # En edición también dejamos el número bloqueado
            self.ed_numero.setReadOnly(True)
        else:
            # Pedido nuevo: generar número automático y bloquear campo
            session = SessionLocal()
            try:
                numero = generar_numero_pedido_db(session, datetime.now())
            except Exception as exc:
                numero = ""
                QMessageBox.critical(self, "Error", f"No se pudo generar N° de pedido:\n{exc}")
            finally:
                session.close()

            self.ed_numero.setText(numero)
            self.ed_numero.setReadOnly(True)

    def cargar_clientes(self):
        session = SessionLocal()
        try:
            clientes = session.query(Cliente).order_by(Cliente.nombre).all()
            self._clientes_ids = []
            self.cb_cliente.clear()
            for c in clientes:
                nombre = c.nombre or ""
                telefono = c.telefono or ""
                correo = c.correo or ""
                extra = []
                if telefono:
                    extra.append(telefono)
                if correo:
                    extra.append(correo)
                if extra and nombre:
                    display = f"{nombre} ({' | '.join(extra)})"
                elif extra:
                    display = " | ".join(extra)
                else:
                    display = nombre
                self.cb_cliente.addItem(display)
                self._clientes_ids.append(c.id)
        finally:
            session.close()

    def crear_nuevo_cliente(self):
        """
        Crear un cliente desde el formulario de pedido,
        preguntando todos los datos (pueden quedar en blanco excepto el nombre).
        Con restricción de solo números en teléfono y combo de comunas.
        """
        dlg = QDialog(self)
        dlg.setWindowTitle("Nuevo cliente")
        dlg.resize(400, 260)

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
            nuevo_id = c.id
        except Exception as exc:
            session.rollback()
            QMessageBox.critical(self, "Error", str(exc))
            return
        finally:
            session.close()

        # Recargar combo y seleccionar el nuevo cliente
        self.cargar_clientes()
        if nuevo_id in self._clientes_ids:
            idx = self._clientes_ids.index(nuevo_id)
            self.cb_cliente.setCurrentIndex(idx)

    def cargar_pedido(self):
        p = self._pedido

        if p.cliente_id in self._clientes_ids:
            idx = self._clientes_ids.index(p.cliente_id)
            self.cb_cliente.setCurrentIndex(idx)

        self.dt_fecha.setDate(QDate(
            p.fecha_pedido.year,
            p.fecha_pedido.month,
            p.fecha_pedido.day
        ))

        self.ed_numero.setText(p.numero_pedido or "")
        self.ed_canal.setText(p.canal_venta or "")
        self.ed_forma_pago.setText(p.forma_pago or "")
        self.ed_tipo_doc.setText(p.tipo_documento or "")
        self.ed_monto.setText(str(p.monto_pagado or ""))
        self.ed_saldo.setText(str(p.saldo or ""))

        # Despacho: si en BD hay algo distinto, se agrega a la lista
        despacho_actual = p.despacho or ""
        if despacho_actual and despacho_actual not in [self.cb_despacho.itemText(i) for i in range(self.cb_despacho.count())]:
            self.cb_despacho.addItem(despacho_actual)
        if despacho_actual:
            self.cb_despacho.setCurrentText(despacho_actual)

        # Estado: si el valor de BD no está en la lista, se agrega al combo
        estado_actual = p.estado or ""
        if estado_actual and estado_actual not in ESTADOS_PEDIDO:
            self.cb_estado.addItem(estado_actual)
        if estado_actual:
            self.cb_estado.setCurrentText(estado_actual)

    def obtener_datos(self):
        idx = self.cb_cliente.currentIndex()
        cliente_id = self._clientes_ids[idx] if idx >= 0 else None

        fecha_q = self.dt_fecha.date()
        fecha = datetime(fecha_q.year(), fecha_q.month(), fecha_q.day())

        try:
            monto = float(self.ed_monto.text() or 0)
        except Exception:
            monto = 0.0

        try:
            saldo = float(self.ed_saldo.text() or 0)
        except Exception:
            saldo = 0.0

        return {
            "cliente_id": cliente_id,
            "fecha": fecha,
            "numero": self.ed_numero.text().strip(),
            "canal": self.ed_canal.text().strip(),
            "forma_pago": self.ed_forma_pago.text().strip(),
            "tipo_doc": self.ed_tipo_doc.text().strip(),
            "monto": monto,
            "saldo": saldo,
            "despacho": self.cb_despacho.currentText().strip(),
            "estado": self.cb_estado.currentText().strip(),
        }


# ===================================================
# ================== LISTA PEDIDOS ==================
# ===================================================

class PedidosDialog(QDialog):
    """Listado y gestión de pedidos."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Pedidos - Raíz Diseño")
        self.resize(950, 500)

        layout = QVBoxLayout(self)

        # ---- Barra de búsqueda ----
        search_layout = QHBoxLayout()
        lbl_buscar_por = QLabel("Buscar por:")
        self.cb_buscar_por = QComboBox()
        self.cb_buscar_por.addItems(["Todos", "N° Pedido", "Cliente", "Fecha", "Estado"])

        self.ed_buscar = QLineEdit()
        self.ed_buscar.setPlaceholderText("Texto a buscar...")

        # Búsqueda por estado
        self.cb_buscar_estado = QComboBox()
        self.cb_buscar_estado.addItem("")
        self.cb_buscar_estado.addItems(ESTADOS_PEDIDO)
        self.cb_buscar_estado.setVisible(False)

        # Búsqueda por rango fecha
        self.lbl_desde = QLabel("Desde:")
        self.date_desde = QDateEdit()
        self.date_desde.setCalendarPopup(True)
        self.date_desde.setVisible(False)

        self.lbl_hasta = QLabel("Hasta:")
        self.date_hasta = QDateEdit()
        self.date_hasta.setCalendarPopup(True)
        self.date_hasta.setVisible(False)

        self.btn_buscar = QPushButton("Buscar")
        self.btn_limpiar_busqueda = QPushButton("Limpiar")

        search_layout.addWidget(lbl_buscar_por)
        search_layout.addWidget(self.cb_buscar_por)
        search_layout.addWidget(self.ed_buscar)
        search_layout.addWidget(self.cb_buscar_estado)
        search_layout.addWidget(self.lbl_desde)
        search_layout.addWidget(self.date_desde)
        search_layout.addWidget(self.lbl_hasta)
        search_layout.addWidget(self.date_hasta)
        search_layout.addWidget(self.btn_buscar)
        search_layout.addWidget(self.btn_limpiar_busqueda)

        layout.addLayout(search_layout)

        # ---- Tabla ----
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(
            [
                "ID",
                "N° Pedido",
                "Fecha",
                "Cliente",
                "Teléfono",
                "Monto",
                "Saldo",
                "Estado",
            ]
        )
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.table)

        # ---- Botones ----
        hb = QHBoxLayout()
        self.btn_add = QPushButton("Nuevo pedido")
        self.btn_edit = QPushButton("Editar")
        self.btn_delete = QPushButton("Eliminar")
        self.btn_items = QPushButton("Ver ítems")
        self.btn_close = QPushButton("Cerrar")

        hb.addWidget(self.btn_add)
        hb.addWidget(self.btn_edit)
        hb.addWidget(self.btn_delete)
        hb.addWidget(self.btn_items)
        hb.addStretch()
        hb.addWidget(self.btn_close)

        layout.addLayout(hb)

        # ---- Conexiones ----
        self.btn_add.clicked.connect(self.nuevo)
        self.btn_edit.clicked.connect(self.editar)
        self.btn_delete.clicked.connect(self.eliminar)
        self.btn_items.clicked.connect(self.ver_items)
        self.btn_close.clicked.connect(self.accept)

        self.btn_buscar.clicked.connect(self.aplicar_busqueda)
        self.btn_limpiar_busqueda.clicked.connect(self.limpiar_busqueda)
        self.ed_buscar.returnPressed.connect(self.aplicar_busqueda)

        self.cb_buscar_por.currentTextChanged.connect(self._cambio_modo_busqueda)
        self.cb_buscar_estado.currentIndexChanged.connect(self.aplicar_busqueda)

        self._datos_pedidos = []
        self.cargar()

    # ===============================================================
    # CAMBIO DE MODO DE BÚSQUEDA
    # ===============================================================
    def _cambio_modo_busqueda(self, modo):
        if modo == "Estado":
            self.ed_buscar.setVisible(False)
            self.cb_buscar_estado.setVisible(True)
            self.lbl_desde.setVisible(False)
            self.date_desde.setVisible(False)
            self.lbl_hasta.setVisible(False)
            self.date_hasta.setVisible(False)

        elif modo == "Fecha":
            self.ed_buscar.setVisible(False)
            self.cb_buscar_estado.setVisible(False)
            self.lbl_desde.setVisible(True)
            self.date_desde.setVisible(True)
            self.lbl_hasta.setVisible(True)
            self.date_hasta.setVisible(True)

        else:
            self.ed_buscar.setVisible(True)
            self.cb_buscar_estado.setVisible(False)
            self.lbl_desde.setVisible(False)
            self.date_desde.setVisible(False)
            self.lbl_hasta.setVisible(False)
            self.date_hasta.setVisible(False)

    # ===============================================================
    # LLENAR TABLA
    # ===============================================================
    def _llenar_tabla(self, datos):
        self.table.setRowCount(len(datos))
        for i, d in enumerate(datos):
            self.table.setItem(i, 0, QTableWidgetItem(str(d["id"])))
            self.table.setItem(i, 1, QTableWidgetItem(d["numero"]))
            self.table.setItem(i, 2, QTableWidgetItem(d["fecha"]))
            self.table.setItem(i, 3, QTableWidgetItem(d["cliente"]))     # nombre
            self.table.setItem(i, 4, QTableWidgetItem(d["telefono"]))    # teléfono
            self.table.setItem(i, 5, QTableWidgetItem(str(d["monto"])))
            self.table.setItem(i, 6, QTableWidgetItem(str(d["saldo"])))
            self.table.setItem(i, 7, QTableWidgetItem(d["estado"]))

        self.table.resizeColumnsToContents()

    # ===============================================================
    # CARGAR PEDIDOS (AQUÍ SE AGREGA LA COLUMNA TELÉFONO)
    # ===============================================================
    def cargar(self):
        session = SessionLocal()
        try:
            pedidos = (
                session.query(Pedido)
                .join(Cliente, Pedido.cliente_id == Cliente.id)
                .order_by(Pedido.fecha_pedido.desc())
                .all()
            )

            self._datos_pedidos = []

            for p in pedidos:

                if p.cliente:
                    nombre = p.cliente.nombre or ""
                    telefono = p.cliente.telefono or ""
                else:
                    nombre = ""
                    telefono = ""

                self._datos_pedidos.append(
                    {
                        "id": p.id,
                        "numero": p.numero_pedido or "",
                        "fecha": p.fecha_pedido.strftime("%Y-%m-%d") if p.fecha_pedido else "",
                        "cliente": nombre,
                        "telefono": telefono,
                        "monto": p.monto_pagado or 0,
                        "saldo": p.saldo or 0,
                        "estado": p.estado or "",
                    }
                )
        finally:
            session.close()

        self._llenar_tabla(self._datos_pedidos)

    # ===============================================================
    # BÚSQUEDA
    # ===============================================================
    def aplicar_busqueda(self):
        modo = self.cb_buscar_por.currentText()
        texto = self.ed_buscar.text().lower()

        # Buscar por estado
        if modo == "Estado":
            estado = self.cb_buscar_estado.currentText().lower()
            if not estado:
                self._llenar_tabla(self._datos_pedidos)
                return

            filtrados = [d for d in self._datos_pedidos if d["estado"].lower() == estado]
            self._llenar_tabla(filtrados)
            return

        # Buscar por fecha (rango)
        if modo == "Fecha":
            desde_q = self.date_desde.date()
            hasta_q = self.date_hasta.date()

            if desde_q > hasta_q:
                desde_q, hasta_q = hasta_q, desde_q

            desde = datetime(desde_q.year(), desde_q.month(), desde_q.day()).date()
            hasta = datetime(hasta_q.year(), hasta_q.month(), hasta_q.day()).date()

            filtrados = []
            for d in self._datos_pedidos:
                if not d["fecha"]:
                    continue
                fdate = datetime.strptime(d["fecha"], "%Y-%m-%d").date()
                if desde <= fdate <= hasta:
                    filtrados.append(d)

            self._llenar_tabla(filtrados)
            return

        # Buscar por texto
        if modo == "Cliente":
            filtrados = [
                d for d in self._datos_pedidos
                if texto in d["cliente"].lower() or texto in d["telefono"].lower()
            ]
            self._llenar_tabla(filtrados)
            return

        if modo == "N° Pedido":
            filtrados = [d for d in self._datos_pedidos if texto in d["numero"].lower()]
            self._llenar_tabla(filtrados)
            return

        # Todos
        self._llenar_tabla(self._datos_pedidos)

    # ===============================================================
    # LIMPIAR BUSQUEDA
    # ===============================================================
    def limpiar_busqueda(self):
        self.ed_buscar.clear()
        self.cb_buscar_por.setCurrentIndex(0)
        self.cb_buscar_estado.setCurrentIndex(0)
        self.date_desde.setDate(QDate.currentDate())
        self.date_hasta.setDate(QDate.currentDate())
        self._llenar_tabla(self._datos_pedidos)

    # ===============================================================
    # UTILIDAD
    # ===============================================================
    def _id_seleccionado(self):
        r = self.table.currentRow()
        if r < 0:
            return None
        return int(self.table.item(r, 0).text())

    # ===============================================================
    # CRUD DE PEDIDOS
    # ===============================================================
    def nuevo(self):
        dlg = PedidoFormDialog(parent=self)
        if dlg.exec() == QDialog.Accepted:
            datos = dlg.obtener_datos()

            if not datos["cliente_id"]:
                QMessageBox.warning(self, "Error", "Debes seleccionar un cliente.")
                return

            session = SessionLocal()
            try:
                p = Pedido(
                    cliente_id=datos["cliente_id"],
                    fecha_pedido=datos["fecha"],
                    numero_pedido=datos["numero"],
                    canal_venta=datos["canal"],
                    forma_pago=datos["forma_pago"],
                    tipo_documento=datos["tipo_doc"],
                    monto_pagado=datos["monto"],
                    saldo=datos["saldo"],
                    despacho=datos["despacho"],
                    estado=datos["estado"],
                )
                session.add(p)
                session.commit()
            finally:
                session.close()

            self.cargar()

    def editar(self):
        pid = self._id_seleccionado()
        if not pid:
            QMessageBox.warning(self, "Editar", "Selecciona un pedido.")
            return

        session = SessionLocal()
        pedido = session.query(Pedido).get(pid)
        session.close()

        if not pedido:
            return

        dlg = PedidoFormDialog(pedido, self)
        if dlg.exec() == QDialog.Accepted:
            datos = dlg.obtener_datos()

            session = SessionLocal()
            try:
                pedido = session.query(Pedido).get(pid)
                pedido.cliente_id = datos["cliente_id"]
                pedido.fecha_pedido = datos["fecha"]
                pedido.canal_venta = datos["canal"]
                pedido.forma_pago = datos["forma_pago"]
                pedido.tipo_documento = datos["tipo_doc"]
                pedido.monto_pagado = datos["monto"]
                pedido.saldo =datos["saldo"]
                pedido.despacho = datos["despacho"]
                pedido.estado = datos["estado"]
                session.commit()
            finally:
                session.close()

            self.cargar()

    def eliminar(self):
        pid = self._id_seleccionado()
        if not pid:
            QMessageBox.warning(self, "Eliminar", "Selecciona un pedido.")
            return

        if QMessageBox.question(self, "Eliminar", "¿Eliminar este pedido?") != QMessageBox.Yes:
            return

        session = SessionLocal()
        try:
            pedido = session.query(Pedido).get(pid)
            session.delete(pedido)
            session.commit()
        finally:
            session.close()

        self.cargar()

    def ver_items(self):
        pid = self._id_seleccionado()
        if not pid:
            QMessageBox.warning(self, "Ítems", "Selecciona un pedido.")
            return

        dlg = ItemsPedidoDialog(pid, self)
        dlg.exec()




# ===================================================
# =========== HISTORIAL DE COMPRAS CLIENTE ==========
# ===================================================

class HistorialClienteDialog(QDialog):
    """Historial de compras de un cliente específico."""

    def __init__(self, cliente_id, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Historial de compras")
        self.resize(750, 350)
        self._cliente_id = cliente_id

        layout = QVBoxLayout(self)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            ["ID pedido", "N° Pedido", "Fecha", "Monto pagado", "Saldo", "Estado"]
        )
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.table)

        hb = QHBoxLayout()
        self.btn_items = QPushButton("Ver ítems")
        self.btn_close = QPushButton("Cerrar")
        hb.addWidget(self.btn_items)
        hb.addStretch()
        hb.addWidget(self.btn_close)
        layout.addLayout(hb)

        self.btn_items.clicked.connect(self.ver_items)
        self.btn_close.clicked.connect(self.accept)

        self.cargar()

    def cargar(self):
        session = SessionLocal()
        try:
            pedidos = (
                session.query(Pedido)
                .filter(Pedido.cliente_id == self._cliente_id)
                .order_by(Pedido.fecha_pedido.desc())
                .all()
            )

            datos = []
            for p in pedidos:
                datos.append({
                    "id": p.id,
                    "numero": p.numero_pedido or "",
                    "fecha": p.fecha_pedido.strftime("%Y-%m-%d") if p.fecha_pedido else "",
                    "monto": p.monto_pagado or 0,
                    "saldo": p.saldo or 0,
                    "estado": p.estado or "",
                })
        finally:
            session.close()

        self.table.setRowCount(len(datos))

        for i, d in enumerate(datos):
            self.table.setItem(i, 0, QTableWidgetItem(str(d["id"])))
            self.table.setItem(i, 1, QTableWidgetItem(d["numero"]))
            self.table.setItem(i, 2, QTableWidgetItem(d["fecha"]))
            self.table.setItem(i, 3, QTableWidgetItem(str(d["monto"])))
            self.table.setItem(i, 4, QTableWidgetItem(str(d["saldo"])))
            self.table.setItem(i, 5, QTableWidgetItem(d["estado"]))

        self.table.resizeColumnsToContents()

    def _id_pedido_seleccionado(self):
        r = self.table.currentRow()
        if r < 0:
            return None
        return int(self.table.item(r, 0).text())

    def ver_items(self):
        pid = self._id_pedido_seleccionado()
        if not pid:
            QMessageBox.information(self, "Ítems", "Selecciona un pedido.")
            return

        dlg = ItemsPedidoDialog(pid, self)
        dlg.exec()
