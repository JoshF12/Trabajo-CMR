# backup.py
import os
import shutil

from config import get_backup_folder
from db import DB_PATH


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

    Esto permite que, en un PC nuevo, con solo tener el backup en OneDrive
    y abrir la app, se restaure automáticamente la información.
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


if __name__ == "__main__":
    hacer_respaldo()
