# src/utils/logging_config.py
import logging
import os
from src.config.settings import settings # Import settings object

def setup_logging():
    """Configura el logging básico para la aplicación."""
    # Ensure log directory exists using the path from settings
    os.makedirs(settings.LOGS_DIR, exist_ok=True)

    # Use ERROR_LOG_FILE property from settings
    error_log_path = settings.ERROR_LOG_FILE

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(), # Muestra logs en consola
            # Note: Basic config might add a default FileHandler. We'll add a specific one for errors below.
        ]
    )
    # Configura el logger de Agno para que también use INFO
    logging.getLogger("agno").setLevel(logging.INFO)

    # Filtro para el FileHandler para que solo escriba errores o superior
    error_handler = logging.FileHandler(error_log_path) # Use path from settings
    error_handler.setLevel(logging.ERROR)
    error_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    error_handler.setFormatter(error_formatter)

    # Añadir el handler de errores al logger root (o a loggers específicos si prefieres)
    logging.getLogger().addHandler(error_handler)

# Llama a la función para configurar el logging cuando se importa este módulo
setup_logging()
logger = logging.getLogger(__name__) # Exporta una instancia de logger para usar en otros módulos
