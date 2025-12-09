import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# ============================================
#  BASE_DIR distinto si está en .exe (PyInstaller)
# ============================================
if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Archivo físico de la base de datos SQLite
DB_PATH = os.path.join(BASE_DIR, "raiz_diseno.db")

# URL para SQLAlchemy (sqlite:///ruta/al/archivo.db)
DB_URL = "sqlite:///" + DB_PATH.replace("\\", "/")

engine = create_engine(DB_URL, echo=False, future=True)
SessionLocal = sessionmaker(bind=engine)
