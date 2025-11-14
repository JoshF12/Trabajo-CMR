from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit,
    QPushButton, QListWidget, QTextEdit, QMessageBox, QInputDialog
)
from PySide6.QtCore import Qt
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import Session, joinedload
from models import Cliente, Pedido, ItemPedido
from datetime import datetime
import sys

# --- Configuración de conexión ---
DB_URL = "mysql+pymysql://crm_user:TuPasswordFuerte123!@localhost:3306/crm_pyme?charset=utf8mb4"
engine = create_engine(DB_URL)


class CRMApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CRM PyME — Gestión de Clientes y Pedidos")
        self.resize(1000, 600)

        # --- Barra de búsqueda ---
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Buscar cliente por nombre, teléfono, correo o comuna...")
        self.search_btn = QPushButton("🔍 Buscar")
        self.search_btn.clicked.connect(self.buscar_clientes)

        # --- Botones principales ---
        self.btn_nuevo_cliente = QPushButton("➕ Nuevo Cliente")
        self.btn_editar_cliente = QPushButton("✏️ Editar Cliente")
        self.btn_eliminar_cliente = QPushButton("🗑️ Eliminar Cliente")
        self.btn_nuevo_pedido = QPushButton("🧾 Nuevo Pedido")

        self.btn_nuevo_cliente.clicked.connect(self.nuevo_cliente)
        self.btn_editar_cliente.clicked.connect(self.editar_cliente)
        self.btn_eliminar_cliente.clicked.connect(self.eliminar_cliente)
        self.btn_nuevo_pedido.clicked.connect(self.nuevo_pedido)

        # --- Layout superior ---
        top_layout = QHBoxLayout()
        for b in [
            self.search_input, self.search_btn,
            self.btn_nuevo_cliente, self.btn_editar_cliente,
            self.btn_eliminar_cliente, self.btn_nuevo_pedido
        ]:
            top_layout.addWidget(b)

        # --- Lista de resultados ---
        self.lista_resultados = QListWidget()
        self.lista_resultados.itemSelectionChanged.connect(self.mostrar_detalle)

        # --- Panel de detalle ---
        self.detalle = QTextEdit()
        self.detalle.setReadOnly(True)

        # --- Layout principal ---
        main_layout = QVBoxLayout()
        content_layout = QHBoxLayout()
        content_layout.addWidget(self.lista_resultados, 3)
        content_layout.addWidget(self.detalle, 6)

        main_layout.addLayout(top_layout)
        main_layout.addLayout(content_layout)
        self.setLayout(main_layout)

        self.cliente_seleccionado = None

    # =======================================================
    # Buscar y mostrar clientes
    # =======================================================
    def buscar_clientes(self):
        texto = self.search_input.text().strip()
        self.lista_resultados.clear()
        self.cliente_seleccionado = None

        if not texto:
            return

        with Session(engine) as s:
            query = select(Cliente).where(
                (Cliente.nombre.ilike(f"%{texto}%")) |
                (Cliente.telefono.ilike(f"%{texto}%")) |
                (Cliente.correo.ilike(f"%{texto}%")) |
                (Cliente.comuna.ilike(f"%{texto}%"))
            ).order_by(Cliente.nombre.asc())

            clientes = s.scalars(query).all()
            for c in clientes:
                self.lista_resultados.addItem(f"{c.id} — {c.nombre} — {c.telefono or ''} — {c.correo or ''}")

    def mostrar_detalle(self):
        items = self.lista_resultados.selectedItems()
        if not items:
            return

        texto = items[0].text()
        cliente_id = int(texto.split("—")[0].strip())
        self.cliente_seleccionado = cliente_id

        with Session(engine) as s:
            cliente = s.scalar(
                select(Cliente)
                .options(joinedload(Cliente.pedidos).joinedload(Pedido.items))
                .where(Cliente.id == cliente_id)
            )

            if not cliente:
                self.detalle.setPlainText("Cliente no encontrado.")
                return

            info = []
            info.append(f"📋 CLIENTE #{cliente.id}\n")
            info.append(f"Nombre: {cliente.nombre}")
            info.append(f"Teléfono: {cliente.telefono or '-'}")
            info.append(f"Correo: {cliente.correo or '-'}")
            info.append(f"Dirección: {cliente.direccion or '-'}")
            info.append(f"Comuna: {cliente.comuna or '-'}")
            info.append(f"Registrado: {cliente.creado_en.strftime('%Y-%m-%d %H:%M:%S')}\n")

            info.append("🛒 PEDIDOS:\n")
            if cliente.pedidos:
                for p in sorted(cliente.pedidos, key=lambda x: x.fecha or 0, reverse=True):
                    info.append(f"  - Pedido #{p.id} | Nº {p.numero_pedido or '(auto)'} | Fecha: {p.fecha or '-'} | Estado: {p.estado or '-'}")
                    for it in p.items:
                        info.append(f"       • {it.producto or '(producto)'} x {it.unidades or '?'}")
            else:
                info.append("  (sin pedidos registrados)")

            self.detalle.setPlainText("\n".join(info))

    # =======================================================
    # CRUD Clientes
    # =======================================================
    def nuevo_cliente(self):
        nombre, ok = QInputDialog.getText(self, "Nuevo Cliente", "Nombre del cliente:")
        if not ok or not nombre.strip():
            return

        telefono, _ = QInputDialog.getText(self, "Nuevo Cliente", "Teléfono:")
        correo, _ = QInputDialog.getText(self, "Nuevo Cliente", "Correo electrónico:")
        direccion, _ = QInputDialog.getText(self, "Nuevo Cliente", "Dirección:")
        comuna, _ = QInputDialog.getText(self, "Nuevo Cliente", "Comuna:")

        with Session(engine) as s:
            nuevo = Cliente(
                nombre=nombre.strip(),
                telefono=telefono.strip() or None,
                correo=correo.strip() or None,
                direccion=direccion.strip() or None,
                comuna=comuna.strip() or None,
                creado_en=datetime.now(),
            )
            s.add(nuevo)
            s.commit()

        QMessageBox.information(self, "Éxito", f"Cliente '{nombre}' agregado correctamente.")
        self.buscar_clientes()

    def editar_cliente(self):
        if not self.cliente_seleccionado:
            QMessageBox.warning(self, "Atención", "Seleccione un cliente para editar.")
            return

        with Session(engine) as s:
            c = s.get(Cliente, self.cliente_seleccionado)
            if not c:
                return

            nombre, _ = QInputDialog.getText(self, "Editar Cliente", "Nombre:", text=c.nombre or "")
            telefono, _ = QInputDialog.getText(self, "Editar Cliente", "Teléfono:", text=c.telefono or "")
            correo, _ = QInputDialog.getText(self, "Editar Cliente", "Correo:", text=c.correo or "")
            direccion, _ = QInputDialog.getText(self, "Editar Cliente", "Dirección:", text=c.direccion or "")
            comuna, _ = QInputDialog.getText(self, "Editar Cliente", "Comuna:", text=c.comuna or "")

            c.nombre = nombre.strip() or c.nombre
            c.telefono = telefono.strip() or None
            c.correo = correo.strip() or None
            c.direccion = direccion.strip() or None
            c.comuna = comuna.strip() or None
            s.commit()

        QMessageBox.information(self, "Actualizado", f"Cliente '{nombre}' actualizado correctamente.")
        self.buscar_clientes()

    def eliminar_cliente(self):
        if not self.cliente_seleccionado:
            QMessageBox.warning(self, "Atención", "Seleccione un cliente para eliminar.")
            return

        respuesta = QMessageBox.question(
            self, "Confirmar eliminación",
            "¿Seguro que desea eliminar este cliente y todos sus pedidos?",
            QMessageBox.Yes | QMessageBox.No
        )
        if respuesta == QMessageBox.No:
            return

        with Session(engine) as s:
            cliente = s.get(Cliente, self.cliente_seleccionado)
            if cliente:
                s.delete(cliente)
                s.commit()

        QMessageBox.information(self, "Eliminado", "Cliente eliminado correctamente.")
        self.buscar_clientes()

    # =======================================================
    # Crear nuevo pedido
    # =======================================================
    def nuevo_pedido(self):
        # Pregunta si es nuevo cliente o existente
        opcion = QMessageBox.question(
            self,
            "Nuevo Pedido",
            "¿Deseas crear un pedido para un cliente existente?\n(Si eliges 'No', se creará un nuevo cliente primero)",
            QMessageBox.Yes | QMessageBox.No
        )

        if opcion == QMessageBox.No:
            self.nuevo_cliente()

        # Buscar cliente (si no hay uno seleccionado)
        if not self.cliente_seleccionado:
            nombre, ok = QInputDialog.getText(self, "Buscar Cliente", "Nombre o correo:")
            if not ok or not nombre.strip():
                return
            with Session(engine) as s:
                c = s.scalar(
                    select(Cliente).where(
                        (Cliente.nombre.ilike(f"%{nombre}%")) |
                        (Cliente.correo.ilike(f"%{nombre}%"))
                    )
                )
                if not c:
                    QMessageBox.warning(self, "No encontrado", "No se encontró cliente con ese dato.")
                    return
                self.cliente_seleccionado = c.id

        # Generar número automático
        fecha = datetime.now()
        num_auto = f"P{fecha.strftime('%Y%m%d%H%M%S')}"

        producto, _ = QInputDialog.getText(self, "Nuevo Pedido", "Producto:")
        unidades, _ = QInputDialog.getInt(self, "Nuevo Pedido", "Unidades:", 1, 1)
        forma_pago, _ = QInputDialog.getText(self, "Nuevo Pedido", "Forma de pago:")
        estado, _ = QInputDialog.getText(self, "Nuevo Pedido", "Estado (pendiente, entregado, etc.):")

        with Session(engine) as s:
            pedido = Pedido(
                cliente_id=self.cliente_seleccionado,
                numero_pedido=num_auto,
                fecha=fecha,
                forma_pago=forma_pago.strip() or None,
                estado=estado.strip() or "pendiente"
            )
            s.add(pedido)
            s.flush()

            item = ItemPedido(
                pedido_id=pedido.id,
                producto=producto.strip(),
                unidades=unidades
            )
            s.add(item)
            s.commit()

        QMessageBox.information(self, "Pedido creado", f"Pedido {num_auto} creado correctamente.")
        self.mostrar_detalle()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    ventana = CRMApp()
    ventana.show()
    sys.exit(app.exec())
