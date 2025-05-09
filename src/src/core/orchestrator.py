# This is a shell for the Query Orchestrator.
# It will be expanded in future tasks to handle intent analysis,
# SQL generation/execution, error correction, and response synthesis.

import logging

from models.query_models import QueryRequest, QueryResponse
from services.intent_analyzer import IntentAnalysisModule, Intent
from services.chitchat_handler import ChitChatHandlerModule

logger = logging.getLogger(__name__)

class QueryOrchestrator:
    """
    Manages the overall flow of processing a user query.
    Orchestrates different modules based on the analyzed intent.
    """

    def __init__(
        self,
        intent_analyzer: IntentAnalysisModule,
        chitchat_handler: ChitChatHandlerModule
    ):
        """
        Initializes the QueryOrchestrator with necessary modules.

        Args:
            intent_analyzer: An instance of IntentAnalysisModule.
            chitchat_handler: An instance of ChitChatHandlerModule.
        """
        self.intent_analyzer = intent_analyzer
        self.chitchat_handler = chitchat_handler
        logger.info("QueryOrchestrator initialized.")

    def process_query(self, query_request: QueryRequest) -> QueryResponse:
        """
        Processes the user's natural language query by analyzing intent
        and routing to the appropriate handler.

        Args:
            query_request: The user's natural language query wrapped in a QueryRequest object.

        Returns:
            A QueryResponse object containing the system's response.
        """
        query = query_request.query
        logger.info(f"Orchestrator received query: {query}")

        try:
            # 1. Analyze Intent
            intent = self.intent_analyzer.analyze_intent(query)
            logger.info(f"Query intent classified as: {intent}")

            # 2. Route based on Intent
            if intent == "CHITCHAT":
                logger.debug("Routing to ChitChatHandlerModule.")
                # 3. Handle Chit-Chat
                response_text = self.chitchat_handler.generate_response(query)
                logger.info("Chit-chat response generated.")
                return QueryResponse(response=response_text)

            elif intent == "DATA_RETRIEVAL":
                logger.debug("Intent is DATA_RETRIEVAL. Returning placeholder.")
                # TODO: Implement Data Retrieval flow in a future task (I3)
                placeholder_response = "OK. I understand you want to retrieve data. This functionality is coming soon!"
                return QueryResponse(response=placeholder_response)

            elif intent == "INSIGHTS":
                logger.debug("Intent is INSIGHTS. Returning placeholder.")
                # TODO: Implement Insights flow in a future task (I4)
                placeholder_response = "Interesting! You're asking for insights. I'm still learning how to do that, but stay tuned!"
                return QueryResponse(response=placeholder_response)

            else:
                 # This case should ideally be caught by IntentAnalysisModule validation,
                 # but as a fallback, handle unexpected intents.
                 logger.warning(f"Unknown or unhandled intent: {intent}. Returning generic placeholder.")
                 placeholder_response = "I'm not sure how to handle that request yet."
                 return QueryResponse(response=placeholder_response)

        except ValueError as ve:
            # Handle cases where intent analysis fails to return a valid intent
            logger.error(f"Intent analysis failed: {ve}")
            error_response = "I had trouble understanding your request. Could you please rephrase?"
            return QueryResponse(response=error_response)
        except Exception as e:
            # Catch any other unexpected errors during orchestration
            logger.exception(f"An unexpected error occurred during query processing for query '{query[:100]}...': {e}")
            error_response = "An internal error occurred while processing your request. Please try again later."
            return QueryResponse(response=error_response)

# Example usage (for testing instantiation and method call flow)
if __name__ == "__main__":
    # This block requires mock or actual dependencies (LLMInteractionService, IntentAnalysisModule, ChitChatHandlerModule)
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__) # Re-get logger after config

    print("\n--- Testing QueryOrchestrator Integration ---")

    # --- Mock Dependencies for standalone testing ---
    # In a real application, these would be actual instances initialized elsewhere.
    class MockLLMInteractionService:
        def get_completion(self, prompt: str, **kwargs) -> str:
            logger.debug(f"Mock LLM received prompt: {prompt[:100]}...")
            # Simple mock logic based on prompt content
            if "classify the intent" in prompt:
                if "hello" in prompt.lower() or "how are you" in prompt.lower() or "joke" in prompt.lower():
                    return "CHITCHAT"
                elif "revenue" in prompt.lower() or "sales" in prompt.lower() or "customers" in prompt.lower():
                    return "DATA_RETRIEVAL"
                elif "trend" in prompt.lower() or "insights" in prompt.lower() or "why" in prompt.lower():
                     return "INSIGHTS"
                else:
                    return "UNKNOWN" # Simulate an unknown intent response
            elif "Respond conversationally" in prompt:
                 user_query_match = prompt.split("user\'s input:")[-1].strip()
                 return f"Mock chit-chat response to: '{user_query_match}'. I am a mock assistant!"
            else:
                return "Mock LLM default response."

    mock_llm_service = MockLLMInteractionService()

    # Instantiate dependent modules with the mock LLM service
    # Note: IntentAnalysisModule and ChitChatHandlerModule might try to load prompt files.
    # For this standalone test, ensure dummy prompt files exist or mock the loading.
    # A simpler mock is to override the methods directly for testing the Orchestrator's logic.

    class MockIntentAnalysisModule:
         def __init__(self, llm_service):
             self.llm_service = llm_service
             logger.info("MockIntentAnalysisModule initialized.")

         def analyze_intent(self, query: str) -> Intent:
             logger.debug(f"Mock Intent Analysis for query: '{query}'")
             # Simulate calling LLM mock based on query content
             mock_prompt_part = f"classify the intent of '{query}'" # Simulate prompt content
             llm_response = self.llm_service.get_completion(mock_prompt_part)
             # In a real scenario, parse llm_response. Here, just return the mock's output directly.
             # Add basic validation expected by Orchestrator if needed for robustness test
             valid_intents: list[Intent] = ["CHITCHAT", "DATA_RETRIEVAL", "INSIGHTS"]
             if llm_response in valid_intents:
                 return llm_response
             elif llm_response == "UNKNOWN":
                  raise ValueError(f"Mock LLM returned unknown intent: {llm_response}")
             else:
                  # Simulate LLM returning something unexpected
                  raise ValueError(f"Mock LLM returned unexpected format: {llm_response}")


    class MockChitChatHandlerModule:
         def __init__(self, llm_service):
             self.llm_service = llm_service
             logger.info("MockChitChatHandlerModule initialized.")

         def generate_response(self, user_query: str, **llm_kwargs) -> str:
             logger.debug(f"Mock Chit-Chat Generation for query: '{user_query}'")
             # Simulate calling LLM mock
             mock_prompt_part = f"Respond conversationally to the user's input: {user_query}"
             return self.llm_service.get_completion(mock_prompt_part)


    mock_intent_analyzer = MockIntentAnalysisModule(llm_service=mock_llm_service)
    mock_chitchat_handler = MockChitChatHandlerModule(llm_service=mock_llm_service)

    # --- Instantiate the Orchestrator with mocks ---
    orchestrator = QueryOrchestrator(
        intent_analyzer=mock_intent_analyzer,
        chitchat_handler=mock_chitchat_handler
    )
    print("QueryOrchestrator instantiated successfully with mock modules.")

    # --- Test cases ---
    queries_to_test = [
        "Hello, how are you?",       # Should be CHITCHAT
        "What is the total revenue?", # Should be DATA_RETRIEVAL
        "Show me sales trends.",      # Should be INSIGHTS
        "Tell me a joke.",            # Should be CHITCHAT
        "List all customers.",        # Should be DATA_RETRIEVAL
        "Why did sales drop?",        # Should be INSIGHTS
        "This is a weird query.",     # Should trigger UNKNOWN/ValueError in mock
    ]

    for query_text in queries_to_test:
        print(f"\nProcessing query: '{query_text}'")
        query_request = QueryRequest(query=query_text)
        response = orchestrator.process_query(query_request)
        print(f"Orchestrator Response: '{response.response}'")

    print("\n--- QueryOrchestrator Integration Test Complete ---")