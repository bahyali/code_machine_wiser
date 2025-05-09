import logging
from core.llm_interaction_service import LLMInteractionService

logger = logging.getLogger(__name__)

class IntentAnalysisModule:
    def __init__(self):
        self.llm_service = LLMInteractionService() # Assuming LLMInteractionService is initialized here or injected
        # Load prompt template for intent analysis
        try:
            with open("src/prompts/intent_analysis.txt", "r") as f:
                self.prompt_template = f.read()
        except FileNotFoundError:
            logger.error("Intent analysis prompt template not found.")
            self.prompt_template = "Analyze the user query: {query}. Classify the intent as CHITCHAT, DATA_RETRIEVAL, or INSIGHTS. Respond only with the classification word." # Fallback

    async def analyze_intent(self, user_query: str, request_id: str = None) -> str:
        """
        Analyzes the user query to determine intent using the LLM.
        """
        logger.debug("Analyzing intent", extra={'request_id': request_id, 'user_query': user_query})

        prompt = self.prompt_template.format(query=user_query)

        try:
            # Call LLM service
            llm_response = await self.llm_service.get_completion(prompt, prompt_type="intent_analysis", request_id=request_id)

            # Simple parsing: expect one of the keywords
            intent = llm_response.strip().upper()
            if intent not in ["CHITCHAT", "DATA_RETRIEVAL", "INSIGHTS"]:
                 logger.warning(f"LLM returned unexpected intent format: {llm_response}", extra={'request_id': request_id, 'llm_response': llm_response})
                 # Fallback or raise error? Let's default to DATA_RETRIEVAL for safety or a generic response
                 intent = "DATA_RETRIEVAL" # Or "UNKNOWN" and handle in orchestrator

            logger.debug(f"Intent analysis complete: {intent}", extra={'request_id': request_id, 'intent': intent})
            return intent

        except Exception as e:
            logger.error("Error during intent analysis", extra={'request_id': request_id, 'user_query': user_query, 'error': str(e)}, exc_info=True)
            # Decide on fallback behavior: default intent, raise error, etc.
            # Returning DATA_RETRIEVAL might lead to SQL errors, returning CHITCHAT might be safer but wrong.
            # Let's return a default that the orchestrator can handle, maybe "ERROR"
            return "ERROR" # Orchestrator should handle this