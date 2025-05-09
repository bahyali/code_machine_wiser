import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

# Assume the main FastAPI app is in src.main
# We need to import it relative to the project root, not using src.
# This might require adjusting the import path based on the actual project structure
# For this example, let's assume main is directly importable or we can point to the router
# A better approach is often to create a test app instance
from api.v1.query_router import router # Assuming router is defined here

# Create a test client for the router
client = TestClient(router)

# Define mock responses for external services
MOCK_CHITCHAT_RESPONSE = {"response": "Hello! How can I help you today?"}
MOCK_DATA_RETRIEVAL_SQL = "SELECT COUNT(*) FROM users WHERE status = 'active';"
MOCK_DATA_RETRIEVAL_DB_RESULT = [{"count": 1234}]
MOCK_DATA_RETRIEVAL_SYNTHESIZED_RESPONSE = {"response": "There are 1,234 active users."}
MOCK_INSIGHT_SQL_1 = "SELECT year, SUM(revenue) FROM sales GROUP BY year;"
MOCK_INSIGHT_DB_RESULT_1 = [{"year": 2022, "sum": 100000}, {"year": 2023, "sum": 150000}]
MOCK_INSIGHT_SQL_2 = "SELECT product, AVG(price) FROM products GROUP BY product;"
MOCK_INSIGHT_DB_RESULT_2 = [{"product": "A", "avg": 50.50}, {"product": "B", "avg": 75.00}]
MOCK_INSIGHT_SYNTHESIZED_RESPONSE = {"response": "Sales increased by 50% from 2022 to 2023. Product A averages 50.50 SAR and Product B averages 75.00 SAR."}
MOCK_SQL_ERROR_MESSAGE = "relation \"users\" does not exist"
MOCK_CORRECTED_SQL = "SELECT COUNT(*) FROM customers WHERE status = 'active';" # Assume 'users' was a typo for 'customers'
MOCK_CORRECTED_DB_RESULT = [{"count": 5678}]
MOCK_ERROR_RESPONSE = {"detail": "An error occurred while processing your query."}


# Use patch.object to mock methods on instances of the classes
# We need to patch the classes themselves where they are imported in orchestrator.py
# Assuming orchestrator.py imports like:
# from services.intent_analyzer import IntentAnalysisModule
# from services.chitchat_handler import ChitChatHandlerModule
# ... etc.

# We need to patch the classes in the module where they are used (orchestrator)
# The patch target string needs to reflect the import path within orchestrator.py
# Example: if orchestrator.py has `from services.intent_analyzer import IntentAnalysisModule`
# the patch target is `core.orchestrator.IntentAnalysisModule`

# Let's assume the following import structure within src/:
# src/core/orchestrator.py imports from src/services/
# src/services/sql_executor.py imports psycopg2
# src/services/llm_interaction_service.py imports openai

# Patch targets relative to the module where the dependency is used (orchestrator.py)
ORCHESTRATOR_PATH = "core.orchestrator"
SERVICES_PATH = "services" # Assuming services are imported directly into orchestrator or its helpers

# Mock the external dependencies at the point they are used or instantiated
# This means patching the classes/functions in the modules that import them
# For example, if SQLExecutionModule is used in Orchestrator, we patch SQLExecutionModule in the context of Orchestrator
# If LLMInteractionService is used by multiple services, we might patch it where it's instantiated or passed around,
# or patch the methods on the service instance used by the orchestrator/services.

# A common pattern is to mock the *methods* of the service instances that the orchestrator uses.
# This requires patching the service classes themselves during the test setup,
# so that when the orchestrator instantiates or uses them, it gets the mock version.

# Let's assume Orchestrator uses instances of these services:
# self.intent_analyzer = IntentAnalysisModule(...)
# self.chitchat_handler = ChitChatHandlerModule(...)
# self.sql_generator = SQLGenerationModule(...)
# self.sql_executor = SQLExecutionModule(...)
# self.error_corrector = SQLErrorCorrectionModule(...)
# self.response_synthesizer = ResponseSynthesisModule(...)
# self.schema_manager = DBSchemaManager(...)
# self.formatter_validator = DataFormatterValidatorModule(...)

# We will patch the classes themselves to control their behavior when instantiated by the orchestrator
# The patch target is the path to the class *within the module that imports it*.
# If orchestrator.py does `from services.intent_analyzer import IntentAnalysisModule`,
# the patch target is `core.orchestrator.IntentAnalysisModule`.

# Let's define patch targets assuming direct imports in orchestrator.py
PATCH_TARGET_INTENT_ANALYZER = f"{ORCHESTRATOR_PATH}.IntentAnalysisModule"
PATCH_TARGET_CHITCHAT_HANDLER = f"{ORCHESTRATOR_PATH}.ChitChatHandlerModule"
PATCH_TARGET_SCHEMA_MANAGER = f"{ORCHESTRATOR_PATH}.DBSchemaManager"
PATCH_TARGET_SQL_GENERATOR = f"{ORCHESTRATOR_PATH}.SQLGenerationModule"
PATCH_TARGET_SQL_EXECUTOR = f"{ORCHESTRATOR_PATH}.SQLExecutionModule"
PATCH_TARGET_ERROR_CORRECTOR = f"{ORCHESTRATOR_PATH}.SQLErrorCorrectionModule"
PATCH_TARGET_RESPONSE_SYNTHESIZER = f"{ORCHESTRATOR_PATH}.ResponseSynthesisModule"
PATCH_TARGET_FORMATTER_VALIDATOR = f"{ORCHESTRATOR_PATH}.DataFormatterValidatorModule"

# We also need to mock the LLM and DB interactions that the services use.
# For simplicity in integration tests, we can often mock the service methods directly
# that interact with external systems. E.g., mock `LLMInteractionService.get_completion`
# and `SQLExecutionModule.execute_sql`.

# Let's refine the patching strategy: Patch the service *classes* when the orchestrator
# instantiates them, and then configure the methods on the *mock instances* returned by the patched classes.

@pytest.fixture
def mock_services(mocker):
    """Fixture to mock all service classes used by the Orchestrator."""
    mock_intent_analyzer_cls = mocker.patch(PATCH_TARGET_INTENT_ANALYZER)
    mock_chitchat_handler_cls = mocker.patch(PATCH_TARGET_CHITCHAT_HANDLER)
    mock_schema_manager_cls = mocker.patch(PATCH_TARGET_SCHEMA_MANAGER)
    mock_sql_generator_cls = mocker.patch(PATCH_TARGET_SQL_GENERATOR)
    mock_sql_executor_cls = mocker.patch(PATCH_TARGET_SQL_EXECUTOR)
    mock_error_corrector_cls = mocker.patch(PATCH_TARGET_ERROR_CORRECTOR)
    mock_response_synthesizer_cls = mocker.patch(PATCH_TARGET_RESPONSE_SYNTHESIZER)
    mock_formatter_validator_cls = mocker.patch(PATCH_TARGET_FORMATTER_VALIDATOR)

    # Return the mock instances that the Orchestrator will receive
    return {
        "intent_analyzer": mock_intent_analyzer_cls.return_value,
        "chitchat_handler": mock_chitchat_handler_cls.return_value,
        "schema_manager": mock_schema_manager_cls.return_value,
        "sql_generator": mock_sql_generator_cls.return_value,
        "sql_executor": mock_sql_executor_cls.return_value,
        "error_corrector": mock_error_corrector_cls.return_value,
        "response_synthesizer": mock_response_synthesizer_cls.return_value,
        "formatter_validator": mock_formatter_validator_cls.return_value,
    }

def test_chit_chat_flow(mock_services):
    """Test the end-to-end chit-chat flow."""
    user_query = "Hello, how are you?"

    # Configure mocks for chit-chat flow
    mock_services["intent_analyzer"].analyze_intent.return_value = "CHITCHAT"
    mock_services["chitchat_handler"].handle_chit_chat.return_value = MOCK_CHITCHAT_RESPONSE["response"]

    # Ensure other services are not called
    mock_services["schema_manager"].get_schema.assert_not_called()
    mock_services["sql_generator"].generate_sql.assert_not_called()
    mock_services["sql_executor"].execute_sql.assert_not_called()
    mock_services["error_corrector"].handle_and_correct.assert_not_called()
    mock_services["response_synthesizer"].synthesize_response.assert_not_called()
    mock_services["formatter_validator"].format_data.assert_not_called()


    # Send request to the API
    response = client.post("/api/v1/query", json={"query": user_query})

    # Assert response status code and body
    assert response.status_code == 200
    assert response.json() == MOCK_CHITCHAT_RESPONSE

    # Verify mocks were called correctly
    mock_services["intent_analyzer"].analyze_intent.assert_called_once_with(user_query)
    mock_services["chitchat_handler"].handle_chit_chat.assert_called_once_with(user_query)


def test_data_retrieval_flow(mock_services):
    """Test the end-to-end data retrieval flow."""
    user_query = "Show me the number of active users"
    mock_schema = "Mock DB Schema DDL..." # Provide a sample schema string

    # Configure mocks for data retrieval flow
    mock_services["intent_analyzer"].analyze_intent.return_value = "DATA_RETRIEVAL"
    mock_services["schema_manager"].get_schema.return_value = mock_schema
    mock_services["sql_generator"].generate_sql.return_value = MOCK_DATA_RETRIEVAL_SQL
    mock_services["sql_executor"].execute_sql.return_value = MOCK_DATA_RETRIEVAL_DB_RESULT
    # Assuming formatter_validator is called by response_synthesizer or orchestrator before final response
    # For simplicity, let's assume response_synthesizer returns the final formatted response
    mock_services["response_synthesizer"].synthesize_response.return_value = MOCK_DATA_RETRIEVAL_SYNTHESIZED_RESPONSE["response"]
    # If formatter_validator is called separately, mock its return value
    # mock_services["formatter_validator"].format_data.return_value = MOCK_DATA_RETRIEVAL_SYNTHESIZED_RESPONSE["response"]


    # Ensure services for other intents are not called
    mock_services["chitchat_handler"].handle_chit_chat.assert_not_called()
    mock_services["error_corrector"].handle_and_correct.assert_not_called()


    # Send request to the API
    response = client.post("/api/v1/query", json={"query": user_query})

    # Assert response status code and body
    assert response.status_code == 200
    # Assuming the response structure is {"response": "..."}
    assert response.json() == MOCK_DATA_RETRIEVAL_SYNTHESIZED_RESPONSE

    # Verify mocks were called correctly
    mock_services["intent_analyzer"].analyze_intent.assert_called_once_with(user_query)
    mock_services["schema_manager"].get_schema.assert_called_once()
    mock_services["sql_generator"].generate_sql.assert_called_once_with(user_query, mock_schema, None) # Assuming no previous results for first query
    mock_services["sql_executor"].execute_sql.assert_called_once_with(MOCK_DATA_RETRIEVAL_SQL)
    mock_services["response_synthesizer"].synthesize_response.assert_called_once_with(user_query, MOCK_DATA_RETRIEVAL_DB_RESULT)
    # If formatter_validator is called separately, verify it
    # mock_services["formatter_validator"].format_data.assert_called_once_with(...)


def test_insight_generation_flow_single_query(mock_services):
    """Test the insight generation flow with a single SQL query."""
    user_query = "Give me insights on sales trends"
    mock_schema = "Mock DB Schema DDL..."

    # Configure mocks for insight flow (single query)
    mock_services["intent_analyzer"].analyze_intent.return_value = "INSIGHTS"
    mock_services["schema_manager"].get_schema.return_value = mock_schema
    # Mock SQL generator to return the first SQL query
    mock_services["sql_generator"].generate_sql.side_effect = [MOCK_INSIGHT_SQL_1]
    # Mock SQL executor to return results for the first query
    mock_services["sql_executor"].execute_sql.side_effect = [MOCK_INSIGHT_DB_RESULT_1]
    # Mock response synthesizer to indicate insight is complete after first query
    # Assuming synthesize_response also handles the iterative check or a separate method is used
    # Let's assume synthesize_response is called with all collected data and returns the final response
    mock_services["response_synthesizer"].synthesize_response.return_value = MOCK_INSIGHT_SYNTHESIZED_RESPONSE["response"]
    # If there's a separate method to check completeness, mock that
    # mock_services["response_synthesizer"].check_completeness.return_value = True

    # Ensure services for other intents are not called
    mock_services["chitchat_handler"].handle_chit_chat.assert_not_called()
    mock_services["error_corrector"].handle_and_correct.assert_not_called()


    # Send request to the API
    response = client.post("/api/v1/query", json={"query": user_query})

    # Assert response status code and body
    assert response.status_code == 200
    assert response.json() == MOCK_INSIGHT_SYNTHESIZED_RESPONSE

    # Verify mocks were called correctly
    mock_services["intent_analyzer"].analyze_intent.assert_called_once_with(user_query)
    mock_services["schema_manager"].get_schema.assert_called_once()
    # Verify SQL generation and execution happened once
    mock_services["sql_generator"].generate_sql.assert_called_once_with(user_query, mock_schema, None)
    mock_services["sql_executor"].execute_sql.assert_called_once_with(MOCK_INSIGHT_SQL_1)
    # Verify response synthesis was called with the collected data
    mock_services["response_synthesizer"].synthesize_response.assert_called_once_with(user_query, MOCK_INSIGHT_DB_RESULT_1)
    # If check_completeness exists, verify it was called
    # mock_services["response_synthesizer"].check_completeness.assert_called_once_with(...)


def test_insight_generation_flow_iterative_queries(mock_services):
    """Test the insight generation flow with multiple iterative SQL queries."""
    user_query = "Give me detailed insights on sales and product performance"
    mock_schema = "Mock DB Schema DDL..."

    # Configure mocks for insight flow (iterative queries)
    mock_services["intent_analyzer"].analyze_intent.return_value = "INSIGHTS"
    mock_services["schema_manager"].get_schema.return_value = mock_schema

    # Mock SQL generator to return a sequence of SQL queries
    mock_services["sql_generator"].generate_sql.side_effect = [
        MOCK_INSIGHT_SQL_1, # First query
        MOCK_INSIGHT_SQL_2  # Second query based on previous results/context
    ]
    # Mock SQL executor to return results for each query
    mock_services["sql_executor"].execute_sql.side_effect = [
        MOCK_INSIGHT_DB_RESULT_1, # Results for first query
        MOCK_INSIGHT_DB_RESULT_2  # Results for second query
    ]

    # Mock response synthesizer to indicate insight is NOT complete after first query,
    # and THEN return the final response after the second query.
    # This requires a mock that changes behavior or a separate method for checking completeness.
    # Let's assume the Orchestrator calls SQLGen -> SQLExec -> (check completeness/need more data) -> loop or SynthResponse
    # We can mock the SQLGen to return None or a special value to signal no more queries needed,
    # or mock a separate method called by the orchestrator to decide.
    # A simpler approach for mocking iterative flow is to control the side_effect of SQLGen.
    # Let's assume the Orchestrator calls SQLGen repeatedly until it gets None or an empty string,
    # or until a max iteration count is reached.
    # Or, let's assume the Orchestrator calls ResponseSynthesizer.assess_insight_completeness(query, collected_data)
    # which returns {"complete": bool, "next_query_prompt": str | None}

    # Let's refine the mock for the iterative process assuming a method like `assess_insight_completeness`
    mock_services["response_synthesizer"].assess_insight_completeness = MagicMock(side_effect=[
        {"complete": False, "next_query_prompt": "Get product performance data"}, # After first query results
        {"complete": True, "next_query_prompt": None} # After second query results
    ])
    # The final synthesize_response is called once at the end with all data
    mock_services["response_synthesizer"].synthesize_response.return_value = MOCK_INSIGHT_SYNTHESIZED_RESPONSE["response"]


    # Ensure services for other intents are not called
    mock_services["chitchat_handler"].handle_chit_chat.assert_not_called()
    mock_services["error_corrector"].handle_and_correct.assert_not_called()

    # Send request to the API
    response = client.post("/api/v1/query", json={"query": user_query})

    # Assert response status code and body
    assert response.status_code == 200
    assert response.json() == MOCK_INSIGHT_SYNTHESIZED_RESPONSE

    # Verify mocks were called correctly
    mock_services["intent_analyzer"].analyze_intent.assert_called_once_with(user_query)
    mock_services["schema_manager"].get_schema.assert_called_once()

    # Verify SQL generation and execution happened twice
    # First call
    mock_services["sql_generator"].generate_sql.assert_any_call(user_query, mock_schema, None)
    mock_services["sql_executor"].execute_sql.assert_any_call(MOCK_INSIGHT_SQL_1)
    mock_services["response_synthesizer"].assess_insight_completeness.assert_any_call(user_query, MOCK_INSIGHT_DB_RESULT_1)

    # Second call (assuming the orchestrator passes the next_query_prompt or similar context)
    # The exact arguments to generate_sql for the second call depend on orchestrator logic
    # It might pass the original query + context, or the next_query_prompt
    # Let's assume it passes original query, schema, and previous results
    mock_services["sql_generator"].generate_sql.assert_any_call(user_query, mock_schema, [MOCK_INSIGHT_DB_RESULT_1]) # Or some representation of previous results
    mock_services["sql_executor"].execute_sql.assert_any_call(MOCK_INSIGHT_SQL_2)
    mock_services["response_synthesizer"].assess_insight_completeness.assert_any_call(user_query, [MOCK_INSIGHT_DB_RESULT_1, MOCK_INSIGHT_DB_RESULT_2]) # Or combined results

    assert mock_services["sql_generator"].generate_sql.call_count == 2
    assert mock_services["sql_executor"].execute_sql.call_count == 2
    assert mock_services["response_synthesizer"].assess_insight_completeness.call_count == 2

    # Verify final response synthesis was called once with all collected data
    mock_services["response_synthesizer"].synthesize_response.assert_called_once_with(user_query, [MOCK_INSIGHT_DB_RESULT_1, MOCK_INSIGHT_DB_RESULT_2])


def test_data_retrieval_sql_error_correction(mock_services):
    """Test data retrieval flow with a correctable SQL error."""
    user_query = "Show me the number of active users from the 'users' table"
    mock_schema = "Mock DB Schema DDL..."

    # Configure mocks for error correction flow
    mock_services["intent_analyzer"].analyze_intent.return_value = "DATA_RETRIEVAL"
    mock_services["schema_manager"].get_schema.return_value = mock_schema

    # Mock SQL generator to return the initial (incorrect) SQL
    mock_services["sql_generator"].generate_sql.return_value = MOCK_DATA_RETRIEVAL_SQL # This SQL assumes 'users' table

    # Mock SQL executor to raise an error on the first attempt
    mock_services["sql_executor"].execute_sql.side_effect = [
        Exception(MOCK_SQL_ERROR_MESSAGE), # Simulate DB error
        MOCK_CORRECTED_DB_RESULT # Successful result after correction
    ]

    # Mock error corrector to return a corrected SQL query
    mock_services["error_corrector"].handle_and_correct.return_value = MOCK_CORRECTED_SQL # Corrected SQL

    # Mock response synthesizer for the final successful response
    mock_services["response_synthesizer"].synthesize_response.return_value = {"response": "There are 5,678 active customers."} # Response based on corrected data

    # Ensure services for other intents are not called
    mock_services["chitchat_handler"].handle_chit_chat.assert_not_called()

    # Send request to the API
    response = client.post("/api/v1/query", json={"query": user_query})

    # Assert response status code and body
    assert response.status_code == 200
    assert response.json() == {"response": "There are 5,678 active customers."}

    # Verify mocks were called correctly
    mock_services["intent_analyzer"].analyze_intent.assert_called_once_with(user_query)
    mock_services["schema_manager"].get_schema.assert_called_once()

    # Verify SQL generation happened once initially
    mock_services["sql_generator"].generate_sql.assert_called_once_with(user_query, mock_schema, None)

    # Verify SQL execution happened twice (failed first, succeeded after correction)
    mock_services["sql_executor"].execute_sql.call_count == 2
    mock_services["sql_executor"].execute_sql.assert_any_call(MOCK_DATA_RETRIEVAL_SQL) # First call with original SQL
    mock_services["sql_executor"].execute_sql.assert_any_call(MOCK_CORRECTED_SQL) # Second call with corrected SQL

    # Verify error corrector was called once after the first execution failure
    mock_services["error_corrector"].handle_and_correct.assert_called_once_with(MOCK_DATA_RETRIEVAL_SQL, MOCK_SQL_ERROR_MESSAGE)

    # Verify response synthesis was called once with the final successful data
    mock_services["response_synthesizer"].synthesize_response.assert_called_once_with(user_query, MOCK_CORRECTED_DB_RESULT)


def test_data_retrieval_sql_error_correction_fails(mock_services):
    """Test data retrieval flow when SQL error correction fails."""
    user_query = "Show me data from a non_existent_table"
    mock_schema = "Mock DB Schema DDL..."

    # Configure mocks for failed error correction flow
    mock_services["intent_analyzer"].analyze_intent.return_value = "DATA_RETRIEVAL"
    mock_services["schema_manager"].get_schema.return_value = mock_schema

    # Mock SQL generator to return initial SQL
    initial_sql = "SELECT * FROM non_existent_table;"
    mock_services["sql_generator"].generate_sql.return_value = initial_sql

    # Mock SQL executor to raise an error repeatedly (simulating correction failure)
    # Assume the orchestrator/error corrector has a retry limit (e.g., 2 attempts total)
    mock_services["sql_executor"].execute_sql.side_effect = [
        Exception(MOCK_SQL_ERROR_MESSAGE), # First attempt
        Exception(MOCK_SQL_ERROR_MESSAGE)  # Second attempt after correction attempt
        # No more attempts expected
    ]

    # Mock error corrector to return a corrected SQL on the first call,
    # but the subsequent execution of that corrected SQL also fails.
    # The orchestrator should stop retrying after a limit.
    mock_services["error_corrector"].handle_and_correct.return_value = "SELECT * FROM still_wrong_table;" # Mock correction attempt

    # Mock response synthesizer to return an error response or a specific failure message
    # The orchestrator should catch the final exception and return an appropriate user-facing error
    # Let's assume the orchestrator returns a standard error detail on final failure
    # We don't mock synthesize_response here as it shouldn't be called on total failure


    # Ensure services for other intents are not called
    mock_services["chitchat_handler"].handle_chit_chat.assert_not_called()
    mock_services["response_synthesizer"].synthesize_response.assert_not_called()


    # Send request to the API
    response = client.post("/api/v1/query", json={"query": user_query})

    # Assert response status code and body - assuming a 500 or 400 level error for unrecoverable DB issue
    # Or the API might return 200 with an error message in the body depending on design
    # Let's assume the API returns a 500 Internal Server Error or similar for unhandled processing errors
    # If the orchestrator is designed to return a user-friendly error message in the 200 response body,
    # the assertion would check response.json()
    assert response.status_code == 500 # Or whatever the API returns for unrecoverable errors
    # assert response.json() == MOCK_ERROR_RESPONSE # If returning 200 with error body


    # Verify mocks were called correctly
    mock_services["intent_analyzer"].analyze_intent.assert_called_once_with(user_query)
    mock_services["schema_manager"].get_schema.assert_called_once()

    # Verify SQL generation happened once initially
    mock_services["sql_generator"].generate_sql.assert_called_once_with(user_query, mock_schema, None)

    # Verify SQL execution happened up to the retry limit (e.g., 2 times)
    assert mock_services["sql_executor"].execute_sql.call_count == 2
    mock_services["sql_executor"].execute_sql.assert_any_call(initial_sql) # First call with original SQL
    mock_services["sql_executor"].execute_sql.assert_any_call("SELECT * FROM still_wrong_table;") # Second call with corrected SQL

    # Verify error corrector was called once after the first execution failure
    mock_services["error_corrector"].handle_and_correct.assert_called_once_with(initial_sql, MOCK_SQL_ERROR_MESSAGE)

    # Verify response synthesis was NOT called
    mock_services["response_synthesizer"].synthesize_response.assert_not_called()

# Add more tests for edge cases, different query types, formatting validation, etc.
# For example:
# - Test with a query that should return no data
# - Test formatting of counts and revenues
# - Test insight generation that requires multiple steps and error correction within the loop