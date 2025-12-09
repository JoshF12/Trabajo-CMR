import os
import sys
import json

# ============================================
#  BASE_DIR distinto si está en .exe (PyInstaller)
# ============================================
if getattr(sys, "frozen", False):
    # Carpeta donde está el ejecutable
    BASE_DIR = os.path.dirname(sys.executable)
else:
    # Carpeta del script .py (modo desarrollo)
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CONFIG_JSON_PATH = os.path.join(BASE_DIR, "config.json")


def load_settings() -> dict:
    """Carga configuración desde config.json (carpeta de backup, etc.)."""
    if not os.path.exists(CONFIG_JSON_PATH):
        return {}
    try:
        with open(CONFIG_JSON_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_settings(settings: dict):
    """Guarda configuración en config.json."""
    with open(CONFIG_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=4, ensure_ascii=False)


def get_backup_folder() -> str | None:
    """Devuelve la carpeta de backup configurada o None si no existe."""
    settings = load_settings()
    return settings.get("backup_folder")
