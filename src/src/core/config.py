import os
from dotenv import load_dotenv
import yaml
import logging

load_dotenv()

# Define a mapping for log level strings to logging module constants
LOG_LEVEL_MAP = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}

class Settings:
    # Load settings from environment variables or config file
    # Environment variables take precedence

    # LLM Settings
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-4o") # Default to gpt-4o as per requirements

    # Database Settings (User's DB)
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://user:password@host:port/dbname") # Example format

    # Logging Settings
    LOG_LEVEL: int = LOG_LEVEL_MAP.get(os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO)
    LOG_FORMAT: str = os.getenv("LOG_FORMAT", "json") # 'json' or 'basic'

    # SQL Generation Settings
    SQL_MAX_RETRY_ATTEMPTS: int = int(os.getenv("SQL_MAX_RETRY_ATTEMPTS", 3))
    SQL_QUERY_LOG_MAX_LENGTH: int = int(os.getenv("SQL_QUERY_LOG_MAX_LENGTH", 1000)) # Max length of SQL query to log

    # LLM Interaction Settings
    LLM_LOG_PROMPT_RESPONSE_CONTENT: bool = os.getenv("LLM_LOG_PROMPT_RESPONSE_CONTENT", "False").lower() == "true"
    LLM_LOG_CONTENT_MAX_LENGTH: int = int(os.getenv("LLM_LOG_CONTENT_MAX_LENGTH", 500)) # Max length of LLM content to log


    # Load from config.yaml if it exists and env vars are not set
    CONFIG_FILE = os.getenv("CONFIG_FILE", "config.yaml")
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            config_data = yaml.safe_load(f)
            if config_data:
                # Override defaults only if env var is not set
                settings_dict = Settings.__dict__
                for key, default_value in settings_dict.items():
                    if not key.startswith('__') and not callable(default_value):
                        env_var = os.getenv(key.upper())
                        if env_var is None and key in config_data:
                             # Handle specific types if necessary, e.g., boolean
                            if isinstance(settings_dict[key], bool):
                                setattr(Settings, key, str(config_data[key]).lower() == 'true')
                            elif isinstance(settings_dict[key], int):
                                setattr(Settings, key, int(config_data[key]))
                            else:
                                setattr(Settings, key, config_data[key])

settings = Settings()

# Note: Logging configuration is handled in src/core/logging_config.py
# to ensure it's set up early in the application lifecycle.