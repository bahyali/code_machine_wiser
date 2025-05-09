# Configuration loading will be implemented in I1.T5
import os
from dotenv import load_dotenv
import yaml
from pydantic import BaseModel, Field
from typing import Optional

# Load environment variables from .env file
load_dotenv()

class DatabaseConfig(BaseModel):
    """Database connection configuration."""
    url: str = Field(..., env="DATABASE_URL") # e.g., postgresql://user:password@host:port/dbname

class LLMConfig(BaseModel):
    """LLM configuration."""
    api_key: str = Field(..., env="OPENAI_API_KEY")
    model: str = Field("gpt-4o", env="LLM_MODEL")
    temperature: float = Field(0.7, env="LLM_TEMPERATURE")

class AppConfig(BaseModel):
    """Main application configuration."""
    database: DatabaseConfig
    llm: LLMConfig
    # Add other configuration settings here

def load_config(config_path: str = "config.yaml") -> AppConfig:
    """Loads configuration from a YAML file and environment variables."""
    settings = {}
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            settings = yaml.safe_load(f)

    # Pydantic will automatically load from environment variables
    # based on the `env` field in the models.
    # We can pass the loaded yaml settings to the model constructor.
    # Note: Environment variables take precedence over YAML if both are defined
    # and Pydantic is configured correctly or env vars are loaded first.
    # For simplicity here, we rely on pydantic's env var loading.
    # A more sophisticated loader might merge explicitly.

    # For now, let's just rely on Pydantic's env loading for sensitive keys
    # and potentially pass other settings from YAML if needed later.
    # Let's simplify for I1.T5 and just load env vars via Pydantic.
    # The YAML loading part can be refined in I1.T5.

    # For I1.T1, just a placeholder structure is needed.
    # The actual loading logic will be in I1.T5.
    # Returning dummy config for structure.
    # In I1.T5, this function will be properly implemented.
    print("Warning: Using placeholder config loading. Implement load_config in I1.T5.")
    try:
         # Attempt to load from env vars via Pydantic for structure validation
         db_config = DatabaseConfig()
         llm_config = LLMConfig()
         return AppConfig(database=db_config, llm=llm_config)
    except Exception as e:
         print(f"Error loading config (using placeholders): {e}")
         # Provide dummy config if env vars are not set for initial structure
         return AppConfig(
             database=DatabaseConfig(url=os.getenv("DATABASE_URL", "postgresql://user:pass@host:5432/db")),
             llm=LLMConfig(api_key=os.getenv("OPENAI_API_KEY", "dummy-key"), model=os.getenv("LLM_MODEL", "gpt-4o"))
         )


# Example usage (will be used by other modules)
# config = load_config()
# print(config.llm.api_key)