import pandas as pd
from sqlalchemy.orm import Session
from datetime import datetime

from db import SessionLocal
from models import Cliente, Pedido, ItemPedido


def generar_codigo_pedido(fecha: datetime, correlativo: int) -> str:
    """Genera un código de pedido interno si el Excel no trae uno."""
    return "P" + fecha.strftime("%Y%m%d") + f"-{correlativo:03d}"


def limpiar_nan(valor, es_telefono: bool = False) -> str:
    """
    Limpia celdas del Excel:
    - Convierte NaN / None a "".
    - Convierte números a string limpio.
    - Para teléfonos:
        * Elimina ".0"
        * Corrige notación científica (9.5e+08 -> 950000000)
        * Quita espacios, comas y guiones.
    """
    if valor is None:
        return ""

    try:
        if pd.isna(valor):
            return ""
    except Exception:
        pass

    txt = str(valor).strip()

    if txt.lower() == "nan":
        return ""

    if es_telefono:
        if txt.endswith(".0"):
            txt = txt[:-2]

        if "e+" in txt.lower() or "e-" in txt.lower():
            try:
                txt = str(int(float(txt)))
            except Exception:
                pass

        txt = txt.replace(" ", "").replace(",", "").replace("-", "")

    return txt


def a_entero_o_cero(valor) -> int:
    """
    Convierte cualquier valor en entero seguro:
    - Si es NaN, "", None → 0
    - Si viene como float o string "10.0" → 10
    - Si viene como "NaN" → 0
    """
    try:
        if valor is None:
            return 0

        if isinstance(valor, float) and pd.isna(valor):
            return 0

        txt = str(valor).strip()
        if not txt or txt.lower() == "nan":
            return 0

        return int(float(txt))
    except Exception:
        return 0


def limpiar_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    df = df.dropna(how="all").copy()

    cols_ffill_global = [
        "fecha", "canal_venta", "numero_pedido",
        "forma_pago", "tipo_documento", "pago",
        "saldo", "despacho", "estado"
    ]
    for col in cols_ffill_global:
        if col in df.columns:
            df[col] = df[col].ffill()

    cleaned_rows = []
    current_cliente = None
    contactos_por_cliente: dict[str, dict[str, str]] = {}

    for _, original_row in df.iterrows():
        row = original_row.copy()

        cliente_str = limpiar_nan(row.get("cliente"))

        if cliente_str:
            current_cliente = cliente_str

            info = contactos_por_cliente.get(current_cliente, {})
            for campo in ["telefono", "direccion", "comuna", "correo"]:
                if campo in df.columns:
                    if campo == "telefono":
                        val = limpiar_nan(row.get(campo), es_telefono=True)
                    else:
                        val = limpiar_nan(row.get(campo))
                    if val:
                        info[campo] = val
            contactos_por_cliente[current_cliente] = info

        elif current_cliente:
            row["cliente"] = current_cliente

        if current_cliente and current_cliente in contactos_por_cliente:
            info = contactos_por_cliente[current_cliente]
            for campo in ["telefono", "direccion", "comuna", "correo"]:
                if campo in df.columns:
                    if campo == "telefono":
                        val = limpiar_nan(row.get(campo), es_telefono=True)
                    else:
                        val = limpiar_nan(row.get(campo))
                    if not val and campo in info:
                        row[campo] = info[campo]
                    else:
                        row[campo] = val
        else:
            for campo in ["telefono", "direccion", "comuna", "correo"]:
                if campo in df.columns:
                    row[campo] = limpiar_nan(
                        row.get(campo),
                        es_telefono=(campo == "telefono")
                    )

        for campo_texto in [
            "canal_venta", "numero_pedido", "forma_pago",
            "tipo_documento", "despacho", "estado", "producto"
        ]:
            if campo_texto in df.columns:
                row[campo_texto] = limpiar_nan(row.get(campo_texto))

        cleaned_rows.append(row)

    cleaned_df = pd.DataFrame(cleaned_rows)
    return cleaned_df


def importar_excel(ruta_excel: str):
    df_raw = pd.read_excel(ruta_excel, header=None)

    header_rows = df_raw.index[df_raw.iloc[:, 0] == "FECHA"].tolist()
    if not header_rows:
        raise ValueError("No se encontró una fila con 'FECHA' como encabezado.")
    header_row = header_rows[0]

    df = pd.read_excel(ruta_excel, header=header_row)

    df = df.rename(columns={
        "FECHA": "fecha",
        "CANAL DE VENTA": "canal_venta",
        "PEDIDO": "numero_pedido",
        "CLIENTE": "cliente",
        "TELÉFONO": "telefono",
        "DIRECCIÓN": "direccion",
        "COMUNA": "comuna",
        "PRODUCTOS": "producto",
        "UNID": "unidades",
        "FORMA DE PAGO": "forma_pago",
        "BOLETA": "tipo_documento",
        "PAGO": "pago",
        "SALDO": "saldo",
        "DESPACHO": "despacho",
        "CORREO": "correo",
        "ESTADO": "estado",
    })

    df = limpiar_dataframe(df)

    session: Session = SessionLocal()

    try:
        correlativo_interno = 1

        for _, row in df.iterrows():
            cliente_nombre = limpiar_nan(row.get("cliente"))
            producto_nombre = limpiar_nan(row.get("producto"))

            if not cliente_nombre and not producto_nombre:
                continue

            if pd.isna(row.get("fecha")):
                continue

            cliente = (
                session.query(Cliente)
                .filter(Cliente.nombre == cliente_nombre)
                .first()
            )

            tel = limpiar_nan(row.get("telefono"), es_telefono=True)
            cor = limpiar_nan(row.get("correo"))
            dir_ = limpiar_nan(row.get("direccion"))
            com = limpiar_nan(row.get("comuna"))

            if not cliente:
                cliente = Cliente(
                    nombre=cliente_nombre,
                    telefono=tel,
                    correo=cor,
                    direccion=dir_,
                    comuna=com,
                )
                session.add(cliente)
                session.flush()
            else:
                if tel:
                    cliente.telefono = tel
                if cor:
                    cliente.correo = cor
                if dir_:
                    cliente.direccion = dir_
                if com:
                    cliente.comuna = com

            fecha_pedido = pd.to_datetime(row.get("fecha")).to_pydatetime()

            numero_pedido = limpiar_nan(row.get("numero_pedido"))
            if not numero_pedido:
                continue

            pedido = (
                session.query(Pedido)
                .filter(Pedido.numero_pedido == numero_pedido)
                .first()
            )

            if not pedido:
                pedido = Pedido(
                    numero_pedido=numero_pedido,
                    fecha_pedido=fecha_pedido,
                    canal_venta=limpiar_nan(row.get("canal_venta")),
                    forma_pago=limpiar_nan(row.get("forma_pago")),
                    tipo_documento=limpiar_nan(row.get("tipo_documento")),
                    monto_pagado=a_entero_o_cero(row.get("pago")),
                    saldo=a_entero_o_cero(row.get("saldo")),
                    estado=limpiar_nan(row.get("estado")),
                    cliente_id=cliente.id,
                )
                session.add(pedido)
                session.flush()
            else:
                if not pedido.canal_venta:
                    pedido.canal_venta = limpiar_nan(row.get("canal_venta"))
                if not pedido.forma_pago:
                    pedido.forma_pago = limpiar_nan(row.get("forma_pago"))
                if not pedido.tipo_documento:
                    pedido.tipo_documento = limpiar_nan(row.get("tipo_documento"))

            if not producto_nombre:
                continue

            unidades = a_entero_o_cero(row.get("unidades"))
            if unidades <= 0:
                unidades = 1

            item = ItemPedido(
                producto=producto_nombre,
                cantidad=unidades,
                precio_unitario=None,
                total_item=None,
                pedido_id=pedido.id,
            )
            session.add(item)

        session.commit()
        print("Importación completa.")

    except Exception as exc:
        session.rollback()
        print("Error al importar Excel:", exc)
        raise
    finally:
        session.close()


if __name__ == "__main__":
    ruta = input("Ruta del Excel a importar: ").strip().strip('"')
    importar_excel(ruta)
 
