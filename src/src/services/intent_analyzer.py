import logging
import os
from typing import Literal

# Assuming LLMInteractionService is in src.core.llm_interaction_service
from core.llm_interaction_service import LLMInteractionService

logger = logging.getLogger(__name__)

# Define the possible intent categories
Intent = Literal["CHITCHAT", "DATA_RETRIEVAL", "INSIGHTS"]

class IntentAnalysisModule:
    """
    Analyzes user queries to determine their intent using an LLM.
    """

    def __init__(self, llm_service: LLMInteractionService):
        """
        Initializes the IntentAnalysisModule with an LLM interaction service.

        Args:
            llm_service: An instance of LLMInteractionService.
        """
        self.llm_service = llm_service
        self.prompt_template_path = os.path.join(
            os.path.dirname(__file__), "..", "prompts", "intent_analysis.txt"
        )
        self._prompt_template = self._load_prompt_template()
        logger.info("IntentAnalysisModule initialized.")

    def _load_prompt_template(self) -> str:
        """
        Loads the intent analysis prompt template from a file.

        Returns:
            The content of the prompt template file.

        Raises:
            FileNotFoundError: If the prompt template file does not exist.
            IOError: If there is an error reading the file.
        """
        try:
            with open(self.prompt_template_path, "r", encoding="utf-8") as f:
                template = f.read()
            logger.debug(f"Loaded prompt template from {self.prompt_template_path}")
            return template
        except FileNotFoundError:
            logger.error(f"Prompt template file not found at {self.prompt_template_path}")
            raise
        except IOError as e:
            logger.error(f"Error reading prompt template file {self.prompt_template_path}: {e}")
            raise

    def analyze_intent(self, query: str) -> Intent:
        """
        Analyzes the user query to determine its intent using the LLM.

        Args:
            query: The user's natural language query.

        Returns:
            The classified intent as a string ("CHITCHAT", "DATA_RETRIEVAL", or "INSIGHTS").

        Raises:
            ValueError: If the LLM response cannot be parsed into a valid intent.
            Exception: Propagates exceptions from the LLM service.
        """
        if not self._prompt_template:
             raise RuntimeError("Prompt template not loaded.")

        formatted_prompt = self._prompt_template.format(user_query=query)
        logger.debug(f"Sending intent analysis prompt to LLM:\n{formatted_prompt}")

        try:
            llm_response = self.llm_service.get_completion(formatted_prompt)
            logger.debug(f"Received LLM response for intent analysis: {llm_response}")

            # Process the LLM response to extract the intent
            # Expecting a single word response like "CHITCHAT", "DATA_RETRIEVAL", "INSIGHTS"
            classified_intent = llm_response.strip().upper()

            # Validate the classified intent against expected categories
            valid_intents: list[Intent] = ["CHITCHAT", "DATA_RETRIEVAL", "INSIGHTS"]
            if classified_intent in valid_intents:
                logger.info(f"Query classified as intent: {classified_intent}")
                return classified_intent
            else:
                logger.warning(f"LLM returned unexpected intent format: '{llm_response}'. Classified as UNKNOWN.")
                # Depending on requirements, you might raise an error, return a default, or log and continue.
                # For now, raise an error as per the acceptance criteria implies a valid classification is expected.
                # Or, we could return a specific 'UNKNOWN' intent if the system is designed to handle it.
                # Let's raise an error to indicate the LLM didn't follow instructions, which needs investigation.
                raise ValueError(f"LLM response '{llm_response}' could not be parsed into a valid intent. Expected one of {valid_intents}.")

        except Exception as e:
            logger.error(f"Error during intent analysis for query '{query[:100]}...': {e}")
            # Re-raise the exception to be handled by the caller (e.g., the orchestrator)
            raise

# Example usage (for testing instantiation and method call)
if __name__ == "__main__":
    # Configure basic logging for the example
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__) # Re-get logger after config

    print("\n--- Testing IntentAnalysisModule ---")

    # --- Mock LLMInteractionService for standalone testing ---
    # In a real application, you would pass a real instance.
    # Here, we mock it to test the IntentAnalysisModule logic in isolation.
    class MockLLMInteractionService:
        def __init__(self, mock_responses: dict):
            self.mock_responses = mock_responses
            self._call_count = 0

        def get_completion(self, prompt: str, **kwargs) -> str:
            self._call_count += 1
            logger.info(f"Mock LLM call {self._call_count}: Prompt starts with '{prompt[:50]}...'")
            # Simple mock: look for keywords in the prompt to return a specific response
            # A more sophisticated mock might parse the prompt more carefully
            if "general conversation" in prompt:
                 response = self.mock_responses.get("CHITCHAT", "Mock CHITCHAT response.")
            elif "specific data points" in prompt or "summaries" in prompt:
                 response = self.mock_responses.get("DATA_RETRIEVAL", "Mock DATA_RETRIEVAL response.")
            elif "analysis" in prompt or "trends" in prompt or "insights" in prompt:
                 response = self.mock_responses.get("INSIGHTS", "Mock INSIGHTS response.")
            else:
                 # Default or fallback response
                 response = self.mock_responses.get("DEFAULT", "Mock UNKNOWN response.")

            # Simulate LLM delay
            # import time
            # time.sleep(0.1)
            logger.debug(f"Mock LLM response: '{response}'")
            return response

    # Define mock responses for different prompt types
    mock_responses = {
        "CHITCHAT": "CHITCHAT",
        "DATA_RETRIEVAL": "DATA_RETRIEVAL",
        "INSIGHTS": "INSIGHTS",
        "DEFAULT": "UNKNOWN_FORMAT", # Simulate a bad response
    }
    mock_llm_service = MockLLMInteractionService(mock_responses)

    # --- Instantiate and Test the Module ---
    intent_module = None
    try:
        intent_module = IntentAnalysisModule(llm_service=mock_llm_service)
        print("IntentAnalysisModule instantiated successfully.")

        # Test cases
        queries_to_test = [
            "Hello, how are you?", # Should be CHITCHAT
            "What is the total revenue for last month?", # Should be DATA_RETRIEVAL
            "Can you show me the sales trend over the past year?", # Should be INSIGHTS
            "Tell me a joke.", # Should be CHITCHAT
            "List all customers in California.", # Should be DATA_RETRIEVAL
            "Why did sales drop in Q3?", # Should be INSIGHTS
            "What is the meaning of life?", # Should be CHITCHAT (general knowledge/philosophy)
            "Show me the count of active users.", # Should be DATA_RETRIEVAL
        ]

        for query in queries_to_test:
            print(f"\nAnalyzing query: '{query}'")
            try:
                intent = intent_module.analyze_intent(query)
                print(f"Classified Intent: {intent}")
            except ValueError as ve:
                 print(f"Classification Error: {ve}")
            except Exception as e:
                print(f"An unexpected error occurred during analysis: {e}")

        # Test with a query that might trigger a bad mock response
        print("\nAnalyzing query designed to fail mock:")
        try:
            # Temporarily change mock response for this test
            mock_llm_service.mock_responses["DEFAULT"] = "GARBAGE RESPONSE"
            intent = intent_module.analyze_intent("This is a weird query.")
            print(f"Classified Intent: {intent}")
        except ValueError as ve:
             print(f"Classification Error (expected): {ve}")
        except Exception as e:
            print(f"An unexpected error occurred during analysis: {e}")
        finally:
             # Restore mock response
             mock_llm_service.mock_responses["DEFAULT"] = "UNKNOWN_FORMAT"


    except FileNotFoundError:
        print("Error: Prompt template file not found. Cannot run tests.")
    except Exception as e:
        print(f"An error occurred during module instantiation or testing setup: {e}")