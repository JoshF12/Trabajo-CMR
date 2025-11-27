# db.py
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Carpeta base del proyecto
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Archivo físico de la base de datos SQLite
DB_PATH = os.path.join(BASE_DIR, "raiz_diseno.db")

# URL para SQLAlchemy (sqlite:///ruta/al/archivo.db)
DB_URL = "sqlite:///" + DB_PATH.replace("\\", "/")

engine = create_engine(DB_URL, echo=False, future=True)
SessionLocal = sessionmaker(bind=engine)
