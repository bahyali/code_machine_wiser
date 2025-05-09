import pytest
from unittest.mock import AsyncMock, MagicMock

# Assuming the IntentAnalysisModule is in src/services/intent_analyzer.py
# and uses LLMInteractionService.
# from src.services.intent_analyzer import IntentAnalysisModule
# from src.core.llm_interaction_service import LLMInteractionService # Dependency

# Mock the actual classes if they don't exist
class MockLLMInteractionService:
    def __init__(self, settings=None):
        pass # No settings needed for this mock
    async def get_completion(self, prompt: str, max_tokens: int = 150, temperature: float = 0.7):
        """Mock LLM completion for intent analysis."""
        # Simulate LLM response based on prompt content or a predefined pattern
        if "classify the intent" in prompt.lower():
            if "sales figures" in prompt.lower() or "revenue" in prompt.lower():
                return "DATA_RETRIEVAL"
            elif "tell me a joke" in prompt.lower() or "hello" in prompt.lower():
                return "CHITCHAT"
            elif "trends" in prompt.lower() or "analyze" in prompt.lower():
                return "INSIGHTS"
            else:
                return "UNKNOWN"
        return "MOCK_LLM_RESPONSE" # Default if prompt format is unexpected

class MockIntentAnalysisModule:
    def __init__(self, llm_service: MockLLMInteractionService, prompt_template: str):
        self.llm_service = llm_service
        self.prompt_template = prompt_template # Store template for potential checks

    async def analyze_intent(self, query: str) -> str:
        """Mock method to analyze intent."""
        # Simulate constructing the prompt using the template
        prompt = self.prompt_template.replace("{query}", query)
        # Call the mock LLM service
        intent = await self.llm_service.get_completion(prompt)
        return intent.strip() # Simulate stripping whitespace

# Mock the actual module path and its dependencies
# @pytest.fixture
# def intent_analyzer(mocker):
#     mock_llm_service = MockLLMInteractionService() # Or mock the actual LLMInteractionService
#     # Mock the actual IntentAnalysisModule class
#     mock_analyzer_class = mocker.patch('src.services.intent_analyzer.IntentAnalysisModule')
#     # Configure the mock instance
#     mock_instance = mock_analyzer_class.return_value
#     mock_instance.analyze_intent = AsyncMock()
#     # We need to configure the return value based on input query in tests
#     return mock_instance

# A better approach is to mock the LLMInteractionService dependency
# and test the actual IntentAnalysisModule logic.
# Assuming src.services.intent_analyzer.py exists and has the class.

# from src.services.intent_analyzer import IntentAnalysisModule
# from src.core.llm_interaction_service import LLMInteractionService # Actual dependency

@pytest.fixture
def mock_llm_service_for_intent(mocker):
    """Mocks the LLMInteractionService dependency for intent analysis."""
    mock_service = AsyncMock()
    # Configure the mock get_completion to return specific intents
    def mock_get_completion(prompt, **kwargs):
        if "sales figures" in prompt.lower() or "revenue" in prompt.lower():
            return AsyncMock(return_value="DATA_RETRIEVAL")()
        elif "tell me a joke" in prompt.lower() or "hello" in prompt.lower():
            return AsyncMock(return_value="CHITCHAT")()
        elif "trends" in prompt.lower() or "analyze" in prompt.lower():
            return AsyncMock(return_value="INSIGHTS")()
        else:
            return AsyncMock(return_value="UNKNOWN")()

    mock_service.get_completion.side_effect = mock_get_completion
    return mock_service

@pytest.fixture
def intent_analyzer_instance(mock_llm_service_for_intent):
    """Provides an instance of IntentAnalysisModule with a mocked LLM service."""
    # Assuming the prompt template is loaded or passed during initialization
    # Let's assume it's passed during init for testability
    prompt_template = "User query: {query}\nClassify the intent: CHITCHAT, DATA_RETRIEVAL, INSIGHTS"
    # In a real test, you'd import and instantiate the actual class:
    # return IntentAnalysisModule(mock_llm_service_for_intent, prompt_template)
    # Using the mock class for demonstration:
    return MockIntentAnalysisModule(mock_llm_service_for_intent, prompt_template)


@pytest.mark.asyncio
async def test_analyze_intent_data_retrieval(intent_analyzer_instance, mock_llm_service_for_intent):
    """Test intent analysis for data retrieval query."""
    query = "What are the total sales figures for last month?"
    intent = await intent_analyzer_instance.analyze_intent(query)

    assert intent == "DATA_RETRIEVAL"
    # Verify LLM service was called with the correct prompt format
    expected_prompt_part = "User query: What are the total sales figures for last month?\nClassify the intent: CHITCHAT, DATA_RETRIEVAL, INSIGHTS"
    mock_llm_service_for_intent.get_completion.assert_called_once()
    # Check if the prompt passed to LLM service contains the expected parts
    called_prompt = mock_llm_service_for_intent.get_completion.call_args[0][0]
    assert expected_prompt_part in called_prompt


@pytest.mark.asyncio
async def test_analyze_intent_chit_chat(intent_analyzer_instance, mock_llm_service_for_intent):
    """Test intent analysis for chit-chat query."""
    query = "Tell me a joke about databases."
    intent = await intent_analyzer_instance.analyze_intent(query)

    assert intent == "CHITCHAT"
    expected_prompt_part = "User query: Tell me a joke about databases.\nClassify the intent: CHITCHAT, DATA_RETRIEVAL, INSIGHTS"
    mock_llm_service_for_intent.get_completion.assert_called_once()
    called_prompt = mock_llm_service_for_intent.get_completion.call_args[0][0]
    assert expected_prompt_part in called_prompt


@pytest.mark.asyncio
async def test_analyze_intent_insights(intent_analyzer_instance, mock_llm_service_for_intent):
    """Test intent analysis for insights query."""
    query = "Analyze the sales trends over the last year."
    intent = await intent_analyzer_instance.analyze_intent(query)

    assert intent == "INSIGHTS"
    expected_prompt_part = "User query: Analyze the sales trends over the last year.\nClassify the intent: CHITCHAT, DATA_RETRIEVAL, INSIGHTS"
    mock_llm_service_for_intent.get_completion.assert_called_once()
    called_prompt = mock_llm_service_for_intent.get_completion.call_args[0][0]
    assert expected_prompt_part in called_prompt

@pytest.mark.asyncio
async def test_analyze_intent_unknown(intent_analyzer_instance, mock_llm_service_for_intent):
    """Test intent analysis for unknown query."""
    query = "What is the capital of France?"
    intent = await intent_analyzer_instance.analyze_intent(query)

    assert intent == "UNKNOWN"
    expected_prompt_part = "User query: What is the capital of France?\nClassify the intent: CHITCHAT, DATA_RETRIEVAL, INSIGHTS"
    mock_llm_service_for_intent.get_completion.assert_called_once()
    called_prompt = mock_llm_service_for_intent.get_completion.call_args[0][0]
    assert expected_prompt_part in called_prompt

# Add tests for error handling if LLM service call fails