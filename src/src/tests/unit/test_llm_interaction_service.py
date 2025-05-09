import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# Assuming the LLMInteractionService is in src/core/llm_interaction_service.py
# and uses the 'openai' library.
# from src.core.llm_interaction_service import LLMInteractionService
# from src.core.config import Settings # Assuming Settings is used for config

# Mock the actual LLMInteractionService and Settings if they don't exist yet
# In a real project, you would import the actual classes.

class MockSettings:
    llm_api_key: str = "mock_llm_key"
    llm_model: str = "gpt-4o"
    retry_attempts: int = 3 # Assuming retry logic is in the service
    retry_delay_seconds: float = 0.1 # Assuming retry delay config

class MockLLMInteractionService:
    def __init__(self, settings: MockSettings):
        self.settings = settings
        # Mock the OpenAI client instance
        self._client = MagicMock()
        self._client.chat.completions.create = AsyncMock()

    async def get_completion(self, prompt: str, max_tokens: int = 150, temperature: float = 0.7):
        """Mock method for getting LLM completion."""
        # Simulate calling the mocked OpenAI client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = f"Mock response for: {prompt}"
        self._client.chat.completions.create.return_value = mock_response
        # In a real test, you might check the arguments passed to create
        # self._client.chat.completions.create.assert_called_once_with(...)
        return await self._client.chat.completions.create(
            model=self.settings.llm_model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=temperature
        )

    # Add mock methods for other potential interactions (e.g., embeddings)

# Mock the actual module path
# @pytest.fixture
# def llm_service(mocker):
#     settings = MockSettings()
#     # Mock the actual LLMInteractionService class
#     mock_service_class = mocker.patch('src.core.llm_interaction_service.LLMInteractionService')
#     mock_instance = mock_service_class.return_value
#     # Configure the mock instance's methods
#     mock_instance.get_completion = AsyncMock()
#     mock_instance.get_completion.return_value = "Mocked LLM response"
#     return mock_instance

# A better approach is to mock the external dependency (openai client)
# and test the actual LLMInteractionService logic (including retries, prompt formatting, etc.)
# assuming src.core.llm_interaction_service.py exists and has the class.

@pytest.fixture
def mock_openai_client(mocker):
    """Mocks the openai.OpenAI client."""
    mock_client = mocker.patch('openai.OpenAI')
    mock_instance = mock_client.return_value
    mock_instance.chat.completions.create = AsyncMock()
    return mock_instance

@pytest.fixture
def mock_settings(mocker):
    """Mocks the configuration settings."""
    mock_settings_obj = MockSettings()
    # If settings are loaded via a function, mock that function
    mocker.patch('src.core.config.get_settings', return_value=mock_settings_obj)
    # If settings are loaded via a class, mock the class instantiation
    mocker.patch('src.core.config.Settings', return_value=mock_settings_obj)
    return mock_settings_obj

# Now, write tests for the actual LLMInteractionService class,
# assuming it's in src/core/llm_interaction_service.py

# from src.core.llm_interaction_service import LLMInteractionService

# If the actual file doesn't exist, use the MockLLMInteractionService for demonstration
LLMInteractionService = MockLLMInteractionService # Replace with actual import

@pytest.mark.asyncio
async def test_get_completion_success(mock_openai_client, mock_settings):
    """Test successful LLM completion."""
    service = LLMInteractionService(mock_settings)

    # Configure the mock OpenAI client's response
    mock_response_obj = MagicMock()
    mock_response_obj.choices = [MagicMock()]
    mock_response_obj.choices[0].message.content = "This is a test response."
    mock_openai_client.chat.completions.create.return_value = mock_response_obj

    prompt = "Tell me a joke"
    response = await service.get_completion(prompt)

    assert response == "This is a test response."
    mock_openai_client.chat.completions.create.assert_called_once_with(
        model=mock_settings.llm_model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=150,
        temperature=0.7
    )

@pytest.mark.asyncio
async def test_get_completion_with_custom_params(mock_openai_client, mock_settings):
    """Test LLM completion with custom parameters."""
    service = LLMInteractionService(mock_settings)

    mock_response_obj = MagicMock()
    mock_response_obj.choices = [MagicMock()]
    mock_response_obj.choices[0].message.content = "Short response."
    mock_openai_client.chat.completions.create.return_value = mock_response_obj

    prompt = "Another prompt"
    max_tokens = 50
    temperature = 0.1
    response = await service.get_completion(prompt, max_tokens=max_tokens, temperature=temperature)

    assert response == "Short response."
    mock_openai_client.chat.completions.create.assert_called_once_with(
        model=mock_settings.llm_model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
        temperature=temperature
    )

# Add tests for error handling and retries
# This requires simulating exceptions from the mock_openai_client
# and checking if the service retries based on the settings.

# Example test for retries (conceptual)
# from openai import APIError # Or the specific exception type

# @pytest.mark.asyncio
# async def test_get_completion_retries_on_error(mock_openai_client, mock_settings):
#     """Test that the service retries on API errors."""
#     mock_settings.retry_attempts = 2 # Total 1 initial + 2 retries = 3 calls
#     service = LLMInteractionService(mock_settings)

#     # Make the first two calls raise an error, the third succeed
#     mock_openai_client.chat.completions.create.side_effect = [
#         APIError("Transient error 1", request=None, response=None, body=None),
#         APIError("Transient error 2", request=None, response=None, body=None),
#         MagicMock(choices=[MagicMock(message=MagicMock(content="Success after retry"))])
#     ]

#     prompt = "Retry test"
#     response = await service.get_completion(prompt)

#     assert response == "Success after retry"
#     assert mock_openai_client.chat.completions.create.call_count == 3 # Initial + 2 retries

# @pytest.mark.asyncio
# async def test_get_completion_fails_after_max_retries(mock_openai_client, mock_settings):
#     """Test that the service fails after exceeding max retries."""
#     mock_settings.retry_attempts = 1 # Total 1 initial + 1 retry = 2 calls
#     service = LLMInteractionService(mock_settings)

#     # Make all calls raise an error
#     mock_openai_client.chat.completions.create.side_effect = APIError("Persistent error", request=None, response=None, body=None)

#     prompt = "Failure test"
#     with pytest.raises(APIError): # Or a custom exception raised by the service
#         await service.get_completion(prompt)

#     assert mock_openai_client.chat.completions.create.call_count == 2 # Initial + 1 retry