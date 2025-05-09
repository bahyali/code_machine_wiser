import pytest
from unittest.mock import AsyncMock, MagicMock

# Assuming the SQLGenerationModule is in src/services/sql_generator.py
# and uses LLMInteractionService and DBSchemaManager.
# from src.services.sql_generator import SQLGenerationModule
# from src.core.llm_interaction_service import LLMInteractionService # Dependency
# from src.services.schema_manager import DBSchemaManager # Dependency

# Mock the actual classes if they don't exist
class MockLLMInteractionService:
    def __init__(self, settings=None):
        pass
    async def get_completion(self, prompt: str, max_tokens: int = 150, temperature: float = 0.7):
        """Mock LLM completion for SQL generation."""
        # Simulate SQL generation based on prompt content
        if "Generate SQL query" in prompt:
            if "sales figures" in prompt.lower():
                return "SELECT SUM(price * quantity) FROM order_items;"
            elif "users" in prompt.lower():
                 return "SELECT user_id, username FROM users LIMIT 10;"
            elif "products over 100" in prompt.lower():
                 return "SELECT product_name, price FROM products WHERE price > 100;"
            elif "trends" in prompt.lower():
                 return "SELECT date_trunc('month', order_date) as month, COUNT(*) as order_count FROM orders GROUP BY 1 ORDER BY 1;"
        return "MOCK_SQL_QUERY"

class MockDBSchemaManager:
    def __init__(self, settings=None):
        pass
    def get_schema(self, force_refresh=False) -> str:
        """Mock schema string."""
        return """Database Schema:
Table: users
  - user_id (integer, Nullable: NO)
  - username (varchar, Nullable: NO)
  - created_at (timestamp with time zone, Nullable: NO)
Table: products
  - product_id (integer, Nullable: NO)
  - product_name (varchar, Nullable: NO)
  - price (numeric, Nullable: NO)
Table: orders
  - order_id (integer, Nullable: NO)
  - user_id (integer, Nullable: NO)
  - order_date (timestamp with time zone, Nullable: NO)
Table: order_items
  - item_id (integer, Nullable: NO)
  - order_id (integer, Nullable: NO)
  - product_id (integer, Nullable: NO)
  - quantity (integer, Nullable: NO)
  - price_per_item (numeric, Nullable: NO)
"""

class MockSQLGenerationModule:
    def __init__(self, llm_service: MockLLMInteractionService, schema_manager: MockDBSchemaManager, prompt_template: str):
        self.llm_service = llm_service
        self.schema_manager = schema_manager
        self.prompt_template = prompt_template

    async def generate_sql(self, query: str, intent: str, context: str = None) -> str:
        """Mock method to generate SQL."""
        schema = self.schema_manager.get_schema()
        prompt = self.prompt_template.replace("{schema}", schema).replace("{query}", query).replace("{intent}", intent)
        if context:
             prompt += f"\nContext: {context}" # Simulate adding context
        sql_query = await self.llm_service.get_completion(prompt)
        # Simulate cleaning up LLM output (e.g., removing markdown)
        sql_query = sql_query.strip()
        if sql_query.startswith("```sql"):
             sql_query = sql_query.replace("```sql", "").replace("```", "").strip()
        return sql_query

# Mock the actual module path and its dependencies
# @pytest.fixture
# def sql_generator(mocker):
#     mock_llm_service = MockLLMInteractionService()
#     mock_schema_manager = MockDBSchemaManager()
#     # Mock the actual SQLGenerationModule class
#     mock_generator_class = mocker.patch('src.services.sql_generator.SQLGenerationModule')
#     mock_instance = mock_generator_class.return_value
#     mock_instance.generate_sql = AsyncMock()
#     # Configure return values in tests
#     return mock_instance

# A better approach is to mock the dependencies (LLM, Schema Manager)
# and test the actual SQLGenerationModule logic.
# Assuming src.services.sql_generator.py exists and has the class.

# from src.services.sql_generator import SQLGenerationModule
# from src.core.llm_interaction_service import LLMInteractionService # Actual dependency
# from src.services.schema_manager import DBSchemaManager # Actual dependency

@pytest.fixture
def mock_llm_service_for_sql(mocker):
    """Mocks the LLMInteractionService dependency for SQL generation."""
    mock_service = AsyncMock()
    def mock_get_completion(prompt, **kwargs):
        if "Generate SQL query" in prompt:
            if "sales figures" in prompt.lower():
                return AsyncMock(return_value="SELECT SUM(price * quantity) FROM order_items;")()
            elif "users" in prompt.lower():
                 return AsyncMock(return_value="SELECT user_id, username FROM users LIMIT 10;")()
            elif "products over 100" in prompt.lower():
                 return AsyncMock(return_value="SELECT product_name, price FROM products WHERE price > 100;")()
            elif "trends" in prompt.lower():
                 return AsyncMock(return_value="SELECT date_trunc('month', order_date) as month, COUNT(*) as order_count FROM orders GROUP BY 1 ORDER BY 1;")()
        return AsyncMock(return_value="SELECT 1;")() # Default mock SQL

    mock_service.get_completion.side_effect = mock_get_completion
    return mock_service

@pytest.fixture
def mock_schema_manager_for_sql(mocker):
    """Mocks the DBSchemaManager dependency for SQL generation."""
    mock_manager = MagicMock()
    mock_manager.get_schema.return_value = """Database Schema:
Table: users
  - user_id (integer, Nullable: NO)
  - username (varchar, Nullable: NO)
Table: products
  - product_id (integer, Nullable: NO)
  - price (numeric, Nullable: NO)
Table: orders
  - order_id (integer, Nullable: NO)
  - user_id (integer, Nullable: NO)
  - order_date (timestamp with time zone, Nullable: NO)
Table: order_items
  - item_id (integer, Nullable: NO)
  - order_id (integer, Nullable: NO)
  - product_id (integer, Nullable: NO)
  - quantity (integer, Nullable: NO)
  - price_per_item (numeric, Nullable: NO)
"""
    return mock_manager

@pytest.fixture
def sql_generator_instance(mock_llm_service_for_sql, mock_schema_manager_for_sql):
    """Provides an instance of SQLGenerationModule with mocked dependencies."""
    # Assuming prompt templates are loaded or passed during initialization
    prompt_template = """You are a PostgreSQL expert.
Given the database schema below and a user query, generate the appropriate SQL query.
Schema:
{schema}

User Query: {query}
Intent: {intent}
Generate SQL query:
"""
    # In a real test, you'd import and instantiate the actual class:
    # return SQLGenerationModule(mock_llm_service_for_sql, mock_schema_manager_for_sql, prompt_template)
    # Using the mock class for demonstration:
    return MockSQLGenerationModule(mock_llm_service_for_sql, mock_schema_manager_for_sql, prompt_template)


@pytest.mark.asyncio
async def test_generate_sql_data_retrieval(sql_generator_instance, mock_llm_service_for_sql, mock_schema_manager_for_sql):
    """Test SQL generation for data retrieval intent."""
    query = "What are the total sales figures?"
    intent = "DATA_RETRIEVAL"
    sql_query = await sql_generator_instance.generate_sql(query, intent)

    assert sql_query == "SELECT SUM(price * quantity) FROM order_items;"
    # Verify LLM service was called with the correct prompt including schema and query
    mock_llm_service_for_sql.get_completion.assert_called_once()
    called_prompt = mock_llm_service_for_sql.get_completion.call_args[0][0]
    assert mock_schema_manager_for_sql.get_schema() in called_prompt
    assert query in called_prompt
    assert intent in called_prompt


@pytest.mark.asyncio
async def test_generate_sql_insights(sql_generator_instance, mock_llm_service_for_sql, mock_schema_manager_for_sql):
    """Test SQL generation for insights intent."""
    query = "Analyze monthly order trends."
    intent = "INSIGHTS"
    sql_query = await sql_generator_instance.generate_sql(query, intent)

    assert sql_query == "SELECT date_trunc('month', order_date) as month, COUNT(*) as order_count FROM orders GROUP BY 1 ORDER BY 1;"
    mock_llm_service_for_sql.get_completion.assert_called_once()
    called_prompt = mock_llm_service_for_sql.get_completion.call_args[0][0]
    assert mock_schema_manager_for_sql.get_schema() in called_prompt
    assert query in called_prompt
    assert intent in called_prompt

@pytest.mark.asyncio
async def test_generate_sql_with_context(sql_generator_instance, mock_llm_service_for_sql, mock_schema_manager_for_sql):
    """Test SQL generation with additional context."""
    query = "Show me products over 100"
    intent = "DATA_RETRIEVAL"
    context = "Focus only on electronics category." # Example context
    sql_query = await sql_generator_instance.generate_sql(query, intent, context=context)

    assert sql_query == "SELECT product_name, price FROM products WHERE price > 100;" # Mock doesn't use context, but test verifies prompt includes it
    mock_llm_service_for_sql.get_completion.assert_called_once()
    called_prompt = mock_llm_service_for_sql.get_completion.call_args[0][0]
    assert mock_schema_manager_for_sql.get_schema() in called_prompt
    assert query in called_prompt
    assert intent in called_prompt
    assert context in called_prompt # Verify context is included in the prompt

# Add tests for error handling if LLM service call fails
# Add tests for handling empty schema or specific query types