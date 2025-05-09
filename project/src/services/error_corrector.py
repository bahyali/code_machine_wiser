import logging
from core.llm_interaction_service import LLMInteractionService
from core.config import settings

logger = logging.getLogger(__name__)

class SQLErrorCorrectionModule:
    def __init__(self):
        self.llm_service = LLMInteractionService() # Assuming LLMInteractionService is initialized here or injected
        # Load prompt template for error correction
        try:
            with open("src/prompts/sql_error_correction.txt", "r") as f:
                self.prompt_template = f.read()
        except FileNotFoundError:
            logger.error("SQL error correction prompt template not found.")
            self.prompt_template = "The following SQL query failed with error: {error}\n\nOriginal Query: {query}\n\nSuggest a corrected PostgreSQL SQL query. Respond only with the corrected SQL." # Fallback

    async def correct_sql_error(self, failed_query: str, error_message: str, request_id: str = None) -> str | None:
        """
        Uses LLM to attempt to correct a failed SQL query based on the error message.
        Returns the corrected query string or None if correction is not possible/successful.
        """
        logger.debug("Attempting SQL error correction", extra={'request_id': request_id, 'failed_query_truncated': failed_query[:settings.SQL_QUERY_LOG_MAX_LENGTH], 'error_message': error_message})

        prompt = self.prompt_template.format(query=failed_query, error=error_message)

        try:
            llm_response = await self.llm_service.get_completion(prompt, prompt_type="sql_correction", request_id=request_id)

            # Basic parsing: expect SQL query in the response
            corrected_sql = llm_response.strip()
            if corrected_sql.startswith("```sql") and corrected_sql.endswith("```"):
                 corrected_sql = corrected_sql[len("```sql"): -len("```")].strip()
            elif corrected_sql.startswith("```") and corrected_sql.endswith("```"): # Handle generic code block
                 corrected_sql = corrected_sql[len("```"): -len("```")].strip()

            # Simple check if LLM just repeated the error or gave non-SQL
            if corrected_sql and corrected_sql != failed_query and "error" not in corrected_sql.lower(): # Add more robust checks if needed
                 logger.info("LLM suggested corrected SQL", extra={'request_id': request_id, 'corrected_sql_truncated': corrected_sql[:settings.SQL_QUERY_LOG_MAX_LENGTH]})
                 return corrected_sql
            else:
                 logger.warning("LLM correction attempt did not yield a valid or different query", extra={'request_id': request_id, 'llm_response_truncated': llm_response[:settings.LLM_LOG_CONTENT_MAX_LENGTH]})
                 return None # Indicate correction failed

        except Exception as e:
            logger.error("Error during SQL error correction attempt", extra={'request_id': request_id, 'failed_query_truncated': failed_query[:settings.SQL_QUERY_LOG_MAX_LENGTH], 'error': str(e)}, exc_info=True)
            return None # Indicate correction failed