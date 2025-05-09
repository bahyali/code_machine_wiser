import logging
from services.intent_analyzer import IntentAnalysisModule # Assuming services are in services dir
from services.chitchat_handler import ChitChatHandlerModule
from services.schema_manager import DBSchemaManager
from services.sql_generator import SQLGenerationModule
from services.sql_executor import SQLExecutionModule
from services.error_corrector import SQLErrorCorrectionModule
from services.response_synthesizer import ResponseSynthesisModule
from services.formatter_validator import DataFormatterValidatorModule
from core.config import settings

logger = logging.getLogger(__name__)

class QueryOrchestrator:
    def __init__(self):
        # Initialize modules (dependency injection framework could manage this)
        self.intent_analyzer = IntentAnalysisModule()
        self.chitchat_handler = ChitChatHandlerModule()
        self.schema_manager = DBSchemaManager()
        self.sql_generator = SQLGenerationModule()
        self.sql_executor = SQLExecutionModule()
        self.error_corrector = SQLErrorCorrectionModule()
        self.response_synthesizer = ResponseSynthesisModule()
        self.formatter_validator = DataFormatterValidatorModule()

    async def process_query(self, user_query: str, request_id: str):
        logger.info("Orchestrator starting query processing", extra={'request_id': request_id, 'user_query': user_query})

        # 1. Intent Analysis
        intent = await self.intent_analyzer.analyze_intent(user_query, request_id)
        logger.info("Intent classified", extra={'request_id': request_id, 'intent': intent})

        if intent == "CHITCHAT":
            # 2. Handle Chit-Chat
            response = await self.chitchat_handler.handle_chit_chat(user_query, request_id)
            logger.info("Handled as chit-chat", extra={'request_id': request_id})
            return response

        elif intent == "DATA_RETRIEVAL" or intent == "INSIGHTS":
            # 3. Handle Data Retrieval or Insights (requires DB interaction)
            schema = await self.schema_manager.get_schema(request_id) # Fetch schema
            logger.debug("Fetched DB schema", extra={'request_id': request_id, 'schema_summary': f"Tables: {len(schema.get('tables', []))}"}) # Log summary

            sql_queries = []
            query_results = []
            current_query_context = {"user_query": user_query, "schema": schema, "previous_results": []}

            # Initial SQL Generation
            sql_query = await self.sql_generator.generate_sql(intent, current_query_context, request_id)
            sql_queries.append(sql_query)
            logger.info("Generated initial SQL query", extra={'request_id': request_id, 'intent': intent, 'sql_query_truncated': sql_query[:settings.SQL_QUERY_LOG_MAX_LENGTH]})

            success = False
            attempts = 0
            max_attempts = settings.SQL_MAX_RETRY_ATTEMPTS # Use config for retry attempts

            while attempts < max_attempts:
                attempts += 1
                logger.debug(f"Attempting SQL execution (Attempt {attempts}/{max_attempts})", extra={'request_id': request_id, 'sql_query_truncated': sql_query[:settings.SQL_QUERY_LOG_MAX_LENGTH]})
                try:
                    results = await self.sql_executor.execute_sql(sql_query, request_id)
                    query_results.append({"query": sql_query, "results": results})
                    logger.info("SQL execution successful", extra={'request_id': request_id, 'attempt': attempts, 'rows_returned': len(results) if results else 0})
                    success = True

                    if intent == "INSIGHTS":
                        # For insights, decide if more queries are needed
                        more_queries_needed = await self.response_synthesizer.check_insight_completeness(user_query, query_results, request_id) # This might use LLM
                        if more_queries_needed:
                            logger.info("Insight incomplete, generating next query", extra={'request_id': request_id})
                            current_query_context["previous_results"] = query_results # Update context
                            sql_query = await self.sql_generator.generate_sql(intent, current_query_context, request_id)
                            sql_queries.append(sql_query)
                            logger.info("Generated next SQL query for insights", extra={'request_id': request_id, 'sql_query_truncated': sql_query[:settings.SQL_QUERY_LOG_MAX_LENGTH]})
                            # Continue loop for next query
                        else:
                            logger.info("Insight deemed complete", extra={'request_id': request_id})
                            break # Break loop if insight is complete
                    else: # DATA_RETRIEVAL is usually a single query
                         break # Break loop after successful execution

                except Exception as e:
                    logger.warning("SQL execution failed", extra={'request_id': request_id, 'attempt': attempts, 'error': str(e)})
                    if attempts < max_attempts:
                        logger.info("Attempting SQL correction", extra={'request_id': request_id, 'attempt': attempts})
                        corrected_sql = await self.error_corrector.correct_sql_error(sql_query, str(e), request_id)
                        if corrected_sql and corrected_sql != sql_query:
                            sql_query = corrected_sql # Use corrected query for next attempt
                            sql_queries.append(sql_query) # Log corrected query
                            logger.info("SQL correction successful, retrying with corrected query", extra={'request_id': request_id, 'corrected_sql_truncated': sql_query[:settings.SQL_QUERY_LOG_MAX_LENGTH]})
                        else:
                            logger.warning("SQL correction failed or returned same query", extra={'request_id': request_id, 'attempt': attempts})
                            # If correction fails, or it's the last attempt, break
                            break
                    else:
                        logger.error("Max SQL execution attempts reached", extra={'request_id': request_id, 'attempt': attempts, 'final_error': str(e)})
                        # Decide whether to proceed with partial data or fail
                        if intent == "INSIGHTS" and query_results:
                             logger.warning("Proceeding with partial data for insights after execution failures", extra={'request_id': request_id})
                             success = True # Treat as partial success for insights
                        else:
                            success = False # Mark as failure
                            break # Break loop after max attempts

            if not success and not (intent == "INSIGHTS" and query_results):
                 logger.error("Failed to retrieve data after all attempts", extra={'request_id': request_id})
                 # Handle complete failure - maybe return a specific error message
                 return "Could not retrieve the requested data due to database errors."

            # 4. Synthesize and Format Response
            logger.info("Synthesizing final response", extra={'request_id': request_id, 'data_points': len(query_results)})
            raw_response_text = await self.response_synthesizer.synthesize_response(user_query, query_results, request_id)

            # 5. Format and Validate Data in Response
            # This step might involve parsing the raw_response_text and applying formatting
            # Or the response_synthesizer might return structured data to be formatted
            # Assuming formatter_validator works on the final text or structured data before final text
            final_response = self.formatter_validator.format_and_validate(raw_response_text, query_results, request_id) # Pass results for context if needed

            logger.info("Response synthesis and formatting complete", extra={'request_id': request_id})
            return final_response

        else:
            # Handle unknown intent
            logger.warning("Unknown intent classified", extra={'request_id': request_id, 'intent': intent, 'user_query': user_query})
            return "I'm not sure how to handle that request."