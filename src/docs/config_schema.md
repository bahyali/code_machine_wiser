# Configuration Schema

The application loads configuration settings from the following sources, in order of precedence:

1.  **Environment Variables:** Values set in the operating system's environment.
2.  **`.env` file:** Variables defined in a `.env` file in the project root (loaded by `python-dotenv`).
3.  **`config.yaml` file:** Values defined in the `config.yaml` file (or specified by the `CONFIG_FILE_PATH` environment variable).
4.  **Default Values:** Default values defined in the `src/core/config.py` code.

**Environment variables take the highest precedence.** This is the recommended way to manage sensitive information like API keys and database passwords.

The `config.yaml` file is optional and can be used to set non-sensitive default parameters for various parts of the application.

---

## `config.yaml` Structure and Settings

The `config.yaml` file should be a flat structure (key-value pairs) where keys correspond to the setting names defined in the `Settings` class in `src/core/config.py`.

Here are the expected settings and their types, along with a description. Note that environment variables using the exact same name (uppercase) will override these values.

```yaml
# Example config.yaml structure

# --- General Settings ---
# Application name (string)
# APP_NAME: LLM-Powered Q&A System

# Application version (string)
# APP_VERSION: 1.0.0

# Application environment (string, e.g., development, staging, production)
# ENVIRONMENT: development # Overridden by ENVIRONMENT env var

# --- API Settings ---
# Base path for API v1 endpoints (string)
# API_V1_STR: /api/v1

# Host interface to bind the FastAPI application to (string)
# HOST: 0.0.0.0

# Port to run the FastAPI application on (integer)
# PORT: 8000

# --- LLM Settings ---
# LLM_MODEL: gpt-4o # Name of the LLM model to use (string)
# LLM_TEMPERATURE: 0.7 # LLM temperature for response randomness (float)
# LLM_TIMEOUT_SECONDS: 60 # Timeout for LLM API calls in seconds (integer)
# LLM_MAX_RETRIES: 3 # Maximum retries for failed LLM API calls (integer)

# Note: OPENAI_API_KEY MUST be set via environment variable and is not read from config.yaml.

# --- Database Settings (for the user's PostgreSQL DB) ---
# These settings are used to construct the database connection URL if DATABASE_URL env var is not set.
# DB_HOST: localhost # Database host (string)
# DB_PORT: 5432 # Database port (integer)
# DB_NAME: mydatabase # Database name (string)
# DB_USER: myuser # Database user (string)

# Note: DB_PASSWORD MUST be set via environment variable and is not read from config.yaml.
# Note: If DATABASE_URL environment variable is set, these individual DB_* settings from config.yaml are ignored for connection URL assembly.

# --- SQL Execution Settings ---
# SQL_TIMEOUT_SECONDS: 30 # Timeout for executing SQL queries in seconds (integer)
# SQL_MAX_ROWS_RETURNED: 1000 # Maximum number of rows to return from a query (integer)

# --- Error Correction Settings ---
# SQL_ERROR_CORRECTION_MAX_ATTEMPTS: 2 # Maximum attempts to correct a failed SQL query using LLM (integer)