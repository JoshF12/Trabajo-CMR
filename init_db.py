# init_db.py
from db import engine
from models import Base

def init_db():
    Base.metadata.create_all(engine)
    print("Base creada/actualizada correctamente.")

if __name__ == "__main__":
    init_db()
