import logging
import json
import os
import sys
from typing import Any, Dict, List, Optional, Literal

# Assuming dependencies are in src.core and src.services
from core.llm_interaction_service import LLMInteractionService
from services.schema_manager import DBSchemaManager
from core.config import Settings # Needed to pass settings or potentially configure generator

logger = logging.getLogger(__name__)

class SQLGenerationModule:
    """
    Translates natural language queries into SQL queries using an LLM.

    Supports different prompting strategies based on intent (e.g., retrieval, insights).
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

        # Define paths for different prompt templates based on intent type
        self.prompt_template_paths = {
            "DATA_RETRIEVAL": "src/prompts/sql_generation_retrieval.txt",
            "INSIGHTS": "src/prompts/sql_generation_insight.txt",
            # Add other types if needed in the future
        }
        self._prompt_templates: Dict[str, Optional[str]] = {}

        # Load all configured prompt templates on initialization
        self._load_prompt_templates()

        # Check if essential templates are loaded (e.g., DATA_RETRIEVAL)
        if not self._prompt_templates.get("DATA_RETRIEVAL"):
             logger.error(f"Failed to load essential SQL generation prompt template for DATA_RETRIEVAL.")
             # Depending on application design, might raise an error here
             # raise FileNotFoundError("Essential prompt template not found.")


    def _load_prompt_templates(self) -> None:
        """Loads all configured prompt templates from files."""
        for intent, path in self.prompt_template_paths.items():
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    self._prompt_templates[intent] = f.read()
                logger.info(f"Loaded prompt template for '{intent}' from {path}")
            except FileNotFoundError:
                logger.error(f"Prompt template file not found at {path} for intent '{intent}'")
                self._prompt_templates[intent] = None # Mark as failed
            except Exception as e:
                logger.error(f"Error loading prompt template {path} for intent '{intent}': {e}")
                self._prompt_templates[intent] = None # Mark as failed


    def generate_sql(self, user_query: str, intent: Literal["DATA_RETRIEVAL", "INSIGHTS"], context: Optional[Dict] = None) -> Optional[str]:
        """
        Generates a SQL query from a natural language user query based on intent.

        Fetches the current database schema and uses the LLM to perform the translation.

        Args:
            user_query: The natural language query from the user.
            intent: The classified intent ("DATA_RETRIEVAL" or "INSIGHTS").
            context: Optional dictionary containing context for the LLM (e.g., previous query results).

        Returns:
            A syntactically plausible SQL query string, or None if generation fails.
        """
        prompt_template = self._prompt_templates.get(intent)

        if not prompt_template:
            logger.error(f"SQL generation prompt template for intent '{intent}' is not loaded. Cannot generate SQL.")
            return None

        logger.info(f"Attempting to generate SQL for query: \'{user_query}\' with intent '{intent}'")

        # 1. Get the database schema
        schema = self.schema_manager.get_schema()
        if not schema:
            logger.error("Failed to retrieve database schema. Cannot generate SQL.")
            return None

        logger.debug(f"Using schema:\\n{schema}")

        # 2. Construct the prompt for the LLM
        # The prompt includes instructions, schema, user query, and optional context.
        try:
            # Format context dictionary into a string suitable for the LLM
            prompt_context_str = ""
            if context:
                 try:
                     # Simple JSON format for context, useful for structured data like previous results
                     prompt_context_str = json.dumps(context, indent=2)
                 except Exception as e:
                     # Fallback to string representation if JSON fails
                     logger.warning(f"Could not format context as JSON: {e}. Passing context as string representation.")
                     prompt_context_str = str(context)


            # Use .format() with placeholders defined in the template files.
            # Ensure templates use placeholders like {schema}, {user_query}, and {context}.
            prompt = prompt_template.format(schema=schema, user_query=user_query, context=prompt_context_str)
            logger.debug(f"Constructed LLM prompt for intent '{intent}':\\n{prompt[:500]}...") # Log start of prompt
        except KeyError as e:
            logger.error(f"Prompt template for '{intent}' is missing expected placeholder: {e}. Cannot format prompt.")
            return None
        except Exception as e:
            logger.error(f"Error formatting prompt template for '{intent}': {e}")
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
                # stop=[";", "\\n\\n"] # Stop sequences might help, but depend on LLM behavior
            )

            # Basic post-processing: strip whitespace
            if generated_sql:
                generated_sql = generated_sql.strip()
                # Add a basic check/warning for non-SELECT.
                # For retrieval, non-SELECT is likely wrong. For insights, it might be okay
                # depending on the required data gathering strategy (though SELECT is most common).
                # Let's log a warning but return it for now; validation/execution will catch issues.
                if not generated_sql.upper().startswith("SELECT"):
                     logger.warning(f"Generated SQL does not start with SELECT (intent: {intent}): {generated_sql[:100]}...")


            logger.info(f"Generated SQL (intent: {intent}): \'{generated_sql[:200]}...\'")
            return generated_sql

        except Exception as e:
            logger.error(f"Failed to get SQL completion from LLM for intent '{intent}': {e}")
            return None

# Example Usage (for testing purposes)
if __name__ == "__main__":
    # This requires a running PostgreSQL DB and appropriate .env settings
    # and a running LLM (OpenAI API key configured).\n\n
    # Add src directory to Python path to allow imports
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), \'../..\')))\n\n
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
         # For a true shell test, you might mock settings or create minimal ones.\n\n
         class MockSettings:\n
            OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "sk-mock-key-1234") # Load from env or use mock\n
            LLM_MODEL: str = "gpt-4o-mini" # Use a cheap model for testing\n
            LLM_TEMPERATURE: float = 0.1 # Lower temp for more deterministic SQL\n
            LLM_TIMEOUT_SECONDS: int = 30\n
            LLM_MAX_RETRIES: int = 1\n
            DATABASE_URL: Optional[str] = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/testdb") # Load from env or use mock\n
            # Add other required settings if BaseSettings validation was strict\n
            APP_NAME: str = "Mock App"\n
            APP_VERSION: str = "0.0.1"\n
            ENVIRONMENT: str = "test"\n
            API_V1_STR: str = "/api/v1"\n
            HOST: str = "0.0.0.0"\n
            PORT: int = 8000\n
            DB_HOST: Optional[str] = None\n
            DB_PORT: Optional[int] = 5432\n
            DB_NAME: Optional[str] = None\n
            DB_USER: Optional[str] = None\n
            DB_PASSWORD: Optional[str] = None\n
            SQL_TIMEOUT_SECONDS: int = 30\n
            SQL_MAX_ROWS_RETURNED: int = 1000\n
            SQL_ERROR_CORRECTION_MAX_ATTEMPTS: int = 2\n
            _CONFIG_FILE_PATH: str = "config.yaml"\n\n
         settings = MockSettings()\n
         print("Using mock settings.")\n
         # Ensure .env is loaded if it exists locally\n
         from dotenv import load_dotenv\n
         load_dotenv()\n
         # Update mock settings from env vars if they exist\n
         settings.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", settings.OPENAI_API_KEY)\n
         settings.DATABASE_URL = os.getenv("DATABASE_URL", settings.DATABASE_URL)\n\n\n
    print("\\n--- Testing SQLGenerationModule ---")\n\n
    # Check if essential settings are available for a real test\n
    if settings.OPENAI_API_KEY == "sk-mock-key-1234" or not settings.DATABASE_URL or "user:password@localhost" in settings.DATABASE_URL:\n
        print("\\nWARNING: Skipping actual test due to missing or mock API key/DB URL.")\n
        print("Please set OPENAI_API_KEY and DATABASE_URL environment variables for a real test.")\n
        # Mock the LLM and Schema Manager for a structural test\n
        class MockLLMService:\n
            def get_completion(self, prompt: str, **kwargs: Any) -> str:\n
                print(f"Mock LLM called with prompt (partial): {prompt[:200]}...")\n
                # Return a plausible mock SQL query based on a simple pattern and intent\n
                if "intent: DATA_RETRIEVAL" in prompt:\n
                    if "users" in prompt.lower() and "count" in prompt.lower():\n
                         return "SELECT COUNT(*) FROM users;"\n
                    elif "orders" in prompt.lower() and "total" in prompt.lower():\n
                         return "SELECT SUM(amount) FROM orders;"\n
                    else:\n
                         return "SELECT * FROM some_table LIMIT 10;" # Default mock retrieval\n
                elif "intent: INSIGHTS" in prompt:\n
                     if "average order amount" in prompt.lower():\n
                          return "SELECT AVG(amount) FROM orders;"\n
                     elif "revenue each month" in prompt.lower():\n
                          return "SELECT DATE_TRUNC('month', order_date) as order_month, SUM(amount) as monthly_revenue FROM orders GROUP BY 1 ORDER BY 1;"\n
                     elif "users placed more than" in prompt.lower():\n
                          return "SELECT user_id, COUNT(*) as order_count FROM orders GROUP BY user_id HAVING COUNT(*) > 5;"\n
                     else:\n
                          return "SELECT 'Mock Insight Data' as insight_data;" # Default mock insight\n
                else:\n
                     return "SELECT 'Unknown Intent Mock Response';" # Fallback\n\n
        class MockSchemaManager:\n
             def get_schema(self) -> Optional[str]:\n
                 print("Mock Schema Manager called.")\n
                 # Provide a simple mock schema\n
                 return """Database Schema:\n\nTables:\n- users:\n  - user_id (integer, PK, NOT NULL)\n  - username (varchar, NOT NULL)\n  - registration_date (timestamp)\n- orders:\n  - order_id (integer, PK, NOT NULL)\n  - user_id (integer, FK -> users.user_id)\n  - amount (numeric, NOT NULL)\n  - order_date (timestamp)\n\nRelationships (Foreign Keys):\n- orders.user_id -> users.user_id\n\n---"""\n\n
        llm_service = MockLLMService()\n
        schema_manager = MockSchemaManager()\n
        print("Using mock LLM and Schema Manager.")\n\n
        # Create dummy prompt template files for the mock test if they don't exist\n
        dummy_retrieval_template_path = "src/prompts/sql_generation_retrieval.txt"\n
        dummy_insight_template_path = "src/prompts/sql_generation_insight.txt"\n
        os.makedirs(os.path.dirname(dummy_retrieval_template_path), exist_ok=True)\n\n
        created_dummy_retrieval = False\n
        if not os.path.exists(dummy_retrieval_template_path):\n
             print(f"Creating dummy prompt template at {dummy_retrieval_template_path}")\n
             default_retrieval_template_content = """You are a PostgreSQL expert. Your task is to translate a user\'s natural language query into a syntactically correct and semantically appropriate PostgreSQL SELECT query.\nAdhere strictly to the provided database schema.\nOnly output the SQL query. Do not include any explanations, comments, or extra text.\n\nDatabase Schema:\n{schema}\n\nUser Query: {user_query}\n\nContext (Optional, e.g., previous results or state):\n{context}\n\nSQL Query:"""\n
             with open(dummy_retrieval_template_path, "w") as f:\n
                 f.write(default_retrieval_template_content)\n
             created_dummy_retrieval = True\n\n
        created_dummy_insight = False\n
        if not os.path.exists(dummy_insight_template_path):\n
             print(f"Creating dummy prompt template at {dummy_insight_template_path}")\n
             default_insight_template_content = """You are a PostgreSQL expert tasked with generating SQL queries to gather data for generating insights based on a user's natural language request.\nYour goal is to produce a syntactically correct and semantically appropriate PostgreSQL SELECT query that will retrieve the necessary raw data or aggregated data points required to answer the user's insight question.\nAdhere strictly to the provided database schema.\nConsider the user query and any provided context (e.g., results from previous queries) to determine the best approach for data retrieval.\nOutput *only* the SQL query. Do not include any explanations, comments, or extra text.\n\nDatabase Schema:\n{schema}\n\nUser Query: {user_query}\n\nContext (Optional, e.g., previous results or state):\n{context}\n\nSQL Query for Insight:"""\n
             with open(dummy_insight_template_path, "w") as f:\n
                 f.write(default_insight_template_content)\n
             created_dummy_insight = True\n\n\n
    else:\n
        # Use real services if configured\n
        try:\n
            llm_service = LLMInteractionService(settings)\n
            schema_manager = DBSchemaManager(settings)\n
            print("Using real LLM and Schema Manager.")\n
            # Ensure the real prompt template files exist or create defaults\n
            real_retrieval_template_path = "src/prompts/sql_generation_retrieval.txt"\n
            real_insight_template_path = "src/prompts/sql_generation_insight.txt"\n
            os.makedirs(os.path.dirname(real_retrieval_template_path), exist_ok=True)\n\n
            created_real_retrieval = False\n
            if not os.path.exists(real_retrieval_template_path):\n
                 print(f"Prompt template not found at {real_retrieval_template_path}. Creating a default.")\n
                 default_retrieval_template_content = """You are a PostgreSQL expert. Your task is to translate a user\'s natural language query into a syntactically correct and semantically appropriate PostgreSQL SELECT query.\nAdhere strictly to the provided database schema.\nOnly output the SQL query. Do not include any explanations, comments, or extra text.\n\nDatabase Schema:\n{schema}\n\nUser Query: {user_query}\n\nContext (Optional, e.g., previous results or state):\n{context}\n\nSQL Query:"""\n
                 with open(real_retrieval_template_path, "w") as f:\n
                     f.write(default_retrieval_template_content)\n
                 created_real_retrieval = True\n\n
            created_real_insight = False\n
            if not os.path.exists(real_insight_template_path):\n
                 print(f"Prompt template not found at {real_insight_template_path}. Creating a default.")\n
                 default_insight_template_content = """You are a PostgreSQL expert tasked with generating SQL queries to gather data for generating insights based on a user's natural language request.\nYour goal is to produce a syntactically correct and semantically appropriate PostgreSQL SELECT query that will retrieve the necessary raw data or aggregated data points required to answer the user's insight question.\nAdhere strictly to the provided database schema.\nConsider the user query and any provided context (e.g., results from previous queries) to determine the best approach for data retrieval.\nOutput *only* the SQL query. Do not include any explanations, comments, or extra text.\n\nDatabase Schema:\n{schema}\n\nUser Query: {user_query}\n\nContext (Optional, e.g., previous results or state):\n{context}\n\nSQL Query for Insight:"""\n
                 with open(real_insight_template_path, "w") as f:\n
                     f.write(default_insight_template_content)\n
                 created_real_insight = True\n\n
        except Exception as e:\n
            print(f"Failed to initialize real services: {e}")\n
            llm_service = None\n
            schema_manager = None\n\n\n
    if llm_service and schema_manager:\n
        sql_generator = SQLGenerationModule(llm_service, schema_manager, settings)\n\n
        # Test queries with specified intents\n
        queries_to_test = [\n
            {"query": "Get the total number of users", "intent": "DATA_RETRIEVAL"},\n
            {"query": "List the usernames of users registered after 2023-01-01", "intent": "DATA_RETRIEVAL"},\n
            {"query": "Show the total amount of all orders", "intent": "DATA_RETRIEVAL"},\n
            {"query": "Find orders placed by user with id 10", "intent": "DATA_RETRIEVAL"},\n
            {"query": "How many orders are there?", "intent": "DATA_RETRIEVAL"},\n
            # Add insight queries\n
            {"query": "What is the average order amount per user?", "intent": "INSIGHTS"},\n
            {"query": "Show me the total revenue generated each month", "intent": "INSIGHTS"},\n
            {"query": "Which users have placed more than 5 orders?", "intent": "INSIGHTS"},\n
        ]\n\n
        for test_case in queries_to_test:\n
            query = test_case["query"]\n
            intent = test_case["intent"]\n
            print(f"\\nGenerating SQL for: \'{query}\' (Intent: {intent})")\n
            try:\n
                # Pass context as None for now, as iterative logic is in Orchestrator (I4.T5)\n
                generated_sql = sql_generator.generate_sql(query, intent, context=None)\n
                if generated_sql:\n
                    print(f"Generated SQL:\\n{generated_sql}")\n
                else:\n
                    print("SQL generation failed.")\n
            except Exception as e:\n
                print(f"An error occurred during SQL generation: {e}")\n
            print("-" * 30)\n\n
    # Clean up dummy template files if created during mock test\n
    if \'created_dummy_retrieval\' in locals() and created_dummy_retrieval and os.path.exists(dummy_retrieval_template_path):\n
         print(f"Removing dummy prompt template file {dummy_retrieval_template_path}")\n
         os.remove(dummy_retrieval_template_path)\n
    if \'created_dummy_insight\' in locals() and created_dummy_insight and os.path.exists(dummy_insight_template_path):\n
         print(f"Removing dummy prompt template file {dummy_insight_template_path}")\n
         os.remove(dummy_insight_template_path)\n\n
    # Clean up default template files if created during real test\n
    if \'created_real_retrieval\' in locals() and created_real_retrieval and os.path.exists(real_retrieval_template_path):\n
         # Check content before removing to avoid deleting user's custom template\n
         try:\n
             with open(real_retrieval_template_path, "r") as f:\n
                 content = f.read()\n
                 if "Context (Optional, e.g., previous results or state):\\n{context}" in content:\n # Check for the added line\n
                      print(f"Removing default prompt template file {real_retrieval_template_path}")\n
                      os.remove(real_retrieval_template_path)\n
         except Exception as e:\n
             print(f"Error checking/removing {real_retrieval_template_path}: {e}")\n\n
    if \'created_real_insight\' in locals() and created_real_insight and os.path.exists(real_insight_template_path):\n
         # Check content before removing\n
         try:\n
             with open(real_insight_template_path, "r") as f:\n
                 content = f.read()\n
                 if "Context (Optional, e.g., previous results or state):\\n{context}" in content:\n # Check for the added line\n
                      print(f"Removing default prompt template file {real_insight_template_path}")\n
                      os.remove(real_insight_template_path)\n
         except Exception as e:\n
             print(f"Error checking/removing {real_insight_template_path}: {e}")\n