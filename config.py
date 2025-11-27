# config.py
import os
import json

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
