# backup.py
import os, subprocess
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
BACKUP_DIR = os.getenv("BACKUP_DIR", r"C:\Users\Public\BackupsCRM")
MYSQLDUMP = os.getenv("MYSQLDUMP", r"C:\Program Files\MySQL\MySQL Server 8.0\bin\mysqldump.exe")

def _ensure_dir(path: str):
    Path(path).mkdir(parents=True, exist_ok=True)

def _filename(db: str) -> str:
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    return f"{db}_backup_{ts}.sql"

def create_backup() -> str:
    """
    Genera un dump .sql de DB_NAME en BACKUP_DIR y retorna la ruta creada.
    Lanza RuntimeError con mensaje claro si algo falla.
    """
    if not DB_NAME or not DB_USER:
        raise RuntimeError("Configura DB_NAME/DB_USER en el archivo .env.")

    _ensure_dir(BACKUP_DIR)
    outfile = os.path.join(BACKUP_DIR, _filename(DB_NAME))

    cmd = [
        MYSQLDUMP,
        f"--host={DB_HOST}",
        f"--port={DB_PORT}",
        f"--user={DB_USER}",
        f"--password={DB_PASS}",
        "--routines", "--events",
        "--single-transaction", "--quick",
        "--databases", DB_NAME
    ]

    try:
        with open(outfile, "wb") as f:
            proc = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, shell=False)
    except FileNotFoundError:
        raise RuntimeError("No se encontró mysqldump. Revisa MYSQLDUMP en .env o agrega MySQL\\bin al PATH.")

    if proc.returncode != 0:
        # Limpia archivo vacío si falló
        try:
            if os.path.exists(outfile) and os.path.getsize(outfile) == 0:
                os.remove(outfile)
        except Exception:
            pass
        raise RuntimeError(f"mysqldump falló: {proc.stderr.decode(errors='ignore')}")

    if os.path.getsize(outfile) < 1024:
        raise RuntimeError(f"Respaldo sospechosamente pequeño: {outfile}")

    return outfile

def backup_once_per_day(flag_dir: str = None) -> str | None:
    """
    Evita repetir respaldo el mismo día. Usa %APPDATA%/crm_pyme/backup_flags
    Retorna la ruta del backup si lo creó, o None si ya existía flag hoy.
    """
    if flag_dir is None:
        flag_dir = os.path.join(os.getenv("APPDATA", str(Path.home())), "crm_pyme", "backup_flags")
    _ensure_dir(flag_dir)

    today = datetime.now().strftime("%Y-%m-%d")
    flag = os.path.join(flag_dir, f"{today}.flag")

    if os.path.exists(flag):
        return None

    ruta = create_backup()
    Path(flag).write_text("ok", encoding="utf-8")
    return ruta
