# src/config/settings.py
import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    """Loads and validates application settings from environment variables."""

    # Load from .env file
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    # API Keys
    GOOGLE_API_KEY: str
    FIRECRAWL_API_KEY: str
    # EXA_API_KEY: Optional[str] = None # Optional, if needed later

    # Directories (provide default values)
    LOGS_DIR: str = "logs"
    OUTPUT_DIR: str = "output"

    # Derived paths (calculated after loading)
    @property
    def ERROR_LOG_FILE(self) -> str:
        return os.path.join(self.LOGS_DIR, "error.log")

# Create a single instance of the settings to be imported by other modules
settings = Settings()

# --- Optional: Create directories if they don't exist ---
# It's often good practice to ensure these exist when settings are loaded.
# os.makedirs(settings.LOGS_DIR, exist_ok=True)
# os.makedirs(settings.OUTPUT_DIR, exist_ok=True)

# --- Validation (Pydantic handles required fields automatically) ---
# You could add custom validation here if needed.
