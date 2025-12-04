# gui/pedidos_dialog.py
from datetime import datetime

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget,
    QTableWidgetItem, QPushButton, QMessageBox,
    QFormLayout, QComboBox, QDateEdit, QLineEdit, QLabel, QCompleter
)
from PySide6.QtCore import Qt, QDate, QRegularExpression
from PySide6.QtGui import QRegularExpressionValidator

from db import SessionLocal
from models import Cliente, Pedido, ItemPedido


# ===================================================
# ========== UTILIDADES COMUNAS Y VALIDADORES =======
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
    """Solo permite dígitos 0-9 (vacío también es válido)."""
    regex = QRegularExpression(r"^[0-9]*$")
    return QRegularExpressionValidator(regex, parent)


def configurar_combo_comuna(combo: QComboBox, valor_actual: str | None = None) -> None:
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

def formatear_rut(texto: str) -> str:
    """
    Limpia y formatea un RUT chileno:
    - Deja solo dígitos y K/k
    - Pone puntos y guion: 12345678K -> 12.345.678-K
    """
    limpio = "".join(ch for ch in texto if ch.isdigit() or ch in "Kk").upper()
    if not limpio:
        return ""

    if len(limpio) == 1:
        # Solo un dígito/dv aún, no formateamos
        return limpio

    cuerpo = limpio[:-1]
    dv = limpio[-1]

    # Separar el cuerpo en grupos de 3 desde la derecha
    rev = cuerpo[::-1]
    grupos = [rev[i:i+3] for i in range(0, len(rev), 3)]
    cuerpo_fmt = ".".join(g[::-1] for g in grupos[::-1])

    return f"{cuerpo_fmt}-{dv}"


def crear_lineedit_rut(parent=None) -> QLineEdit:
    """
    Crea un QLineEdit que formatea el RUT en vivo mientras se escribe.
    """
    le = QLineEdit(parent)
    le._rut_lock = False  # bandera para evitar recursión

    def on_text_edited(text: str):
        if le._rut_lock:
            return
        le._rut_lock = True
        formateado = formatear_rut(text)
        le.setText(formateado)
        # Por simplicidad dejamos el cursor al final
        le.setCursorPosition(len(formateado))
        le._rut_lock = False

    le.textEdited.connect(on_text_edited)
    return le



# ===================================================
# ========== GENERACIÓN NÚMERO DE PEDIDO ============
# ===================================================

def _generar_codigo_pedido(fecha: datetime, correlativo: int) -> str:
    """Genera un código del tipo PYYYYMMDD-XXX."""
    return "P" + fecha.strftime("%Y%m%d") + f"-{correlativo:03d}"


def generar_numero_pedido_db(session, fecha: datetime | None = None) -> str:
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

    def __init__(self, pedido_id: int, parent=None) -> None:
        super().__init__(parent)

        # 👉 permitir maximizar / minimizar
        self.setWindowFlags(
            self.windowFlags()
            | Qt.WindowMaximizeButtonHint
            | Qt.WindowMinimizeButtonHint
        )

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
                # Resumen de montos del pedido
        self.lbl_resumen = QLabel()
        layout.addWidget(self.lbl_resumen)


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

    def load_items(self) -> None:
        """Carga los ítems actuales del pedido desde la BD y calcula resumen."""
        session = SessionLocal()
        try:
            items = (
                session.query(ItemPedido)
                .filter_by(pedido_id=self._pedido_id)
                .all()
            )
            pedido = session.query(Pedido).get(self._pedido_id)

            rows: list[dict] = []
            total_pedido = 0
            for it in items:
                cantidad = it.cantidad or 0
                precio = it.precio_unitario or 0
                total_pedido += int(cantidad) * int(precio)
                rows.append(
                    {
                        "id": it.id,
                        "producto": it.producto or "",
                        "cantidad": cantidad,
                        "precio": precio,
                    }
                )

            abono = pedido.monto_pagado or 0 if pedido else 0
            if pedido and pedido.saldo is not None:
                saldo_final = pedido.saldo
            else:
                saldo_final = max(int(total_pedido) - int(abono), 0)
        finally:
            session.close()

        self.table.setRowCount(len(rows))

        for r, d in enumerate(rows):
            self.table.setItem(r, 0, QTableWidgetItem(str(d["id"])))
            self.table.setItem(r, 1, QTableWidgetItem(d["producto"]))
            self.table.setItem(r, 2, QTableWidgetItem(str(d["cantidad"])))
            self.table.setItem(r, 3, QTableWidgetItem(str(d["precio"])))

        self.table.resizeColumnsToContents()

        self.lbl_resumen.setText(
            f"Monto: {int(total_pedido)} | Abono: {int(abono)} | Saldo final: {int(saldo_final)}"
        )


    def add_item_row(self) -> None:
        """Agrega una fila vacía para un nuevo ítem."""
        r = self.table.rowCount()
        self.table.insertRow(r)
        self.table.setItem(r, 0, QTableWidgetItem(""))      # ID vacío (nuevo)
        self.table.setItem(r, 1, QTableWidgetItem(""))      # Producto
        self.table.setItem(r, 2, QTableWidgetItem("1"))     # Cantidad por defecto
        self.table.setItem(r, 3, QTableWidgetItem("0"))     # Precio por defecto

    def delete_item_row(self) -> None:
        """Elimina la fila seleccionada en la tabla."""
        row = self.table.currentRow()
        if row >= 0:
            self.table.removeRow(row)

    def save_items(self) -> None:
        """
        Guarda los ítems de la tabla en la base de datos.

        - Crea ítems nuevos para filas sin ID.
        - Actualiza ítems existentes.
        - Elimina ítems que estaban en la BD pero ya no están en la tabla.
        """
        session = SessionLocal()

        try:
            # Ítems que ya existen en la BD para este pedido
            existentes: dict[int, ItemPedido] = {
                it.id: it
                for it in session.query(ItemPedido)
                .filter_by(pedido_id=self._pedido_id)
                .all()
            }

            # Recorrer las filas de la tabla y actualizar / crear ítems
            for r in range(self.table.rowCount()):
                id_item = self.table.item(r, 0)
                prod_item = self.table.item(r, 1)
                cant_item = self.table.item(r, 2)
                prec_item = self.table.item(r, 3)

                # Si no hay celda de producto, ignoramos la fila
                if not prod_item:
                    continue

                producto = prod_item.text().strip()
                if not producto:
                    # Fila vacía de producto -> no se guarda
                    continue

                # Cantidad
                try:
                    cantidad = int(cant_item.text()) if cant_item and cant_item.text().strip() else 0
                except Exception:
                    cantidad = 0

                if cantidad <= 0:
                    cantidad = 1

                # Precio
                try:
                    precio = float(prec_item.text()) if prec_item and prec_item.text().strip() else 0.0
                except Exception:
                    precio = 0.0

                # ¿Es un ítem ya existente o uno nuevo?
                iid: int | None = None
                if id_item and id_item.text().strip().isdigit():
                    iid = int(id_item.text().strip())

                if iid is not None and iid in existentes:
                    # Actualizar ítem existente
                    it = existentes.pop(iid)
                    it.producto = producto
                    it.cantidad = cantidad
                    it.precio_unitario = precio
                    it.total_item = cantidad * precio
                else:
                    # Crear ítem nuevo
                    it = ItemPedido(
                        producto=producto,
                        cantidad=cantidad,
                        precio_unitario=precio,
                        total_item=cantidad * precio,
                        pedido_id=self._pedido_id,
                    )
                    session.add(it)

            # Eliminar ítems que ya no están en la tabla
            for it in existentes.values():
                session.delete(it)

                # Primero guardamos los cambios
            session.commit()

                        # ---- Calcular el total del pedido y actualizar saldo final ----
            total = session.query(ItemPedido).filter_by(pedido_id=self._pedido_id).all()
            total_pedido = sum(
                (int(it.cantidad or 0)) * int(it.precio_unitario or 0) for it in total
            )

            pedido = session.query(Pedido).get(self._pedido_id)
            if pedido:
                abono = pedido.monto_pagado or 0
                pedido.saldo = max(int(total_pedido) - int(abono), 0)

            session.commit()
            # ---------------------------------------------

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

    def __init__(self, pedido: Pedido | None = None, parent=None) -> None:
        super().__init__(parent)

        # 👉 permitir maximizar / minimizar
        self.setWindowFlags(
            self.windowFlags()
            | Qt.WindowMaximizeButtonHint
            | Qt.WindowMinimizeButtonHint
        )

        self.setWindowTitle("Pedido")
        self.resize(450, 260)
        self._pedido = pedido


        layout = QVBoxLayout(self)
        form = QFormLayout()

               # Combo de clientes + botón "Nuevo cliente"
        self.cb_cliente = QComboBox()
        self._clientes_ids: list[int] = []
        self.btn_nuevo_cliente = QPushButton("Nuevo cliente")
        self.cargar_clientes()

        # Hacer el combo de clientes editable con búsqueda por texto
        self.cb_cliente.setEditable(True)
        # Evita que al escribir se creen clientes nuevos en la lista
        self.cb_cliente.setInsertPolicy(QComboBox.NoInsert)
        # Autocompletado que busca el texto en cualquier parte del nombre/teléfono
        completer = QCompleter(self.cb_cliente.model(), self.cb_cliente)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setFilterMode(Qt.MatchContains)
        self.cb_cliente.setCompleter(completer)

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
        self.ed_abono = QLineEdit()


        # Despacho: solo 2 opciones
        self.cb_despacho = QComboBox()
        self.cb_despacho.addItems(
            [
                "Retiro en tienda",
                "Despacho al domicilio",
            ]
        )

        # Estado como combo con opciones fijas
        self.cb_estado = QComboBox()
        self.cb_estado.addItems(ESTADOS_PEDIDO)

        form.addRow("Cliente:", hb_cliente)
        form.addRow("Fecha:", self.dt_fecha)
        form.addRow("N° Pedido:", self.ed_numero)
        form.addRow("Canal:", self.ed_canal)
        form.addRow("Forma de pago:", self.ed_forma_pago)
        form.addRow("Documento:", self.ed_tipo_doc)
        form.addRow("Abono:", self.ed_abono)
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

    # ------------------- CLIENTES -------------------

    def cargar_clientes(self) -> None:
        """Carga los clientes en el combo, guardando IDs en un arreglo paralelo."""
        session = SessionLocal()
        try:
            clientes = session.query(Cliente).order_by(Cliente.nombre).all()
            self._clientes_ids = []
            self.cb_cliente.clear()
            for c in clientes:
                nombre = c.nombre or ""
                telefono = c.telefono or ""
                if telefono and nombre:
                    display = f"{nombre} ({telefono})"
                else:
                    display = nombre or telefono
                self.cb_cliente.addItem(display)
                self._clientes_ids.append(c.id)
        finally:
            session.close()

    def crear_nuevo_cliente(self) -> None:
        """
        Crear un cliente desde el formulario de pedido,
        ...
        """
        dlg = QDialog(self)

        # 👉 permitir maximizar / minimizar
        dlg.setWindowFlags(
         dlg.windowFlags()
         | Qt.WindowMaximizeButtonHint
            | Qt.WindowMinimizeButtonHint
     )

        dlg.setWindowTitle("Nuevo cliente")
        dlg.resize(400, 260)


        vbox = QVBoxLayout(dlg)
        form = QFormLayout()

        ed_nombre = QLineEdit()
        ed_rut = crear_lineedit_rut(dlg)

        ed_telefono = QLineEdit()
        ed_telefono.setValidator(crear_validador_telefono(dlg))

        ed_correo = QLineEdit()
        ed_direccion = QLineEdit()

        cb_comuna = QComboBox()
        configurar_combo_comuna(cb_comuna)

        form.addRow("Nombre:", ed_nombre)
        form.addRow("RUT:", ed_rut)
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
        rut = ed_rut.text().strip()
        telefono = ed_telefono.text().strip() or None
        correo = ed_correo.text().strip() or None
        direccion = ed_direccion.text().strip() or None
        comuna = cb_comuna.currentText().strip() or None

        # Nombre y RUT obligatorios
        if not nombre or not rut:
            QMessageBox.warning(
                self,
                "Nuevo cliente",
                "Nombre y RUT son obligatorios."
            )
            return

        rut_limpio = rut.replace(".", "").replace("-", "").upper()

        session = SessionLocal()
        nuevo_id: int | None = None
        try:
            # Buscar si ya existe un cliente con ese RUT
            cliente_existente = None
            for c in session.query(Cliente).all():
                if not c.rut:
                    continue
                rut_existente_limpio = (
                    c.rut.replace(".", "").replace("-", "").upper()
                )
                if rut_existente_limpio == rut_limpio:
                    cliente_existente = c
                    break

            if cliente_existente:
                # Ya existe: usamos ese cliente para el pedido
                QMessageBox.information(
                    self,
                    "Cliente existente",
                    f"Ya existe un cliente con este RUT:\n"
                    f"{cliente_existente.nombre} ({cliente_existente.rut}).\n"
                    f"Se usará ese cliente en el pedido."
                )
                nuevo_id = cliente_existente.id
            else:
                # No existe: creamos un nuevo cliente
                c = Cliente(
                    nombre=nombre,
                    rut=rut,
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

        # Recargar combo y seleccionar el cliente (nuevo o existente)
        self.cargar_clientes()
        if nuevo_id in self._clientes_ids:
            idx = self._clientes_ids.index(nuevo_id)
            self.cb_cliente.setCurrentIndex(idx)


    # -------------------- PEDIDO --------------------

    def cargar_pedido(self) -> None:
        """Carga datos del pedido en el formulario (modo edición)."""
        p = self._pedido

        # Cliente
        if p.cliente_id in self._clientes_ids:
            idx = self._clientes_ids.index(p.cliente_id)
            self.cb_cliente.setCurrentIndex(idx)

        # Fecha
        if p.fecha_pedido:
            self.dt_fecha.setDate(QDate(
                p.fecha_pedido.year,
                p.fecha_pedido.month,
                p.fecha_pedido.day,
            ))

        # Datos básicos
        self.ed_numero.setText(p.numero_pedido or "")
        self.ed_canal.setText(p.canal_venta or "")
        self.ed_forma_pago.setText(p.forma_pago or "")
        self.ed_tipo_doc.setText(p.tipo_documento or "")
        # El abono se guarda en el campo monto_pagado
        self.ed_abono.setText(str(p.monto_pagado or ""))


        # Despacho: si en BD hay algo distinto, se agrega a la lista
        despacho_actual = p.despacho or ""
        if despacho_actual and despacho_actual not in [
            self.cb_despacho.itemText(i) for i in range(self.cb_despacho.count())
        ]:
            self.cb_despacho.addItem(despacho_actual)
        if despacho_actual:
            self.cb_despacho.setCurrentText(despacho_actual)

        # Estado: si el valor de BD no está en la lista, se agrega al combo
        estado_actual = p.estado or ""
        if estado_actual and estado_actual not in ESTADOS_PEDIDO:
            self.cb_estado.addItem(estado_actual)
        if estado_actual:
            self.cb_estado.setCurrentText(estado_actual)

    def obtener_datos(self) -> dict:
        """Devuelve un diccionario con los datos del formulario."""
        idx = self.cb_cliente.currentIndex()
        cliente_id = self._clientes_ids[idx] if idx >= 0 else None

        fecha_q = self.dt_fecha.date()
        fecha = datetime(fecha_q.year(), fecha_q.month(), fecha_q.day())

        try:
            abono = int(self.ed_abono.text() or 0)
        except Exception:
            abono = 0

        return {
            "cliente_id": cliente_id,
            "fecha": fecha,
            "numero": self.ed_numero.text().strip(),
            "canal": self.ed_canal.text().strip(),
            "forma_pago": self.ed_forma_pago.text().strip(),
            "tipo_doc": self.ed_tipo_doc.text().strip(),
            "abono": abono,
            "despacho": self.cb_despacho.currentText().strip(),
            "estado": self.cb_estado.currentText().strip(),
        }



# ===================================================
# ================== LISTA PEDIDOS ==================
# ===================================================

class PedidosDialog(QDialog):
    """Listado y gestión de pedidos."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        # 👉 permitir maximizar / minimizar
        self.setWindowFlags(
            self.windowFlags()
            | Qt.WindowMaximizeButtonHint
            | Qt.WindowMinimizeButtonHint
        )

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
        self.table.setColumnCount(10)
        self.table.setHorizontalHeaderLabels(
            [
                "ID",
                "N° Pedido",
                "Fecha",
                "Cliente",
                "RUT",
                "Teléfono",
                "Monto",
                "Abono",
                "Saldo final",
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

        self._datos_pedidos: list[dict] = []
        self.cargar()

    # ===============================================================
    # CAMBIO DE MODO DE BÚSQUEDA
    # ===============================================================
    def _cambio_modo_busqueda(self, modo: str) -> None:
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
    def _llenar_tabla(self, datos: list[dict]) -> None:
        self.table.setRowCount(len(datos))
        for i, d in enumerate(datos):
            self.table.setItem(i, 0, QTableWidgetItem(str(d["id"])))
            self.table.setItem(i, 1, QTableWidgetItem(d["numero"]))
            self.table.setItem(i, 2, QTableWidgetItem(d["fecha"]))
            self.table.setItem(i, 3, QTableWidgetItem(d["cliente"]))
            # NUEVA COLUMNA RUT (columna 4)
            self.table.setItem(i, 4, QTableWidgetItem(d.get("rut", "")))
            # El resto se corre una posición
            self.table.setItem(i, 5, QTableWidgetItem(d["telefono"]))
            self.table.setItem(i, 6, QTableWidgetItem(str(int(d["monto"]))))
            self.table.setItem(i, 7, QTableWidgetItem(str(int(d["abono"]))))
            self.table.setItem(i, 8, QTableWidgetItem(str(int(d["saldo_final"]))))
            self.table.setItem(i, 9, QTableWidgetItem(d["estado"]))


        self.table.resizeColumnsToContents()


    # ===============================================================
    # CARGAR PEDIDOS (CON TELÉFONO DEL CLIENTE)
    # ===============================================================
    def cargar(self) -> None:
        """Carga los pedidos desde la BD y rellena la tabla."""
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
                    # NUEVO: RUT formateado si existe
                    rut = formatear_rut(p.cliente.rut) if getattr(p.cliente, "rut", None) else ""
                else:
                    nombre = ""
                    telefono = ""
                    rut = ""

                                # Calcular monto del pedido a partir de los ítems
                total_pedido = 0
                for it in p.items:
                    total_pedido += int(it.cantidad or 0) * int(it.precio_unitario or 0)

                abono = p.monto_pagado or 0
                if p.saldo is not None:
                    saldo_final = p.saldo
                else:
                    saldo_final = max(int(total_pedido) - int(abono), 0)

                self._datos_pedidos.append(
                    {
                        "id": p.id,
                        "numero": p.numero_pedido or "",
                        "fecha": p.fecha_pedido.strftime("%Y-%m-%d") if p.fecha_pedido else "",
                        "cliente": nombre,
                        "rut": rut,
                        "telefono": telefono,
                        "monto": total_pedido,
                        "abono": abono,
                        "saldo_final": saldo_final,
                        "estado": p.estado or "",
                    }
                )


        finally:
            session.close()

        self._llenar_tabla(self._datos_pedidos)

    # ===============================================================
    # BÚSQUEDA
    # ===============================================================
    def aplicar_busqueda(self) -> None:
        modo = self.cb_buscar_por.currentText()
        texto = self.ed_buscar.text().lower()

        # Buscar por estado
        if modo == "Estado":
            estado = self.cb_buscar_estado.currentText().lower()
            if not estado:
                self._llenar_tabla(self._datos_pedidos)
                return

            filtrados = [
                d for d in self._datos_pedidos if d["estado"].lower() == estado
            ]
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

            filtrados: list[dict] = []
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
            filtrados = []
            for d in self._datos_pedidos:
                cliente = d["cliente"].lower()
                telefono = d["telefono"].lower()
                rut = d.get("rut", "").lower()
                if texto in cliente or texto in telefono or texto in rut:
                    filtrados.append(d)

            self._llenar_tabla(filtrados)
            return


        if modo == "N° Pedido":
            filtrados = [
                d for d in self._datos_pedidos if texto in d["numero"].lower()
            ]
            self._llenar_tabla(filtrados)
            return

        # Todos
        self._llenar_tabla(self._datos_pedidos)

    # ===============================================================
    # LIMPIAR BÚSQUEDA
    # ===============================================================
    def limpiar_busqueda(self) -> None:
        self.ed_buscar.clear()
        self.cb_buscar_por.setCurrentIndex(0)
        self.cb_buscar_estado.setCurrentIndex(0)
        self.date_desde.setDate(QDate.currentDate())
        self.date_hasta.setDate(QDate.currentDate())
        self._llenar_tabla(self._datos_pedidos)

    # ===============================================================
    # UTILIDAD
    # ===============================================================
    def _id_seleccionado(self) -> int | None:
        r = self.table.currentRow()
        if r < 0:
            return None
        return int(self.table.item(r, 0).text())

    # ===============================================================
    # CRUD DE PEDIDOS
    # ===============================================================
    def nuevo(self) -> None:
        """
        Crea un nuevo pedido.
        Después de crearlo, abre automáticamente la ventana de ítems
        para que el usuario pueda agregar productos al pedido.
        """
        dlg = PedidoFormDialog(parent=self)
        if dlg.exec() == QDialog.Accepted:
            datos = dlg.obtener_datos()

            if not datos["cliente_id"]:
                QMessageBox.warning(self, "Error", "Debes seleccionar un cliente.")
                return

            session = SessionLocal()
            nuevo_id: int | None = None
            try:
                p = Pedido(
                    cliente_id=datos["cliente_id"],
                    fecha_pedido=datos["fecha"],
                    numero_pedido=datos["numero"],
                    canal_venta=datos["canal"],
                    forma_pago=datos["forma_pago"],
                    tipo_documento=datos["tipo_doc"],
                    # Guardamos el abono en monto_pagado
                    monto_pagado=datos["abono"],
                    # El saldo final se calculará según los ítems
                    saldo=0,
                    despacho=datos["despacho"],
                    estado=datos["estado"],
                )

                session.add(p)
                session.commit()
                nuevo_id = p.id
            except Exception as exc:
                session.rollback()
                QMessageBox.critical(
                    self, "Error", f"No se pudo crear el pedido:\n{exc}"
                )
                return
            finally:
                session.close()

            # Si el pedido se creó bien, abrimos inmediatamente la ventana de ítems
            if nuevo_id is not None:
                dlg_items = ItemsPedidoDialog(nuevo_id, self)
                dlg_items.exec()

            # Finalmente refrescamos la tabla de pedidos
            self.cargar()

    def editar(self) -> None:
        pid = self._id_seleccionado()
        if not pid:
            QMessageBox.warning(self, "Editar", "Selecciona un pedido.")
            return

        session = SessionLocal()
        try:
            pedido = session.query(Pedido).get(pid)
        finally:
            session.close()

        if not pedido:
            return

        dlg = PedidoFormDialog(pedido, self)
        if dlg.exec() == QDialog.Accepted:
            datos = dlg.obtener_datos()

            session = SessionLocal()
            try:
                pedido = session.query(Pedido).get(pid)
                if not pedido:
                    return
                pedido.cliente_id = datos["cliente_id"]
                pedido.fecha_pedido = datos["fecha"]
                pedido.canal_venta = datos["canal"]
                pedido.forma_pago = datos["forma_pago"]
                pedido.tipo_documento = datos["tipo_doc"]
                               # Guardamos el abono
                pedido.monto_pagado = datos["abono"]
                pedido.despacho = datos["despacho"]
                pedido.estado = datos["estado"]

                # Recalcular saldo final según ítems
                total_pedido = 0
                for it in pedido.items:
                    total_pedido += int(it.cantidad or 0) * int(it.precio_unitario or 0)

                abono = pedido.monto_pagado or 0
                pedido.saldo = max(int(total_pedido) - int(abono), 0)

                session.commit()

            finally:
                session.close()

            self.cargar()

    def eliminar(self) -> None:
        pid = self._id_seleccionado()
        if not pid:
            QMessageBox.warning(self, "Eliminar", "Selecciona un pedido.")
            return

        if QMessageBox.question(
            self, "Eliminar", "¿Eliminar este pedido?"
        ) != QMessageBox.Yes:
            return

        session = SessionLocal()
        try:
            pedido = session.query(Pedido).get(pid)
            if pedido:
                session.delete(pedido)
                session.commit()
        finally:
            session.close()

        self.cargar()

    def ver_items(self) -> None:
        pid = self._id_seleccionado()
        if not pid:
            QMessageBox.warning(self, "Ítems", "Selecciona un pedido.")
            return

        dlg = ItemsPedidoDialog(pid, self)
        dlg.exec()
        # refrescar la tabla de pedidos para que se vea el nuevo monto
        self.cargar()



# ===================================================
# =========== HISTORIAL DE COMPRAS CLIENTE ==========
# ===================================================

class HistorialClienteDialog(QDialog):
    """Historial de compras de un cliente específico."""

    def __init__(self, cliente_id: int, parent=None) -> None:
        super().__init__(parent)

        # 👉 permitir maximizar / minimizar
        self.setWindowFlags(
            self.windowFlags()
            | Qt.WindowMaximizeButtonHint
            | Qt.WindowMinimizeButtonHint
        )

        self.setWindowTitle("Historial de compras")
        self.resize(750, 350)
        self._cliente_id = cliente_id

        layout = QVBoxLayout(self)

        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(
            ["ID pedido", "N° Pedido", "Fecha", "Monto", "Abono", "Saldo final", "Estado"]
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

    def cargar(self) -> None:
        """Carga el historial de pedidos de un cliente."""
        session = SessionLocal()
        try:
            pedidos = (
                session.query(Pedido)
                .filter(Pedido.cliente_id == self._cliente_id)
                .order_by(Pedido.fecha_pedido.desc())
                .all()
            )

            datos: list[dict] = []
            for p in pedidos:
                                # Calcular monto del pedido desde los ítems
                total_pedido = 0
                for it in p.items:
                    total_pedido += int(it.cantidad or 0) * int(it.precio_unitario or 0)

                abono = p.monto_pagado or 0
                if p.saldo is not None:
                    saldo_final = p.saldo
                else:
                    saldo_final = max(int(total_pedido) - int(abono), 0)

                datos.append(
                    {
                        "id": p.id,
                        "numero": p.numero_pedido or "",
                        "fecha": p.fecha_pedido.strftime("%Y-%m-%d")
                        if p.fecha_pedido
                        else "",
                        "monto": total_pedido,
                        "abono": abono,
                        "saldo_final": saldo_final,
                        "estado": p.estado or "",
                    }
                )

        finally:
            session.close()

        self.table.setRowCount(len(datos))

        for i, d in enumerate(datos):
            self.table.setItem(i, 0, QTableWidgetItem(str(d["id"])))
            self.table.setItem(i, 1, QTableWidgetItem(d["numero"]))
            self.table.setItem(i, 2, QTableWidgetItem(d["fecha"]))
            self.table.setItem(i, 3, QTableWidgetItem(str(d["monto"])))
            self.table.setItem(i, 4, QTableWidgetItem(str(d["abono"])))
            self.table.setItem(i, 5, QTableWidgetItem(str(d["saldo_final"])))
            self.table.setItem(i, 6, QTableWidgetItem(d["estado"]))

        self.table.resizeColumnsToContents()

    def _id_pedido_seleccionado(self) -> int | None:
        r = self.table.currentRow()
        if r < 0:
            return None
        return int(self.table.item(r, 0).text())

    def ver_items(self) -> None:
        pid = self._id_pedido_seleccionado()
        if not pid:
            QMessageBox.information(self, "Ítems", "Selecciona un pedido.")
            return

        dlg = ItemsPedidoDialog(pid, self)
        dlg.exec()
        self.cargar()

