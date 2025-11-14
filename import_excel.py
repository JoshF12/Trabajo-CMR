import pandas as pd
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from models import Base, Cliente, Pedido, ItemPedido
from datetime import datetime

# Configurar conexión
DB_URL = "mysql+pymysql://crm_user:TuPasswordFuerte123!@localhost:3306/crm_pyme?charset=utf8mb4"
engine = create_engine(DB_URL)

# 📄 Ruta del archivo Excel (ajustada a tu proyecto)
excel_path = r"C:\Users\diego\OneDrive\Desktop\Ing. Software Proyecto\utem.proyecto sercotec.xlsx"

# Leer el Excel
xls = pd.ExcelFile(excel_path)
sheet = xls.sheet_names[0]
raw = xls.parse(sheet)

# Limpieza básica (como el Excel tenía títulos en las primeras filas)
header = raw.iloc[0].tolist()
df = raw[3:].copy()
df.columns = header + raw.columns[len(header):].tolist()[:len(raw.columns)-len(header)]
df = df.loc[:, ~df.columns.duplicated()]

# Renombrar columnas para que coincidan con el modelo
COLS = {
    'FECHA': 'fecha',
    'CANAL DE VENTA': 'canal',
    'PEDIDO': 'numero_pedido',
    'CLIENTE': 'cliente_nombre',
    'TELÉFONO': 'telefono',
    'DIRECCIÓN': 'direccion',
    'COMUNA': 'comuna',
    'PRODUCTOS': 'producto',
    'UNID': 'unidades',
    'FORMA DE PAGO': 'forma_pago',
    'BOLETA': 'tipo_doc',
    'PAGO': 'pagado',
    'SALDO': 'saldo',
    'DESPACHO': 'despacho',
    'CORREO': 'correo',
    'ESTADO': 'estado',
}

df = df.rename(columns={k: v for k, v in COLS.items() if k in df.columns})

# Convertir tipos
def parse_date(x):
    if pd.isna(x):
        return None
    try:
        return pd.to_datetime(x, dayfirst=True, errors='coerce')
    except Exception:
        return None

df['fecha'] = df['fecha'].apply(parse_date)

for money in ['pagado', 'saldo']:
    if money in df.columns:
        df[money] = (df[money]
                     .astype(str)
                     .str.replace('.', '', regex=False)
                     .str.replace(',', '.', regex=False))
        df[money] = pd.to_numeric(df[money], errors='coerce')

if 'unidades' in df.columns:
    df['unidades'] = pd.to_numeric(df['unidades'], errors='coerce').astype('Int64')

# Crear tablas si no existen
Base.metadata.create_all(engine)

# Insertar datos en la base
with Session(engine) as session:
    for _, row in df.iterrows():
        nombre = str(row.get('cliente_nombre') or '').strip()
        if not nombre:
            continue

        telefono = str(row.get('telefono') or '') if not pd.isna(row.get('telefono')) else None
        correo = str(row.get('correo') or '') if not pd.isna(row.get('correo')) else None
        direccion = str(row.get('direccion') or '') if not pd.isna(row.get('direccion')) else None
        comuna = str(row.get('comuna') or '') if not pd.isna(row.get('comuna')) else None

        # Buscar cliente existente
        cli = session.scalar(
            select(Cliente).where(
                (Cliente.nombre == nombre) &
                (Cliente.telefono == telefono) &
                (Cliente.correo == correo)
            )
        )

        # Crear nuevo cliente si no existe
        if not cli:
            cli = Cliente(
                nombre=nombre,
                telefono=telefono,
                correo=correo,
                direccion=direccion,
                comuna=comuna
            )
            session.add(cli)
            session.flush()

        # Crear pedido
        pedido = Pedido(
            cliente_id=cli.id,
            numero_pedido=str(row.get('numero_pedido')) if not pd.isna(row.get('numero_pedido')) else None,
            fecha=pd.Timestamp.to_pydatetime(row['fecha']) if pd.notna(row['fecha']) else None,
            canal=str(row.get('canal')) if not pd.isna(row.get('canal')) else None,
            forma_pago=str(row.get('forma_pago')) if not pd.isna(row.get('forma_pago')) else None,
            tipo_doc=str(row.get('tipo_doc')) if not pd.isna(row.get('tipo_doc')) else None,
            pagado=float(row.get('pagado')) if pd.notna(row.get('pagado')) else None,
            saldo=float(row.get('saldo')) if pd.notna(row.get('saldo')) else None,
            despacho=str(row.get('despacho')) if not pd.isna(row.get('despacho')) else None,
            estado=str(row.get('estado')) if not pd.isna(row.get('estado')) else None
        )
        session.add(pedido)
        session.flush()

        # Crear item asociado
        item = ItemPedido(
            pedido_id=pedido.id,
            producto=str(row.get('producto')) if not pd.isna(row.get('producto')) else None,
            unidades=int(row.get('unidades')) if pd.notna(row.get('unidades')) else None
        )
        session.add(item)

    session.commit()

print("✅ Importación completa: clientes, pedidos e items cargados en MySQL.")
