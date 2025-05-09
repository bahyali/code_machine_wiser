import logging
import time
from typing import Any, Dict, List, Optional

# Assuming config is in src.core.config
from core.config import Settings

# Import OpenAI library and specific exceptions for handling
import openai
from openai import OpenAI
from openai import APIError, RateLimitError, Timeout, APIConnectionError

# Import tenacity for retries
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)

# Define a retry strategy for transient OpenAI API errors
# Retry on APIError (covers 500s), RateLimitError (429), Timeout, APIConnectionError
# Wait exponentially between retries, up to LLM_MAX_RETRIES attempts.
# The timeout setting from config will be handled by the OpenAI client itself.
RETRY_STRATEGY = retry(
    stop=stop_after_attempt(Settings().LLM_MAX_RETRIES), # Use settings for max attempts
    wait=wait_exponential(multiplier=1, min=4, max=10), # Wait 2^x * multiplier seconds, max 10s
    retry=retry_if_exception_type((APIError, RateLimitError, Timeout, APIConnectionError)),
    before_sleep=lambda retry_state: logger.warning(
        f"Retrying LLM API call (attempt {retry_state.attempt_number}/{Settings().LLM_MAX_RETRIES}). "
        f"Waiting {retry_state.next_action.sleep} seconds due to {retry_state.outcome.exception()}..."
    )
)


class LLMInteractionService:
    """
    Service for interacting with the LLM API (e.g., GPT-4o).

    Initializes with configuration settings and provides methods
    for making LLM calls with error handling.
    """

    def __init__(self, settings: Settings):
        """
        Initializes the LLMInteractionService with application settings
        and the OpenAI client.

        Args:
            settings: The application settings object containing LLM configuration.
        """
        self.settings: Settings = settings
        self.api_key: str = settings.OPENAI_API_KEY
        self.model: str = settings.LLM_MODEL
        self.temperature: float = settings.LLM_TEMPERATURE
        self.timeout: int = settings.LLM_TIMEOUT_SECONDS
        self.max_retries: int = settings.LLM_MAX_RETRIES # Used by tenacity decorator

        # Initialize the OpenAI client
        # The timeout parameter here applies to the entire request, including retries.
        # tenacity handles the retries themselves based on exceptions.
        try:
            self.client: OpenAI = OpenAI(
                api_key=self.api_key,
                timeout=self.timeout,
            )
            logger.info(f"LLMInteractionService initialized for model: {self.model}")
            # Avoid logging the full API key
            logger.debug(f"LLM API Key loaded (first 4 chars): {self.api_key[:4]}****")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}")
            # Depending on application design, you might raise the exception
            # or handle it as a critical startup failure.
            raise

    @RETRY_STRATEGY
    def _create_chat_completion(self, messages: List[Dict[str, str]], **kwargs: Any) -> str:
        """
        Internal method to call the OpenAI chat completions API with retry logic.

        Args:
            messages: A list of message dictionaries for the chat history.
            **kwargs: Additional parameters for the LLM call (e.g., max_tokens, stop).

        Returns:
            The text content of the LLM's response.

        Raises:
            openai.APIError: If the API call fails after all retries.
            Exception: For other unexpected errors.
        """
        logger.debug(f"Attempting LLM chat completion call with model: {self.model}")
        # Log messages carefully, especially in production
        logger.debug(f"Messages: {messages}")
        logger.debug(f"Call kwargs: {kwargs}")

        try:
            # Merge default parameters with provided kwargs, kwargs take precedence
            call_params = {
                "model": self.model,
                "messages": messages,
                "temperature": self.temperature,
                **kwargs
            }

            response = self.client.chat.completions.create(**call_params)

            if not response.choices:
                logger.error("LLM API call returned no choices.")
                # This might indicate an unexpected API response structure
                raise APIError("LLM API call returned no choices.", response=response)

            completion_text = response.choices[0].message.content
            if completion_text is None:
                 logger.warning("LLM API call returned a choice with None content.")
                 # Treat None content as a failure or empty response depending on context
                 # For now, raise an error to indicate something unexpected happened
                 raise APIError("LLM API call returned None content.", response=response)


            logger.debug(f"LLM API call successful. Response: {completion_text[:200]}...")
            return completion_text

        except (APIError, RateLimitError, Timeout, APIConnectionError) as e:
            logger.error(f"LLM API transient error: {e}")
            # tenacity will catch these and trigger a retry if attempts remain
            raise # Re-raise to allow tenacity to handle

        except Exception as e:
            logger.exception(f"An unexpected error occurred during LLM API call: {e}")
            # For non-transient errors or errors after retries, tenacity stops and re-raises the last exception.
            # If this catch block is reached, it's likely an error tenacity wasn't configured to retry,
            # or an error during response processing.
            raise # Re-raise the exception

    def get_completion(self, prompt: str, **kwargs: Any) -> str:
        """
        Gets a completion from the LLM based on a single prompt string.
        This method wraps the chat completion API for simple text-in/text-out use cases.

        Args:
            prompt: The prompt string to send to the LLM.
            **kwargs: Additional parameters for the LLM call (e.g., max_tokens, stop).
                      These override default settings like temperature if provided.

        Returns:
            The LLM's response as a string.

        Raises:
            Exception: If the LLM API call fails after retries or encounters a non-retryable error.
        """
        logger.info(f"LLMInteractionService received prompt: {prompt[:200]}...")

        # Construct messages list for chat completion API
        messages = [{"role": "user", "content": prompt}]

        try:
            # Call the internal method with retry logic
            completion = self._create_chat_completion(messages, **kwargs)
            logger.info("Successfully received LLM completion.")
            return completion
        except Exception as e:
            logger.error(f"Failed to get LLM completion after multiple retries or due to unhandled error: {e}")
            # Re-raise the exception to be handled by the caller (e.g., the orchestrator)
            raise

    # You might add other methods here based on anticipated needs,
    # e.g., for chat completions with history, structured output, etc.
    # def get_chat_completion(self, messages: list[Dict[str, str]], **kwargs: Any) -> str:
    #     """Gets a completion from the LLM based on a list of messages."""
    #     logger.info(f"LLMInteractionService received chat messages.")
    #     try:
    #         completion = self._create_chat_completion(messages, **kwargs)
    #         logger.info("Successfully received LLM chat completion.")
    #         return completion
    #     except Exception as e:
    #         logger.error(f"Failed to get LLM chat completion: {e}")
    #         raise


# Example usage (for testing instantiation and method call)
if __name__ == "__main__":
    # Configure basic logging for the example
    logging.basicConfig(level=logging.DEBUG)

    # Assume settings are loaded (as done in core/config __main__)
    # In a real app, you'd import the settings instance: from core.config import settings
    # For this standalone test, we'll load them explicitly if not already loaded
    try:
        from core.config import settings
        print("Using settings from core.config.")
    except ImportError:
        # Fallback for running this file directly if core.config isn't importable yet
        print("Could not import settings from core.config. Attempting local load.")
        # This requires a .env file with OPENAI_API_KEY and potentially config.yaml
        # For a true shell test, you might mock settings or create minimal ones.
        # Let's create minimal mock settings for demonstration.
        # NOTE: This mock will NOT allow actual API calls unless you replace the key.
        class MockSettings:
            OPENAI_API_KEY: str = "sk-mock-key-1234" # Replace with a real key or mock the client for testing
            LLM_MODEL: str = "gpt-4o-mini" # Use a cheap model for testing
            LLM_TEMPERATURE: float = 0.5
            LLM_TIMEOUT_SECONDS: int = 30
            LLM_MAX_RETRIES: int = 1 # Keep low for quick test failures

            # Add other required settings if BaseSettings validation was strict
            APP_NAME: str = "Mock App"
            APP_VERSION: str = "0.0.1"
            ENVIRONMENT: str = "test"
            API_V1_STR: str = "/api/v1"
            HOST: str = "0.0.0.0"
            PORT: int = 8000
            DATABASE_URL: Optional[str] = None
            DB_HOST: Optional[str] = None
            DB_PORT: Optional[int] = 5432
            DB_NAME: Optional[str] = None
            DB_USER: Optional[str] = None
            DB_PASSWORD: Optional[str] = None
            SQL_TIMEOUT_SECONDS: int = 30
            SQL_MAX_ROWS_RETURNED: int = 1000
            SQL_ERROR_CORRECTION_MAX_ATTEMPTS: int = 2
            _CONFIG_FILE_PATH: str = "config.yaml"

        settings = MockSettings()
        print("Using mock settings.")


    print("\n--- Testing LLMInteractionService ---")

    # Instantiate the service
    llm_service = None
    try:
        # Ensure you have a valid OPENAI_API_KEY in your environment or .env file
        # if you are not using the mock settings with a real key.
        if settings.OPENAI_API_KEY == "sk-mock-key-1234":
             print("WARNING: Using mock API key. Actual API calls will fail unless replaced.")
             # For testing the service structure without a real key, you would mock openai.OpenAI
             # import unittest.mock
             # with unittest.mock.patch('openai.OpenAI') as MockOpenAI:
             #    MockOpenAI.return_value.chat.completions.create.return_value.choices = [unittest.mock.Mock(message=unittest.mock.Mock(content="Mocked LLM Response"))]
             #    llm_service = LLMInteractionService(settings)
             #    ... test calls ...
             # This example doesn't include full mocking setup.
             pass # Skip instantiation if using mock key without mocking client

        if settings.OPENAI_API_KEY != "sk-mock-key-1234":
            llm_service = LLMInteractionService(settings)
            print("LLMInteractionService instantiated successfully.")

            # Call the actual method
            test_prompt = "What is the capital of France? Respond concisely."
            print(f"Calling get_completion with prompt: '{test_prompt}'")
            try:
                response = llm_service.get_completion(test_prompt)
                print(f"Received response: '{response}'")
            except Exception as e:
                print(f"Error during get_completion call: {e}")

            print("-" * 20)

            # Test with kwargs
            test_prompt_with_kwargs = "Tell me a very short joke."
            print(f"Calling get_completion with prompt: '{test_prompt_with_kwargs}' and kwargs (max_tokens=30).")
            try:
                response_with_kwargs = llm_service.get_completion(
                    test_prompt_with_kwargs,
                    max_tokens=30,
                    stop=["\n\n"]
                )
                print(f"Received response: '{response_with_kwargs}'")
            except Exception as e:
                 print(f"Error during get_completion call with kwargs: {e}")

        else:
             print("Skipping actual API calls due to mock API key.")


    except Exception as e:
        print(f"An error occurred during service instantiation or testing setup: {e}")