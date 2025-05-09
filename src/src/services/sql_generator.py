import logging
from typing import Any, Dict, List, Optional

# Assuming dependencies are in src.core and src.services
from core.llm_interaction_service import LLMInteractionService
from services.schema_manager import DBSchemaManager
from core.config import Settings # Needed to pass settings or potentially configure generator

logger = logging.getLogger(__name__)

class SQLGenerationModule:
    """
    Translates natural language queries into SQL queries using an LLM.

    Utilizes the LLMInteractionService and schema information from DBSchemaManager.
    """

    def __init__(self, llm_service: LLMInteractionService, schema_manager: DBSchemaManager, settings: Settings):
        """
        Initializes the SQLGenerationModule.

        Args:
            llm_service: An instance of LLMInteractionService.
            schema_manager: An instance of DBSchemaManager.
            settings: Application settings.
        """
        self.llm_service = llm_service
        self.schema_manager = schema_manager
        self.settings = settings
        self.prompt_template_path = "src/prompts/sql_generation_retrieval.txt" # Path to the prompt template

        # Load prompt template on initialization
        self._prompt_template = self._load_prompt_template()
        if not self._prompt_template:
             logger.error(f"Failed to load SQL generation prompt template from {self.prompt_template_path}")
             # Depending on application design, you might raise an error here
             # raise FileNotFoundError(f"Prompt template not found at {self.prompt_template_path}")


    def _load_prompt_template(self) -> Optional[str]:
        """Loads the prompt template from a file."""
        try:
            with open(self.prompt_template_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            logger.error(f"Prompt template file not found at {self.prompt_template_path}")
            return None
        except Exception as e:
            logger.error(f"Error loading prompt template {self.prompt_template_path}: {e}")
            return None

    def generate_sql(self, user_query: str) -> Optional[str]:
        """
        Generates a SQL query from a natural language user query.

        Fetches the current database schema and uses the LLM to perform the translation.

        Args:
            user_query: The natural language query from the user.

        Returns:
            A syntactically plausible SQL query string, or None if generation fails.
        """
        if not self._prompt_template:
            logger.error("SQL generation prompt template is not loaded. Cannot generate SQL.")
            return None

        logger.info(f"Attempting to generate SQL for query: '{user_query}'")

        # 1. Get the database schema
        schema = self.schema_manager.get_schema()
        if not schema:
            logger.error("Failed to retrieve database schema. Cannot generate SQL.")
            return None

        logger.debug(f"Using schema:\n{schema}")

        # 2. Construct the prompt for the LLM
        # The prompt includes instructions, schema, and the user query.
        # Use .format() or f-strings with placeholders defined in the template file.
        # Ensure the template file uses placeholders like {schema} and {user_query}.
        try:
            prompt = self._prompt_template.format(schema=schema, user_query=user_query)
            logger.debug(f"Constructed LLM prompt:\n{prompt[:500]}...") # Log start of prompt
        except KeyError as e:
            logger.error(f"Prompt template is missing expected placeholder: {e}. Cannot format prompt.")
            return None
        except Exception as e:
            logger.error(f"Error formatting prompt template: {e}")
            return None


        # 3. Call the LLM to generate the SQL query
        try:
            # Pass additional parameters to the LLM call if needed, e.g., higher temperature
            # or specific stop sequences to ensure only SQL is returned.
            # The template itself should guide the LLM to output only SQL.
            generated_sql = self.llm_service.get_completion(
                prompt=prompt,
                temperature=self.settings.LLM_TEMPERATURE, # Use default temp, or override if needed for SQL gen
                # max_tokens=..., # Consider limiting tokens to prevent overly long queries or explanations
                # stop=[";", "\n\n"] # Stop sequences might help, but depend on LLM behavior
            )

            # Basic post-processing: strip whitespace, ensure it starts with SELECT (for retrieval intent)
            if generated_sql:
                generated_sql = generated_sql.strip()
                # A more robust check might involve parsing or regex, but a simple startswith is okay for now
                if not generated_sql.upper().startswith("SELECT"):
                     logger.warning(f"Generated SQL does not start with SELECT: {generated_sql[:100]}...")
                     # Decide if this should be treated as a failure or passed through
                     # For retrieval intent, non-SELECT is likely wrong.
                     # Let's log a warning but return it for now; validation/execution will catch issues.

            logger.info(f"Generated SQL: '{generated_sql[:200]}...'")
            return generated_sql

        except Exception as e:
            logger.error(f"Failed to get SQL completion from LLM: {e}")
            return None

# Example Usage (for testing purposes)
if __name__ == "__main__":
    # This requires a running PostgreSQL DB and appropriate .env settings
    # and a running LLM (OpenAI API key configured).

    import os
    import sys

    # Add src directory to Python path to allow imports
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

    # Configure basic logging for the example
    logging.basicConfig(level=logging.DEBUG, stream=sys.stdout) # Use DEBUG for detailed LLM logs

    # Need to load settings first
    try:
        from core.config import load_settings, settings as app_settings_instance
        settings = app_settings_instance # Use the globally loaded settings
        print("Using settings from core.config.")
    except ImportError:
         print("Could not import settings from core.config. Attempting local mock.")
         # Fallback for running this file directly if core.config isn't importable yet
         # This requires a .env file with OPENAI_API_KEY and potentially config.yaml
         # For a true shell test, you might mock settings or create minimal ones.
         class MockSettings:
            OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "sk-mock-key-1234") # Load from env or use mock
            LLM_MODEL: str = "gpt-4o-mini" # Use a cheap model for testing
            LLM_TEMPERATURE: float = 0.1 # Lower temp for more deterministic SQL
            LLM_TIMEOUT_SECONDS: int = 30
            LLM_MAX_RETRIES: int = 1
            DATABASE_URL: Optional[str] = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/testdb") # Load from env or use mock
            # Add other required settings if BaseSettings validation was strict
            APP_NAME: str = "Mock App"
            APP_VERSION: str = "0.0.1"
            ENVIRONMENT: str = "test"
            API_V1_STR: str = "/api/v1"
            HOST: str = "0.0.0.0"
            PORT: int = 8000
            DB_HOST: Optional[str] = None
            DB_PORT: Optional[int] = 5432
            DB_NAME: Optional[str] = None
            DB_USER: Optional[str] = None
            DB_PASSWORD: Optional[str] = None
            SQL_TIMEOUT_SECONDS: int = 30
            SQL_MAX_ROWS_RETURNED: int = 1000
            SQL_ERROR_CORRECTION_MAX_ATTEMPTS: int = 2
            _CONFIG_FILE_PATH: str = "config.yaml"

            # Mock validator if needed, though not strictly necessary for this test
            # def assemble_db_connection(self):
            #     if self.DATABASE_URL: return self.DATABASE_URL
            #     if all([self.DB_USER, self.DB_HOST, self.DB_NAME]):
            #         password_part = f":{self.DB_PASSWORD}" if self.DB_PASSWORD else ""
            #         port_part = f":{self.DB_PORT}" if self.DB_PORT is not None else ""
            #         return f"postgresql://{self.DB_USER}{password_part}@{self.DB_HOST}{port_part}/{self.DB_NAME}"
            #     return None

         settings = MockSettings()
         print("Using mock settings.")
         # Ensure .env is loaded if it exists locally
         from dotenv import load_dotenv
         load_dotenv()
         # Update mock settings from env vars if they exist
         settings.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", settings.OPENAI_API_KEY)
         settings.DATABASE_URL = os.getenv("DATABASE_URL", settings.DATABASE_URL)


    print("\n--- Testing SQLGenerationModule ---")

    # Check if essential settings are available for a real test
    if settings.OPENAI_API_KEY == "sk-mock-key-1234" or not settings.DATABASE_URL or "user:password@localhost" in settings.DATABASE_URL:
        print("\nWARNING: Skipping actual test due to missing or mock API key/DB URL.")
        print("Please set OPENAI_API_KEY and DATABASE_URL environment variables for a real test.")
        # Mock the LLM and Schema Manager for a structural test
        class MockLLMService:
            def get_completion(self, prompt: str, **kwargs: Any) -> str:
                print(f"Mock LLM called with prompt (partial): {prompt[:200]}...")
                # Return a plausible mock SQL query based on a simple pattern
                if "users" in prompt.lower() and "count" in prompt.lower():
                     return "SELECT COUNT(*) FROM users;"
                elif "orders" in prompt.lower() and "total" in prompt.lower():
                     return "SELECT SUM(amount) FROM orders;"
                else:
                     return "SELECT * FROM some_table LIMIT 10;" # Default mock

        class MockSchemaManager:
             def get_schema(self) -> Optional[str]:
                 print("Mock Schema Manager called.")
                 # Provide a simple mock schema
                 return """Database Schema:

Tables:
- users:
  - user_id (integer, PK, NOT NULL)
  - username (varchar, NOT NULL)
  - registration_date (timestamp)
- orders:
  - order_id (integer, PK, NOT NULL)
  - user_id (integer, FK -> users.user_id)
  - amount (numeric, NOT NULL)
  - order_date (timestamp)

Relationships (Foreign Keys):
- orders.user_id -> users.user_id

---"""

        llm_service = MockLLMService()
        schema_manager = MockSchemaManager()
        print("Using mock LLM and Schema Manager.")

        # Create a dummy prompt template file for the mock test
        dummy_template_content = """Translate the following natural language query into a PostgreSQL SELECT query.
Use only the tables and columns provided in the schema below.
Output only the SQL query, no explanations or extra text.

Database Schema:
{schema}

User Query: {user_query}

SQL Query:"""
        dummy_template_path = "src/prompts/sql_generation_retrieval.txt"
        os.makedirs(os.path.dirname(dummy_template_path), exist_ok=True)
        with open(dummy_template_path, "w") as f:
            f.write(dummy_template_content)
        print(f"Created dummy prompt template at {dummy_template_path}")


    else:
        # Use real services if configured
        try:
            llm_service = LLMInteractionService(settings)
            schema_manager = DBSchemaManager(settings)
            print("Using real LLM and Schema Manager.")
            # Ensure the real prompt template file exists or create a default
            real_template_path = "src/prompts/sql_generation_retrieval.txt"
            if not os.path.exists(real_template_path):
                 print(f"Prompt template not found at {real_template_path}. Creating a default.")
                 default_template_content = """You are a PostgreSQL expert. Your task is to translate a user's natural language query into a syntactically correct and semantically appropriate PostgreSQL SELECT query.
Adhere strictly to the provided database schema.
Only output the SQL query. Do not include any explanations, comments, or extra text.

Database Schema:
{schema}

User Query: {user_query}

SQL Query:"""
                 os.makedirs(os.path.dirname(real_template_path), exist_ok=True)
                 with open(real_template_path, "w") as f:
                     f.write(default_template_content)
                 print(f"Created default prompt template at {real_template_path}")


        except Exception as e:
            print(f"Failed to initialize real services: {e}")
            llm_service = None
            schema_manager = None


    if llm_service and schema_manager:
        sql_generator = SQLGenerationModule(llm_service, schema_manager, settings)

        # Test queries
        queries_to_test = [
            "Get the total number of users",
            "List the usernames of users registered after 2023-01-01",
            "Show the total amount of all orders",
            "Find orders placed by user with id 10",
            "How many orders are there?"
        ]

        for query in queries_to_test:
            print(f"\nGenerating SQL for: '{query}'")
            try:
                generated_sql = sql_generator.generate_sql(query)
                if generated_sql:
                    print(f"Generated SQL:\n{generated_sql}")
                else:
                    print("SQL generation failed.")
            except Exception as e:
                print(f"An error occurred during SQL generation: {e}")
            print("-" * 30)

    # Clean up dummy template file if created during mock test
    if 'dummy_template_path' in locals() and os.path.exists(dummy_template_path):
         print(f"Removing dummy prompt template file {dummy_template_path}")
         os.remove(dummy_template_path)

    # Clean up default template file if created during real test
    if 'real_template_path' in locals() and os.path.exists(real_template_path) and "default prompt template" in open(real_template_path).read():
         print(f"Removing default prompt template file {real_template_path}")
         os.remove(real_template_path)