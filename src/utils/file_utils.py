# utils/file_utils.py
import json
import os
from pathlib import Path
from src.utils.logging_config import logger # Corrected logger import
from src.config.settings import settings # Import settings object

def save_json(data: dict, filename: str):
    """Guarda un diccionario como archivo JSON."""
    output_path = Path(settings.OUTPUT_DIR) / f"{filename}.json" # Use settings.OUTPUT_DIR
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        logger.info(f"Archivo JSON guardado exitosamente en: {output_path}")
    except Exception as e:
        logger.error(f"Error al guardar el archivo JSON {output_path}: {e}")

def save_markdown(content: str, filename: str):
    """Guarda contenido de texto como archivo Markdown."""
    output_path = Path(settings.OUTPUT_DIR) / f"{filename}.md" # Use settings.OUTPUT_DIR
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
        logger.info(f"Archivo Markdown guardado exitosamente en: {output_path}")
    except Exception as e:
        logger.error(f"Error al guardar el archivo Markdown {output_path}: {e}")
