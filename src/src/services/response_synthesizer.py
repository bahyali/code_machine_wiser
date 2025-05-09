import logging
from core.llm_interaction_service import LLMInteractionService

logger = logging.getLogger(__name__)

class ResponseSynthesisModule:
    def __init__(self):
        self.llm_service = LLMInteractionService() # Assuming LLMInteractionService is initialized here or injected
        # Load prompt templates
        try:
            with open("src/prompts/response_synthesis_retrieval.txt", "r") as f:
                self.retrieval_prompt_template = f.read()
            with open("src/prompts/response_synthesis_insight.txt", "r") as f:
                self.insight_prompt_template = f.read()
            with open("src/prompts/insight_completeness_check.txt", "r") as f:
                self.completeness_check_template = f.read()
        except FileNotFoundError:
            logger.error("Response synthesis or completeness check prompt templates not found.")
            self.retrieval_prompt_template = "Given the user query: {query}\nAnd the data: {data}\n\nSynthesize a natural language response." # Fallback
            self.insight_prompt_template = "Given the user query: {query}\nAnd the collected data: {data}\n\nSynthesize a comprehensive insight." # Fallback
            self.completeness_check_template = "Given the user query: {query}\nAnd the data collected so far: {data}\n\nIs the data sufficient to provide a complete insight? Respond 'YES' or 'NO', followed by suggested next steps if NO." # Fallback


    async def synthesize_response(self, user_query: str, query_results: list, request_id: str = None) -> str:
        """
        Synthesizes a natural language response from query results using the LLM.
        Handles both retrieval and insight synthesis.
        """
        logger.debug("Synthesizing response", extra={'request_id': request_id, 'user_query': user_query, 'data_sets': len(query_results)})

        # Format results for the prompt (can be complex depending on data structure)
        formatted_data = ""
        for i, result_set in enumerate(query_results):
            formatted_data += f"--- Data Set {i+1} (Query: {result_set['query'][:settings.SQL_QUERY_LOG_MAX_LENGTH]}...)\n"
            if result_set['results']:
                # Simple representation of results (e.g., first few rows or summary)
                # For production, consider a more robust data-to-text approach
                formatted_data += str(result_set['results'])[:settings.LLM_LOG_CONTENT_MAX_LENGTH * 2] # Limit data sent to LLM
            else:
                formatted_data += "No results.\n"
            formatted_data += "\n"

        # Determine which template to use (assuming intent is implicitly handled by orchestrator calling this)
        # A more robust way would be to pass intent explicitly
        # For now, let's assume if query_results has multiple sets or is for insights, use insight template
        if len(query_results) > 1 or (query_results and "insight" in user_query.lower()): # Simple heuristic
             prompt = self.insight_prompt_template.format(query=user_query, data=formatted_data)
             prompt_type = "response_synthesis_insight"
        else:
             prompt = self.retrieval_prompt_template.format(query=user_query, data=formatted_data)
             prompt_type = "response_synthesis_retrieval"


        try:
            llm_response = await self.llm_service.get_completion(prompt, prompt_type=prompt_type, request_id=request_id)

            logger.debug("Response synthesis complete", extra={'request_id': request_id})
            return llm_response.strip()

        except Exception as e:
            logger.error("Error during response synthesis", extra={'request_id': request_id, 'user_query': user_query, 'error': str(e)}, exc_info=True)
            # Fallback response
            return "I have retrieved the data, but I encountered an issue while formulating the response."

    async def check_insight_completeness(self, user_query: str, query_results: list, request_id: str = None) -> bool:
        """
        Uses LLM to check if collected data is sufficient for a complete insight.
        Returns True if complete, False otherwise.
        """
        logger.debug("Checking insight completeness", extra={'request_id': request_id, 'user_query': user_query, 'data_sets': len(query_results)})

        formatted_data = ""
        for i, result_set in enumerate(query_results):
            formatted_data += f"--- Data Set {i+1} (Query: {result_set['query'][:settings.SQL_QUERY_LOG_MAX_LENGTH]}...)\n"
            if result_set['results']:
                formatted_data += str(result_set['results'])[:settings.LLM_LOG_CONTENT_MAX_LENGTH * 2]
            else:
                formatted_data += "No results.\n"
            formatted_data += "\n"


        prompt = self.completeness_check_template.format(query=user_query, data=formatted_data)

        try:
            llm_response = await self.llm_service.get_completion(prompt, prompt_type="insight_completeness_check", request_id=request_id)

            # Simple parsing: expect "YES" or "NO" at the start
            response_upper = llm_response.strip().upper()

            is_complete = response_upper.startswith("YES")

            logger.debug(f"Insight completeness check result: {is_complete}", extra={'request_id': request_id, 'is_complete': is_complete})
            return is_complete

        except Exception as e:
            logger.error("Error during insight completeness check", extra={'request_id': request_id, 'user_query': user_query, 'error': str(e)}, exc_info=True)
            # Default to False (need more data) or True (stop to avoid infinite loop)?
            # Let's default to True to prevent infinite loops in case of LLM error
            return True