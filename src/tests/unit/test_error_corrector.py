import pytest
from unittest.mock import AsyncMock, MagicMock

# Assuming the SQLErrorCorrectionModule is in src/services/error_corrector.py
# and uses LLMInteractionService and potentially SQLGenerationModule.
# from src.services.error_corrector import SQLErrorCorrectionModule
# from src.core.llm_interaction_service import LLMInteractionService # Dependency
# from src.services.sql_generator import SQLGenerationModule # Optional Dependency for complex correction

# Mock the actual classes if they don't exist
class MockLLMInteractionService:
    def __init__(self, settings=None):
        pass
    async def get_completion(self, prompt: str, max_tokens: int = 150, temperature: float = 0.7):
        """Mock LLM completion for error correction."""
        # Simulate LLM suggesting a corrected query or analysis
        if "Analyze the SQL error" in prompt:
            if "relation \"non_existent_table\" does not exist" in prompt:
                return "Correction: The table 'non_existent_table' does not exist. Check table name.\nSuggested SQL: SELECT * FROM users;" # Simple correction
            elif "column \"user_name\" does not exist" in prompt:
                 return "Correction: Column name is misspelled. It should be 'username'.\nSuggested SQL: SELECT user_id, username FROM users;" # Correction with specific detail
            elif "syntax error" in prompt:
                 return "Correction: There is a syntax error near 'FROM'. Check SQL syntax.\nSuggested SQL: SELECT * FROM users;" # Generic correction
            else:
                return "Analysis: Could not determine specific correction.\nSuggested SQL: None" # Failed correction

        return "MOCK_CORRECTION_RESPONSE"

# Mock the actual SQLErrorCorrectionModule class if it doesn't exist
class MockSQLErrorCorrectionModule:
    def __init__(self, llm_service: MockLLMInteractionService, prompt_template: str, max_attempts: int = 2):
        self.llm_service = llm_service
        self.prompt_template = prompt_template
        self.max_attempts = max_attempts # Max correction attempts *after* the first failure

    async def attempt_correction(self, original_query: str, error_message: str, attempt_count: int) -> tuple[str | None, str]:
        """Mock method to attempt SQL correction."""
        if attempt_count >= self.max_attempts:
            return None, "Max correction attempts reached."

        prompt = self.prompt_template.replace("{original_query}", original_query).replace("{error_message}", error_message)
        llm_response = await self.llm_service.get_completion(prompt)

        # Simulate parsing LLM response
        suggested_sql = None
        analysis = "Could not parse LLM response."

        if "Suggested SQL:" in llm_response:
            parts = llm_response.split("Suggested SQL:", 1)
            analysis = parts[0].replace("Correction:", "").strip()
            suggested_sql = parts[1].strip()
            if suggested_sql.lower() == "none":
                 suggested_sql = None
                 analysis = analysis if analysis else "LLM suggested no correction."
        elif "Analysis:" in llm_response:
             analysis = llm_response.replace("Analysis:", "").strip()

        return suggested_sql, analysis

# Mock the actual module path and its dependencies
# @pytest.fixture
# def error_corrector(mocker):
#     mock_llm_service = MockLLMInteractionService()
#     # Mock the actual SQLErrorCorrectionModule class
#     mock_corrector_class = mocker.patch('src.services.error_corrector.SQLErrorCorrectionModule')
#     mock_instance = mock_corrector_class.return_value
#     mock_instance.attempt_correction = AsyncMock()
#     # Configure return values in tests
#     return mock_instance

# A better approach is to mock the LLMInteractionService dependency
# and test the actual SQLErrorCorrectionModule logic.
# Assuming src.services.error_corrector.py exists and has the class.

# from src.services.error_corrector import SQLErrorCorrectionModule
# from src.core.llm_interaction_service import LLMInteractionService # Actual dependency

@pytest.fixture
def mock_llm_service_for_correction(mocker):
    """Mocks the LLMInteractionService dependency for error correction."""
    mock_service = AsyncMock()
    def mock_get_completion(prompt, **kwargs):
        if "relation \"non_existent_table\" does not exist" in prompt:
            return AsyncMock(return_value="Correction: Table does not exist.\nSuggested SQL: SELECT * FROM users;")()
        elif "column \"user_name\" does not exist" in prompt:
             return AsyncMock(return_value="Correction: Column 'user_name' is wrong, use 'username'.\nSuggested SQL: SELECT user_id, username FROM users;")()
        elif "syntax error" in prompt:
             return AsyncMock(return_value="Correction: Check syntax.\nSuggested SQL: SELECT 1;")()
        elif "division by zero" in prompt:
             return AsyncMock(return_value="Analysis: Division by zero occurred.\nSuggested SQL: None")() # Simulate no SQL correction possible
        else:
            return AsyncMock(return_value="Analysis: Unhandled error.\nSuggested SQL: None")()

    mock_service.get_completion.side_effect = mock_get_completion
    return mock_service

@pytest.fixture
def error_corrector_instance(mock_llm_service_for_correction):
    """Provides an instance of SQLErrorCorrectionModule with mocked dependencies."""
    # Assuming prompt template and max attempts are loaded or passed during initialization
    prompt_template = """Analyze the following SQL query and the error message.
Suggest a corrected SQL query if possible, or provide analysis.
Original Query: {original_query}
Error Message: {error_message}
Respond format: Correction: [analysis]\nSuggested SQL: [corrected_query or None]
"""
    max_attempts = 2 # Corresponds to FR-ERROR-001 (2-3 attempts *after* initial failure)
    # In a real test, you'd import and instantiate the actual class:
    # return SQLErrorCorrectionModule(mock_llm_service_for_correction, prompt_template, max_attempts)
    # Using the mock class for demonstration:
    return MockSQLErrorCorrectionModule(mock_llm_service_for_correction, prompt_template, max_attempts)


@pytest.mark.asyncio
async def test_attempt_correction_success(error_corrector_instance, mock_llm_service_for_correction):
    """Test successful correction attempt."""
    original_query = "SELECT * FROM non_existent_table;"
    error_message = "relation \"non_existent_table\" does not exist"
    attempt_count = 0 # First attempt after initial failure

    suggested_sql, analysis = await error_corrector_instance.attempt_correction(original_query, error_message, attempt_count)

    assert suggested_sql == "SELECT * FROM users;"
    assert "Table does not exist." in analysis
    mock_llm_service_for_correction.get_completion.assert_called_once()
    called_prompt = mock_llm_service_for_correction.get_completion.call_args[0][0]
    assert original_query in called_prompt
    assert error_message in called_prompt


@pytest.mark.asyncio
async def test_attempt_correction_specific_error(error_corrector_instance, mock_llm_service_for_correction):
    """Test correction attempt for a specific error like misspelled column."""
    original_query = "SELECT user_name FROM users;"
    error_message = "column \"user_name\" does not exist"
    attempt_count = 1 # Second attempt

    suggested_sql, analysis = await error_corrector_instance.attempt_correction(original_query, error_message, attempt_count)

    assert suggested_sql == "SELECT user_id, username FROM users;"
    assert "Column 'user_name' is wrong, use 'username'." in analysis
    mock_llm_service_for_correction.get_completion.assert_called_once()
    called_prompt = mock_llm_service_for_correction.get_completion.call_args[0][0]
    assert original_query in called_prompt
    assert error_message in called_prompt


@pytest.mark.asyncio
async def test_attempt_correction_no_sql_suggestion(error_corrector_instance, mock_llm_service_for_correction):
    """Test correction attempt where LLM provides analysis but no SQL."""
    original_query = "SELECT 1/0;"
    error_message = "division by zero"
    attempt_count = 0

    suggested_sql, analysis = await error_corrector_instance.attempt_correction(original_query, error_message, attempt_count)

    assert suggested_sql is None
    assert "Division by zero occurred." in analysis
    mock_llm_service_for_correction.get_completion.assert_called_once()


@pytest.mark.asyncio
async def test_attempt_correction_max_attempts_reached(error_corrector_instance, mock_llm_service_for_correction):
    """Test that correction stops after max attempts."""
    original_query = "SELECT * FROM non_existent_table;"
    error_message = "relation \"non_existent_table\" does not exist"
    attempt_count = error_corrector_instance.max_attempts # Attempt count equals or exceeds max allowed

    suggested_sql, analysis = await error_corrector_instance.attempt_correction(original_query, error_message, attempt_count)

    assert suggested_sql is None
    assert "Max correction attempts reached." in analysis
    # Verify LLM service was NOT called
    mock_llm_service_for_correction.get_completion.assert_not_called()

# Add tests for error handling if LLM service call fails during correction attempt