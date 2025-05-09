import logging
from core.llm_interaction_service import LLMInteractionService

logger = logging.getLogger(__name__)

class ChitChatHandlerModule:
    def __init__(self):
        self.llm_service = LLMInteractionService() # Assuming LLMInteractionService is initialized here or injected
        # Load prompt template for chit-chat
        try:
            with open("src/prompts/chitchat_response.txt", "r") as f:
                self.prompt_template = f.read()
        except FileNotFoundError:
            logger.error("Chit-chat prompt template not found.")
            self.prompt_template = "Respond conversationally to: {query}" # Fallback

    async def handle_chit_chat(self, user_query: str, request_id: str = None) -> str:
        """
        Generates a conversational response for chit-chat queries using the LLM.
        """
        logger.debug("Handling chit-chat query", extra={'request_id': request_id, 'user_query': user_query})

        prompt = self.prompt_template.format(query=user_query)

        try:
            # Call LLM service
            llm_response = await self.llm_service.get_completion(prompt, prompt_type="chit_chat", request_id=request_id)

            logger.debug("Chit-chat response generated", extra={'request_id': request_id})
            return llm_response.strip()

        except Exception as e:
            logger.error("Error during chit-chat handling", extra={'request_id': request_id, 'user_query': user_query, 'error': str(e)}, exc_info=True)
            # Fallback response
            return "I'm sorry, I can't chat right now."