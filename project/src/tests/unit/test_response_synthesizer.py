import pytest
from unittest.mock import AsyncMock, MagicMock

# Assuming the ResponseSynthesisModule is in src/services/response_synthesizer.py
# and uses LLMInteractionService and DataFormatterValidatorModule.
# from src.services.response_synthesizer import ResponseSynthesisModule
# from src.core.llm_interaction_service import LLMInteractionService # Dependency
# from src.services.formatter_validator import DataFormatterValidatorModule # Dependency

# Mock the actual classes if they don't exist
class MockLLMInteractionService:
    def __init__(self, settings=None):
        pass
    async def get_completion(self, prompt: str, max_tokens: int = 150, temperature: float = 0.7):
        """Mock LLM completion for response synthesis."""
        # Simulate response generation based on prompt content
        if "Synthesize a natural language response" in prompt:
            if "sales data" in prompt:
                return "Based on the data, the total sales are [FORMATTED_SALES_VALUE]."
            elif "user list" in prompt:
                 return "Here is a list of users: [FORMATTED_USER_LIST]."
            elif "monthly trends" in prompt:
                 return "Analysis of monthly trends shows [INSIGHT_SUMMARY]."
        return "MOCK_SYNTHESIS_RESPONSE"

class MockDataFormatterValidatorModule:
    def __init__(self):
        pass
    def format_data(self, data):
        """Mock method to format data."""
        # Simulate formatting based on data structure
        if isinstance(data, dict) and "rows" in data:
            if data["rows"] and isinstance(data["rows"][0], tuple):
                 # Simulate formatting for tabular data
                 header = data.get("columns", ["Col1", "Col2"])
                 formatted_rows = [", ".join(str(c) for c in row) for row in data["rows"]]
                 return f"| {' | '.join(header)} |\n|{'-' * (sum(len(h) for h in header) + len(header)*3 -1)}|\n" + "\n".join([f"| {' | '.join(row)} |" for row in formatted_rows])
            elif data["rows"] and isinstance(data["rows"][0], (int, float)):
                 # Simulate formatting for single value (like sum)
                 value = data["rows"][0]
                 # Apply specific formatting rules (mocked)
                 if "sum" in data.get("columns", [])[0].lower() or "revenue" in data.get("columns", [])[0].lower():
                      return f"{value:,.2f} SAR" # Simulate SAR formatting
                 elif "count" in data.get("columns", [])[0].lower():
                      return f"{int(value):,}" # Simulate whole number formatting
                 else:
                      return str(value)
        return str(data) # Default string conversion

    def validate_data_presentation(self, formatted_data):
        """Mock method to validate formatted data."""
        # In a real scenario, this would check if counts are whole numbers, SAR format is correct, etc.
        # For the mock, just return True
        return True


class MockResponseSynthesisModule:
    def __init__(self, llm_service: MockLLMInteractionService, formatter: MockDataFormatterValidatorModule, prompt_template_retrieval: str, prompt_template_insight: str):
        self.llm_service = llm_service
        self.formatter = formatter
        self.prompt_template_retrieval = prompt_template_retrieval
        self.prompt_template_insight = prompt_template_insight

    async def synthesize_response(self, query: str, data: dict | list, intent: str) -> str:
        """Mock method to synthesize response."""
        # Simulate compiling data (simple pass-through for mock)
        compiled_data = data

        # Simulate formatting data before sending to LLM (optional, depending on prompt strategy)
        # Or format after LLM response (more likely for presentation)

        # Choose prompt template based on intent
        prompt_template = self.prompt_template_retrieval if intent == "DATA_RETRIEVAL" else self.prompt_template_insight

        # Simulate preparing data for LLM prompt (e.g., converting dict/list to string)
        data_for_prompt = str(compiled_data) # Simple string conversion

        prompt = prompt_template.replace("{query}", query).replace("{data}", data_for_prompt)

        llm_response = await self.llm_service.get_completion(prompt)

        # Simulate formatting the final response, potentially replacing placeholders
        # This mock formatter is simple, let's assume it formats the raw data structure
        # and the LLM output might contain placeholders or just need insertion.
        # A more realistic mock would have the formatter process the LLM text output.

        # For this mock, let's assume the LLM output contains placeholders like [FORMATTED_SALES_VALUE]
        # and we use the formatter to generate the actual formatted string to replace it.
        final_response = llm_response
        if "[FORMATTED_SALES_VALUE]" in final_response:
             # Assume 'data' contains the raw sales value like {"columns": ["sum"], "rows": [(1234.50,)]}
             formatted_sales = self.formatter.format_data(data)
             final_response = final_response.replace("[FORMATTED_SALES_VALUE]", formatted_sales)
        elif "[FORMATTED_USER_LIST]" in final_response:
             # Assume 'data' contains user list like {"columns": ["user_id", "username"], "rows": [(1, 'alice'), (2, 'bob')]}
             formatted_users = self.formatter.format_data(data)
             final_response = final_response.replace("[FORMATTED_USER_LIST]", formatted_users)
        elif "[INSIGHT_SUMMARY]" in final_response:
             # Assume LLM output for insights is the final text, no specific formatting needed by formatter
             pass # Formatter might be used on intermediate data for insights, but not the final text

        # Simulate validation (optional, depending on where validation happens)
        # self.formatter.validate_data_presentation(final_response) # This would raise an error if validation fails

        return final_response.strip()

# Mock the actual module path and its dependencies
# @pytest.fixture
# def response_synthesizer(mocker):
#     mock_llm_service = MockLLMInteractionService()
#     mock_formatter = MockDataFormatterValidatorModule()
#     # Mock the actual ResponseSynthesisModule class
#     mock_synthesizer_class = mocker.patch('src.services.response_synthesizer.ResponseSynthesisModule')
#     mock_instance = mock_synthesizer_class.return_value
#     mock_instance.synthesize_response = AsyncMock()
#     # Configure return values in tests
#     return mock_instance

# A better approach is to mock the dependencies (LLM, Formatter)
# and test the actual ResponseSynthesisModule logic.
# Assuming src.services.response_synthesizer.py exists and has the class.

# from src.services.response_synthesizer import ResponseSynthesisModule
# from src.core.llm_interaction_service import LLMInteractionService # Actual dependency
# from src.services.formatter_validator import DataFormatterValidatorModule # Actual dependency

@pytest.fixture
def mock_llm_service_for_synthesis(mocker):
    """Mocks the LLMInteractionService dependency for response synthesis."""
    mock_service = AsyncMock()
    def mock_get_completion(prompt, **kwargs):
        if "sales data" in prompt:
            return AsyncMock(return_value="Based on the data, the total sales are [FORMATTED_SALES_VALUE].")()
        elif "user list" in prompt:
             return AsyncMock(return_value="Here is a list of users:\n[FORMATTED_USER_LIST]")()
        elif "monthly trends" in prompt:
             return AsyncMock(return_value="Analysis of monthly trends shows a steady increase in orders.")()
        else:
            return AsyncMock(return_value="Generic response.")()

    mock_service.get_completion.side_effect = mock_get_completion
    return mock_service

@pytest.fixture
def mock_formatter_validator(mocker):
    """Mocks the DataFormatterValidatorModule dependency."""
    mock_formatter = MagicMock()
    def mock_format_data(data):
        if isinstance(data, dict) and "rows" in data:
            if data["rows"] and isinstance(data["rows"][0], tuple):
                 # Simulate formatting for tabular data
                 header = data.get("columns", ["Col1", "Col2"])
                 formatted_rows = [", ".join(str(c) for c in row) for row in data["rows"]]
                 return f"| {' | '.join(header)} |\n|{'-' * (sum(len(h) for h in header) + len(header)*3 -1)}|\n" + "\n".join([f"| {' | '.join(row)} |" for row in formatted_rows])
            elif data["rows"] and isinstance(data["rows"][0], (int, float)):
                 # Simulate formatting for single value (like sum)
                 value = data["rows"][0][0] # Get the value from the tuple
                 if "sum" in data.get("columns", [])[0].lower() or "revenue" in data.get("columns", [])[0].lower():
                      return f"{value:,.2f} SAR"
                 elif "count" in data.get("columns", [])[0].lower():
                      return f"{int(value):,}"
                 else:
                      return str(value)
        return str(data) # Default string conversion

    mock_formatter.format_data.side_effect = mock_format_data
    mock_formatter.validate_data_presentation.return_value = True # Assume validation always passes for this mock

    return mock_formatter

@pytest.fixture
def response_synthesizer_instance(mock_llm_service_for_synthesis, mock_formatter_validator):
    """Provides an instance of ResponseSynthesisModule with mocked dependencies."""
    # Assuming prompt templates are loaded or passed during initialization
    prompt_template_retrieval = """Synthesize a natural language response based on the user query and the retrieved data.
User Query: {query}
Data: {data}
"""
    prompt_template_insight = """Analyze the compiled data and generate insights based on the user query.
User Query: {query}
Data: {data}
"""
    # In a real test, you'd import and instantiate the actual class:
    # return ResponseSynthesisModule(mock_llm_service_for_synthesis, mock_formatter_validator, prompt_template_retrieval, prompt_template_insight)
    # Using the mock class for demonstration:
    return MockResponseSynthesisModule(mock_llm_service_for_synthesis, mock_formatter_validator, prompt_template_retrieval, prompt_template_insight)


@pytest.mark.asyncio
async def test_synthesize_response_data_retrieval_scalar(response_synthesizer_instance, mock_llm_service_for_synthesis, mock_formatter_validator):
    """Test synthesis for data retrieval returning a single value (e.g., sum)."""
    query = "What are the total sales figures?"
    data = {"columns": ["sum"], "rows": [(1234.50,)]}
    intent = "DATA_RETRIEVAL"

    response = await response_synthesizer_instance.synthesize_response(query, data, intent)

    # Verify LLM service was called with correct prompt
    mock_llm_service_for_synthesis.get_completion.assert_called_once()
    called_prompt = mock_llm_service_for_synthesis.get_completion.call_args[0][0]
    assert query in called_prompt
    assert str(data) in called_prompt # Check if raw data string is in prompt

    # Verify formatter was called to format the scalar value
    mock_formatter_validator.format_data.assert_called_once_with(data)

    # Verify the final response contains the formatted value
    assert "Based on the data, the total sales are 1,234.50 SAR." in response


@pytest.mark.asyncio
async def test_synthesize_response_data_retrieval_table(response_synthesizer_instance, mock_llm_service_for_synthesis, mock_formatter_validator):
    """Test synthesis for data retrieval returning tabular data."""
    query = "List the first 2 users."
    data = {"columns": ["user_id", "username"], "rows": [(1, 'alice'), (2, 'bob')]}
    intent = "DATA_RETRIEVAL"

    response = await response_synthesizer_instance.synthesize_response(query, data, intent)

    # Verify LLM service was called
    mock_llm_service_for_synthesis.get_completion.assert_called_once()
    called_prompt = mock_llm_service_for_synthesis.get_completion.call_args[0][0]
    assert query in called_prompt
    assert str(data) in called_prompt

    # Verify formatter was called to format the table data
    mock_formatter_validator.format_data.assert_called_once_with(data)

    # Verify the final response contains the formatted table
    expected_formatted_table = """| user_id | username |
|--------------------|
| 1 | alice |
| 2 | bob |""" # Based on mock_format_data logic
    assert "Here is a list of users:\n" in response
    assert expected_formatted_table in response


@pytest.mark.asyncio
async def test_synthesize_response_insights(response_synthesizer_instance, mock_llm_service_for_synthesis, mock_formatter_validator):
    """Test synthesis for insights intent."""
    query = "Analyze monthly order trends."
    # Insights might involve multiple data points or compiled data
    data = [
        {"columns": ["month", "order_count"], "rows": [("2023-01", 100), ("2023-02", 120)]},
        {"columns": ["month", "revenue"], "rows": [("2023-01", 10000.00), ("2023-02", 15000.00)]}
    ]
    intent = "INSIGHTS"

    response = await response_synthesizer_instance.synthesize_response(query, data, intent)

    # Verify LLM service was called with the insight prompt template
    mock_llm_service_for_synthesis.get_completion.assert_called_once()
    called_prompt = mock_llm_service_for_synthesis.get_completion.call_args[0][0]
    assert "Analyze the compiled data and generate insights" in called_prompt # Check insight template part
    assert query in called_prompt
    assert str(data) in called_prompt

    # Verify formatter was NOT called on the final LLM response (assuming insight text doesn't need formatting)
    # It might be called on intermediate data *before* sending to LLM depending on implementation
    # For this mock, formatter is only called if specific placeholders are found in LLM output
    mock_formatter_validator.format_data.assert_not_called() # Based on mock LLM output for insights

    # Verify the final response is the mock insight summary
    assert response == "Analysis of monthly trends shows a steady increase in orders."

# Add tests for error handling if LLM service call fails
# Add tests for validation being called (if validation happens after synthesis)