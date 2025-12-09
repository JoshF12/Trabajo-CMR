import os
import shutil

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from config import get_backup_folder
from db import DB_PATH, SessionLocal
from models import Cliente, Pedido, ItemPedido


def hacer_respaldo():
    """
    Crea (o reemplaza) un único archivo de respaldo de la base de datos SQLite
    en la carpeta de respaldo configurada.
    """
    backup_folder = get_backup_folder()
    if not backup_folder:
        raise RuntimeError("No hay carpeta de respaldo configurada.")

    if not os.path.exists(DB_PATH):
        raise RuntimeError(
            f"No se encontró la base de datos en {DB_PATH}.\n"
            "Ejecuta primero el sistema para crearla."
        )

    os.makedirs(backup_folder, exist_ok=True)

    # Siempre el mismo nombre: se sobrescribe el archivo anterior
    destino = os.path.join(backup_folder, "backup_raiz_diseno.db")
    shutil.copy2(DB_PATH, destino)
    print("Respaldo generado en:", destino)


def restaurar_si_no_existe():
    """
    Si la base de datos principal no existe pero sí existe el archivo
    backup_raiz_diseno.db en la carpeta de respaldo, lo copia como DB actual.

    (Esta función ya no se llama automáticamente al inicio, pero
    la dejamos por si quieres usarla manualmente en el futuro).
    """
    backup_folder = get_backup_folder()
    if not backup_folder:
        # No hay carpeta configurada: no hacemos nada
        return

    # Si ya existe la BD, no tocamos nada
    if os.path.exists(DB_PATH):
        return

    ruta_backup = os.path.join(backup_folder, "backup_raiz_diseno.db")
    if not os.path.exists(ruta_backup):
        # No hay backup para restaurar
        return

    # Asegurar carpeta donde va la DB
    db_dir = os.path.dirname(DB_PATH)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)

    shutil.copy2(ruta_backup, DB_PATH)
    print("Base de datos restaurada automáticamente desde:", ruta_backup)


def importar_respaldo(ruta_backup: str) -> dict:
    """
    Importa datos desde un archivo de base de datos SQLite externo (respaldo)
    hacia la BD actual, SIN borrar lo que ya existe.

    - Si un pedido con el mismo numero_pedido ya existe, se omite.
    - Los clientes se emparejan por RUT (si tiene) o por nombre.
    - Los ítems se consideran duplicados si coinciden pedido + producto + cantidad + precio.

    Devuelve un diccionario con conteo de registros nuevos.
    """
    if not os.path.exists(ruta_backup):
        raise RuntimeError(f"No se encontró el archivo de respaldo: {ruta_backup}")

    # Engine / sesión para la BD de respaldo
    engine_backup = create_engine(
        "sqlite:///" + ruta_backup.replace("\\", "/"),
        echo=False,
        future=True,
    )
    SessionBackup = sessionmaker(bind=engine_backup)

    session_dest = SessionLocal()
    session_src = SessionBackup()

    clientes_nuevos = 0
    pedidos_nuevos = 0
    items_nuevos = 0

    try:
        # ----------------------------
        # 1) Importar / emparejar clientes
        # ----------------------------
        mapa_clientes_id: dict[int, int] = {}

        clientes_src = session_src.query(Cliente).all()
        for c_src in clientes_src:
            destino = None

            # Primero probamos por RUT (si tiene)
            rut_src = (c_src.rut or "").strip()
            if rut_src:
                destino = (
                    session_dest.query(Cliente)
                    .filter(Cliente.rut == rut_src)
                    .first()
                )

            # Si no se encontró por RUT, probamos por nombre
            if destino is None:
                destino = (
                    session_dest.query(Cliente)
                    .filter(Cliente.nombre == (c_src.nombre or ""))
                    .first()
                )

            if destino is None:
                # Cliente nuevo → lo creamos
                destino = Cliente(
                    nombre=c_src.nombre,
                    rut=c_src.rut,
                    telefono=c_src.telefono,
                    correo=c_src.correo,
                    direccion=c_src.direccion,
                    comuna=c_src.comuna,
                )
                session_dest.add(destino)
                session_dest.flush()
                clientes_nuevos += 1
            else:
                # Opcional: actualizar campos vacíos con lo que viene del backup
                if not destino.telefono and c_src.telefono:
                    destino.telefono = c_src.telefono
                if not destino.correo and c_src.correo:
                    destino.correo = c_src.correo
                if not destino.direccion and c_src.direccion:
                    destino.direccion = c_src.direccion
                if not destino.comuna and c_src.comuna:
                    destino.comuna = c_src.comuna

            mapa_clientes_id[c_src.id] = destino.id

        # ----------------------------
        # 2) Importar pedidos
        # ----------------------------
        mapa_pedidos_id: dict[int, int] = {}

        pedidos_src = session_src.query(Pedido).all()
        for p_src in pedidos_src:
            numero = (p_src.numero_pedido or "").strip()
            if not numero:
                continue

            # ¿Ya existe un pedido con ese número?
            p_dest = (
                session_dest.query(Pedido)
                .filter(Pedido.numero_pedido == numero)
                .first()
            )

            if p_dest is None:
                p_dest = Pedido(
                    numero_pedido=p_src.numero_pedido,
                    fecha_pedido=p_src.fecha_pedido,
                    canal_venta=p_src.canal_venta,
                    forma_pago=p_src.forma_pago,
                    tipo_documento=p_src.tipo_documento,
                    monto_pagado=p_src.monto_pagado,
                    saldo=p_src.saldo,
                    despacho=p_src.despacho,
                    estado=p_src.estado,
                    cliente_id=mapa_clientes_id.get(p_src.cliente_id),
                )
                session_dest.add(p_dest)
                session_dest.flush()
                pedidos_nuevos += 1

            mapa_pedidos_id[p_src.id] = p_dest.id

        # ----------------------------
        # 3) Importar ítems de pedido
        # ----------------------------
        items_src = session_src.query(ItemPedido).all()
        for it_src in items_src:
            nuevo_pedido_id = mapa_pedidos_id.get(it_src.pedido_id)
            if nuevo_pedido_id is None:
                continue

            # ¿Ya existe ese ítem en el pedido destino?
            existente = (
                session_dest.query(ItemPedido)
                .filter(
                    ItemPedido.pedido_id == nuevo_pedido_id,
                    ItemPedido.producto == it_src.producto,
                    ItemPedido.cantidad == it_src.cantidad,
                    ItemPedido.precio_unitario == it_src.precio_unitario,
                )
                .first()
            )

            if existente:
                continue

            it_dest = ItemPedido(
                producto=it_src.producto,
                cantidad=it_src.cantidad,
                precio_unitario=it_src.precio_unitario,
                total_item=it_src.total_item,
                pedido_id=nuevo_pedido_id,
            )
            session_dest.add(it_dest)
            items_nuevos += 1

        session_dest.commit()

        return {
            "clientes_nuevos": clientes_nuevos,
            "pedidos_nuevos": pedidos_nuevos,
            "items_nuevos": items_nuevos,
        }

    except Exception:
        session_dest.rollback()
        raise
    finally:
        session_src.close()
        session_dest.close()


if __name__ == "__main__":
    hacer_respaldo()
