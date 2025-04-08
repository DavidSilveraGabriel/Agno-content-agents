# src/config/settings.py
import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import ValidationError # Import ValidationError for explicit handling
from typing import Optional
import sys # Import sys for error exit

# --- Determine Project Root and .env Path ---
# Assumes settings.py is in project_root/src/config/
# Go up two levels from the current file's directory to reach the project root
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
ENV_FILE_PATH = os.path.join(PROJECT_ROOT, '.env')

# Check if the .env file actually exists at the calculated path
if not os.path.exists(ENV_FILE_PATH):
    print(f"Warning: '.env' file not found at the expected location: {ENV_FILE_PATH}")
    # You might decide to raise an error or proceed using only environment variables
    # For now, we'll let pydantic-settings try (it might find vars in the environment)


class Settings(BaseSettings):
    """
    Loads and validates application settings from environment variables
    and a .env file located in the project root.
    """

    # Configure Pydantic settings loader
    model_config = SettingsConfigDict(
        # Explicitly provide the full path to the .env file
        env_file=ENV_FILE_PATH,
        env_file_encoding='utf-8',
        # Ignore extra variables found in the environment or .env file
        # that are not defined in this Settings model. Prevents errors.
        extra='ignore'
    )

    # --- API Keys (Required) ---
    # Pydantic will raise an error during instantiation if these are missing
    # either in the environment or the specified .env file.
    GOOGLE_API_KEY: str
    FIRECRAWL_API_KEY: str
    SERPER_API_KEY: str # For the ResearcherAgent's search capability

    # --- API Keys (Optional) ---
    # Define keys present in .env but maybe not used everywhere yet.
    # Use Optional[str] = None if the key might be missing or is not always needed.
    SERPAPI_API_KEY: Optional[str] = None # Present in your .env, added here as optional
    # EXA_API_KEY: Optional[str] = None # Example if you add it later

    # --- Directories (Provide sensible defaults) ---
    # These can still be overridden by environment variables or .env entries
    LOGS_DIR: str = os.path.join(PROJECT_ROOT, "logs") # Use absolute paths based on root
    OUTPUT_DIR: str = os.path.join(PROJECT_ROOT, "output") # Use absolute paths based on root

    # --- Derived paths (Calculated after loading) ---
    @property
    def ERROR_LOG_FILE(self) -> str:
        """Provides the full path to the error log file."""
        # Ensure the base LOGS_DIR exists before trying to join path
        # (Directory creation happens after settings instantiation)
        return os.path.join(self.LOGS_DIR, "error.log")

# --- Instantiate Settings and Handle Errors ---
try:
    # Create a single instance of the settings to be imported by other modules
    settings = Settings()
    # Print a success message or log it (optional)
    print("✅ Settings loaded successfully.")
    # You could add: print(f" - Logs directory: {settings.LOGS_DIR}")
    # You could add: print(f" - Output directory: {settings.OUTPUT_DIR}")

except ValidationError as e:
    print("\n❌ ERROR: Failed to load or validate settings!")
    print("Please check your environment variables or the '.env' file.")
    print(f"    (.env expected location: {ENV_FILE_PATH})")
    print("\nMissing or invalid settings:")
    for error in e.errors():
        # error['loc'] is a tuple, e.g., ('GOOGLE_API_KEY',)
        field = error['loc'][0] if error['loc'] else 'Unknown Field'
        print(f"  - {field}: {error['msg']}")
    # Exit the application if critical settings are missing
    sys.exit(1) # Stop execution


# --- Create Log/Output Directories ---
# It's good practice to ensure these exist right after settings are loaded.
try:
    os.makedirs(settings.LOGS_DIR, exist_ok=True)
    os.makedirs(settings.OUTPUT_DIR, exist_ok=True)
    # print("✅ Log and Output directories ensured.") # Optional confirmation
except OSError as e:
    print(f"Warning: Could not create directories ({settings.LOGS_DIR}, {settings.OUTPUT_DIR}): {e}")
    # Decide if this is a critical error or just a warning

# --- Validation Example (Optional) ---
# You could add custom validation logic here if needed, e.g.,
# if not settings.SOME_OTHER_SETTING.startswith("expected_prefix"):
#     raise ValueError("SOME_OTHER_SETTING has an invalid format.")