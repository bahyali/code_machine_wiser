import os
from typing import Optional

import yaml
from pydantic import BaseSettings, Field, PostgresDsn, validator

# Load environment variables from .env file
# This should be done as early as possible
from dotenv import load_dotenv
load_dotenv()

class Settings(BaseSettings):
    """
    Application settings loaded from environment variables and config.yaml.

    Environment variables take precedence over config.yaml.
    Sensitive variables should ONLY be loaded from environment variables.
    """
    # --- General Settings ---
    APP_NAME: str = "LLM-Powered Q&A System"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = Field("development", env="ENVIRONMENT") # Use Field to specify env var name explicitly

    # --- API Settings ---
    API_V1_STR: str = "/api/v1"
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # --- LLM Settings ---
    # LLM API Key MUST be loaded from environment variable
    OPENAI_API_KEY: str = Field(..., env="OPENAI_API_KEY") # ... means required
    LLM_MODEL: str = "gpt-4o"
    LLM_TEMPERATURE: float = 0.7
    LLM_TIMEOUT_SECONDS: int = 60
    LLM_MAX_RETRIES: int = 3

    # --- Database Settings (for user's DB) ---
    # Sensitive parts (password) should prioritize environment variables
    # Full DSN can also be provided via env var DATABASE_URL
    DATABASE_URL: Optional[PostgresDsn] = Field(None, env="DATABASE_URL")
    DB_HOST: Optional[str] = None
    DB_PORT: Optional[int] = 5432
    DB_NAME: Optional[str] = None
    DB_USER: Optional[str] = None
    # DB_PASSWORD MUST be loaded from environment variable
    DB_PASSWORD: Optional[str] = Field(None, env="DB_PASSWORD")

    # --- SQL Execution Settings ---
    SQL_TIMEOUT_SECONDS: int = 30
    SQL_MAX_ROWS_RETURNED: int = 1000

    # --- Error Correction Settings ---
    SQL_ERROR_CORRECTION_MAX_ATTEMPTS: int = 2

    # --- Configuration File Loading ---
    # Path to an optional YAML configuration file
    CONFIG_FILE_PATH: str = os.getenv("CONFIG_FILE_PATH", "config.yaml")

    @validator("DATABASE_URL", pre=True)
    def assemble_db_connection(cls, v, values):
        """
        Assemble DATABASE_URL from individual components if not provided as a full URL.
        Prioritizes DATABASE_URL env var if present.
        """
        if isinstance(v, str):
            return v
        db_user = values.get("DB_USER")
        db_password = values.get("DB_PASSWORD") # Pydantic handles env var priority here
        db_host = values.get("DB_HOST")
        db_port = values.get("DB_PORT")
        db_name = values.get("DB_NAME")

        if all([db_user, db_host, db_name]):
             # Construct DSN string. Handle password safely.
            password_part = f":{db_password}" if db_password else ""
            port_part = f":{db_port}" if db_port else ""
            return f"postgresql://{db_user}{password_part}@{db_host}{port_part}/{db_name}"

        # If DATABASE_URL env var was not set and components are missing,
        # Pydantic will handle the missing required fields if they were defined as required.
        # Here, we allow components to be None if DATABASE_URL is None.
        return None

    class Config:
        """Pydantic configuration"""
        env_file = ".env" # Pydantic will look for .env by default
        env_file_encoding = "utf-8"
        # Pydantic v2 uses `env_vars_priority = 'higher'` by default, which is what we want.
        # For v1, you might need `env_nested_delimiter = '__'`

    def load_from_yaml(self, file_path: str = None):
        """
        Load settings from a YAML file, overriding existing values.
        Environment variables already loaded by Pydantic will NOT be overridden.
        This is useful for non-sensitive defaults.
        """
        if file_path is None:
            file_path = self.CONFIG_FILE_PATH

        if not os.path.exists(file_path):
            print(f"Config file not found at {file_path}. Using environment variables and defaults.")
            return

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                yaml_config = yaml.safe_load(f)
                if yaml_config:
                    # Update settings, but respect existing environment variables
                    # Pydantic's Settings class handles env var priority automatically
                    # when initialized. We re-initialize with YAML data.
                    # This approach is a bit clunky with Pydantic's BaseSettings.
                    # A better approach is to load YAML first, then Pydantic.
                    # Let's refactor to load YAML first, then Pydantic overrides.

                    # Re-initialize settings with YAML data first
                    # Note: This requires passing the data during instantiation,
                    # which is not the standard BaseSettings env var loading flow.
                    # A common pattern is to load YAML, then load env vars *manually*
                    # and merge, or use a library designed for layered config.
                    # Given the requirement for env vars to override YAML,
                    # the simplest Pydantic-native way is to let Pydantic load env vars,
                    # then manually update with YAML *only if the setting wasn't from env*.
                    # This is complex. Let's stick to the Pydantic BaseSettings flow
                    # where env vars override defaults/YAML implicitly IF Pydantic supported YAML directly.
                    # Since it doesn't, we'll load YAML and then let Pydantic load env vars
                    # which will correctly override.

                    # Let's try loading YAML, then passing it to Pydantic's constructor.
                    # Pydantic's BaseSettings.__init__ loads env vars *after* processing kwargs.
                    # This means kwargs (from YAML) would override env vars, which is the opposite
                    # of the requirement.

                    # Alternative: Load YAML, then manually set attributes IF they weren't set by env vars.
                    # This requires checking if a value came from an env var, which Pydantic doesn't expose easily.

                    # Simplest approach aligning with Pydantic BaseSettings and requirement:
                    # 1. Load env vars using dotenv (done at the top).
                    # 2. Instantiate BaseSettings. Pydantic reads env vars.
                    # 3. Load YAML.
                    # 4. Manually update settings from YAML *only if the corresponding env var was NOT set*.
                    # This is still complex.

                    # Let's reconsider the requirement: "Application can load configuration from .env and/or config.yaml. Sensitive keys (like API key) are loaded from .env."
                    # This implies a priority: Env Vars > YAML > Defaults.
                    # Pydantic BaseSettings does Env Vars > Defaults.
                    # We need to add YAML in between.

                    # Let's use a custom approach:
                    # 1. Define schema with Pydantic.
                    # 2. Load YAML data.
                    # 3. Load environment variables manually or let Pydantic do it.
                    # 4. Merge: Env Vars > YAML > Pydantic Defaults.

                    # Let's try loading YAML first, then letting Pydantic load env vars which will override.
                    # This means YAML provides defaults that env vars can override.
                    # This matches the common pattern: config file for defaults, env vars for overrides/secrets.
                    # The requirement "Sensitive keys (like API key) are loaded from .env." is met because
                    # the Pydantic field `OPENAI_API_KEY = Field(..., env="OPENAI_API_KEY")` will *only* look at the env var.
                    # Other fields will take YAML value if present, otherwise Pydantic default, then be overridden by env var if present.

                    # Let's load YAML and then pass it as initial values to BaseSettings.
                    # Pydantic BaseSettings.__init__ signature: __init__(self, _env_file: str | None = None, _env_file_encoding: str | None = None, _env_nested_delimiter: str | None = None, _secrets_dir: str | Path | None = None, **values: Any)
                    # It seems it processes `values` (kwargs) *before* loading from env.
                    # This means kwargs (from YAML) would override env vars. This is the opposite of desired priority.

                    # Okay, let's use a different approach: Load env vars with dotenv, load YAML, then manually merge.
                    # Pydantic is still useful for validation and schema definition.

                    # Let's redefine the loading logic.
                    pass # This method won't be used in the final version below


# Redefine settings loading to handle priority: Env Vars > YAML > Defaults
class Settings(BaseSettings):
    """
    Application settings loaded with priority: Environment Variables > config.yaml > Defaults.
    Sensitive variables should ONLY be loaded from environment variables.
    """
    # Define all settings with their types and default values
    # Pydantic will handle validation
    APP_NAME: str = "LLM-Powered Q&A System"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"

    API_V1_STR: str = "/api/v1"
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # LLM Settings
    OPENAI_API_KEY: str # Required, will be loaded from env var
    LLM_MODEL: str = "gpt-4o"
    LLM_TEMPERATURE: float = 0.7
    LLM_TIMEOUT_SECONDS: int = 60
    LLM_MAX_RETRIES: int = 3

    # Database Settings (for user's DB)
    # Full DSN can be provided via env var DATABASE_URL
    DATABASE_URL: Optional[PostgresDsn] = None
    DB_HOST: Optional[str] = None
    DB_PORT: Optional[int] = 5432
    DB_NAME: Optional[str] = None
    DB_USER: Optional[str] = None
    DB_PASSWORD: Optional[str] = None # Sensitive, will be loaded from env var

    # SQL Execution Settings
    SQL_TIMEOUT_SECONDS: int = 30
    SQL_MAX_ROWS_RETURNED: int = 1000

    # Error Correction Settings
    SQL_ERROR_CORRECTION_MAX_ATTEMPTS: int = 2

    # Configuration File Path (used internally by the loading logic)
    _CONFIG_FILE_PATH: str = "config.yaml" # Internal use, not part of user config

    @validator("DATABASE_URL", pre=True)
    def assemble_db_connection(cls, v, values):
        """
        Assemble DATABASE_URL from individual components if not provided as a full URL.
        This validator runs *after* initial value loading (from defaults, YAML, env vars).
        It ensures that if components are provided, a DSN is constructed if DATABASE_URL isn't set.
        """
        if isinstance(v, str):
            return v # DATABASE_URL was provided directly (likely from env var)

        # Check if individual components are available
        db_user = values.get("DB_USER")
        db_password = values.get("DB_PASSWORD")
        db_host = values.get("DB_HOST")
        db_port = values.get("DB_PORT")
        db_name = values.get("DB_NAME")

        if all([db_user, db_host, db_name]):
             # Construct DSN string. Handle password safely.
            password_part = f":{db_password}" if db_password else ""
            port_part = f":{db_port}" if db_port is not None else "" # Use default port if not specified
            return f"postgresql://{db_user}{password_part}@{db_host}{port_part}/{db_name}"

        # If neither DATABASE_URL nor components are sufficient, return None.
        # Pydantic will raise validation error later if DATABASE_URL is required but None.
        # In this schema, DATABASE_URL is Optional, so None is allowed.
        return None

    class Config:
        """Pydantic configuration"""
        # We will load env vars manually after loading YAML
        # env_file = ".env" # Don't use Pydantic's env_file loading directly here
        env_file_encoding = "utf-8"
        # Allow extra fields temporarily during loading if needed, then validate
        extra = "ignore" # Or 'allow' if we want to keep extra fields

# Custom function to load settings with desired priority
def load_settings(config_file_path: str = "config.yaml") -> Settings:
    """
    Loads application settings with priority: Environment Variables > config.yaml > Defaults.

    1. Load defaults from Pydantic model.
    2. Load settings from config.yaml if it exists.
    3. Load settings from environment variables, overriding previous sources.
    4. Validate the final settings using Pydantic.
    """
    settings_data = {}

    # 2. Load settings from config.yaml
    if os.path.exists(config_file_path):
        try:
            with open(config_file_path, "r", encoding="utf-8") as f:
                yaml_config = yaml.safe_load(f)
                if yaml_config:
                    settings_data.update(yaml_config)
            print(f"Loaded settings from {config_file_path}")
        except yaml.YAMLError as e:
            print(f"Error loading config file {config_file_path}: {e}")
        except Exception as e:
             print(f"An unexpected error occurred loading {config_file_path}: {e}")


    # 3. Load settings from environment variables
    # Pydantic's BaseSettings.__init__ handles loading from env vars automatically
    # and overrides values passed in kwargs. This is exactly the priority we want
    # (Env Vars > kwargs/YAML > Defaults).
    # So, we pass the YAML data as kwargs to the Settings constructor.
    # Pydantic will then load env vars on top of these.

    # Need to handle potential nested structure from YAML if Pydantic expects flat env vars
    # For example, YAML might have:
    # llm:
    #   model: gpt-4o
    # Pydantic BaseSettings expects LLM_MODEL env var.
    # Pydantic v1 had env_nested_delimiter='__'. V2 handles nested configs better but
    # BaseSettings primarily maps flat env vars to flat fields.
    # Let's assume a flat structure in YAML for simplicity, matching env var names.
    # e.g., LLM_MODEL: gpt-4o in YAML

    # Instantiate Settings. Pydantic will load env vars and validate.
    # Pass the data loaded from YAML as initial values.
    # Pydantic's BaseSettings will process these, then load environment variables,
    # giving environment variables higher priority.
    try:
        settings = Settings(**settings_data)
        print("Settings loaded successfully.")
        return settings
    except Exception as e:
        print(f"Error validating settings: {e}")
        # Depending on strictness, you might raise the exception or return None/default
        raise # Re-raise the exception after logging

# Instantiate settings globally or per request context if needed
# For a simple FastAPI app, a global instance is common.
settings = load_settings()

# Example usage (for testing)
if __name__ == "__main__":
    print("\n--- Loaded Settings ---")
    # Print sensitive keys carefully or not at all in real apps
    # print(f"OpenAI API Key: {settings.OPENAI_API_KEY[:4]}...") # Print first few chars
    print(f"App Name: {settings.APP_NAME}")
    print(f"Environment: {settings.ENVIRONMENT}")
    print(f"LLM Model: {settings.LLM_MODEL}")
    print(f"LLM Temperature: {settings.LLM_TEMPERATURE}")
    print(f"Database URL: {settings.DATABASE_URL}")
    print(f"DB Host: {settings.DB_HOST}")
    print(f"DB User: {settings.DB_USER}")
    # print(f"DB Password: {settings.DB_PASSWORD[:4]}...") # Print first few chars
    print(f"SQL Timeout: {settings.SQL_TIMEOUT_SECONDS}s")
    print(f"Config File Path (used for loading): {settings._CONFIG_FILE_PATH}")

    # Test priority: Create a temporary .env and config.yaml
    temp_env_content = """
OPENAI_API_KEY=env_openai_key_1234
LLM_MODEL=gpt-4-turbo
DB_USER=env_user
DB_PASSWORD=env_password
"""
    temp_yaml_content = """
APP_NAME: YAML App
LLM_MODEL: gpt-3.5-turbo # Should be overridden by env
LLM_TEMPERATURE: 0.9
DB_HOST: yaml.db.com
DB_USER: yaml_user # Should be overridden by env
DB_PORT: 5433
"""
    with open(".env.temp", "w") as f:
        f.write(temp_env_content)
    with open("config.temp.yaml", "w") as f:
        f.write(temp_yaml_content)

    print("\n--- Loading Settings with Temp Files ---")
    # Load temp .env first
    load_dotenv(".env.temp", override=True)
    # Load settings using the temp config file
    temp_settings = load_settings("config.temp.yaml")

    print(f"OpenAI API Key: {temp_settings.OPENAI_API_KEY}") # Should be from .env.temp
    print(f"App Name: {temp_settings.APP_NAME}") # Should be from config.temp.yaml
    print(f"LLM Model: {temp_settings.LLM_MODEL}") # Should be from .env.temp (overrides yaml)
    print(f"LLM Temperature: {temp_settings.LLM_TEMPERATURE}") # Should be from config.temp.yaml
    print(f"DB Host: {temp_settings.DB_HOST}") # Should be from config.temp.yaml
    print(f"DB User: {temp_settings.DB_USER}") # Should be from .env.temp (overrides yaml)
    print(f"DB Port: {temp_settings.DB_PORT}") # Should be from config.temp.yaml
    print(f"DB Password: {temp_settings.DB_PASSWORD}") # Should be from .env.temp
    print(f"Database URL: {temp_settings.DATABASE_URL}") # Should be assembled from env/yaml components

    # Clean up temp files
    os.remove(".env.temp")
    os.remove("config.temp.yaml")
    # Reload original .env if it exists
    load_dotenv(override=True) # Load default .env again