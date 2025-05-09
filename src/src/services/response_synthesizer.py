import logging
from typing import Any, Dict, List

# Assuming LLMInteractionService is in core
from core.llm_interaction_service import LLMInteractionService
from core.config import settings # Assuming settings is needed for prompt file path

logger = logging.getLogger(__name__)

class ResponseSynthesisModule:
    """
    Module responsible for synthesizing a natural language response
    from the original user query and the database query results.
    """

    def __init__(self, llm_service: LLMInteractionService):
        """
        Initializes the ResponseSynthesisModule.

        Args:
            llm_service: An instance of LLMInteractionService.
        """
        self.llm_service = llm_service
        self.retrieval_prompt_template_path = "src/prompts/response_synthesis_retrieval.txt"
        logger.info("ResponseSynthesisModule initialized.")

    def _load_prompt_template(self, template_path: str) -> str:
        """Loads a prompt template from a file."""
        try:
            with open(template_path, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            logger.error(f"Prompt template file not found: {template_path}")
            raise
        except Exception as e:
            logger.error(f"Error loading prompt template {template_path}: {e}")
            raise

    def _format_query_results_for_llm(self, results: List[Dict[str, Any]]) -> str:
        """
        Formats query results into a string representation suitable for the LLM.
        This is a basic text table format. More sophisticated formatting
        might be needed for complex data structures.

        Args:
            results: A list of dictionaries, where each dictionary is a row.

        Returns:
            A string representation of the results.
        """
        if not results:
            return "No data returned."

        # Get headers from the first row keys
        headers = results[0].keys()
        header_line = "| " + " | ".join(headers) + " |"
        separator_line = "|-" + "-|-".join(["-" * len(str(h)) for h in headers]) + "-|" # Basic separator

        # Format rows
        data_lines = []
        for row in results:
            row_data = [str(row.get(header, '')) for header in headers]
            data_lines.append("| " + " | ".join(row_data) + " |")

        formatted_output = "\n".join([header_line, separator_line] + data_lines)

        # Add a note about potential formatting needs later (handled by I3.T5)
        formatted_output += "\n\nNOTE: The raw data is provided above. Specific formatting (e.g., currency, counts) will be applied to the final user-facing response by a separate module."


        return formatted_output

    def synthesize_response(self, original_query: str, query_results: List[Dict[str, Any]]) -> str:
        """
        Synthesizes a natural language response based on the original query
        and the provided query results using the LLM.

        Args:
            original_query: The user's original natural language query.
            query_results: The data fetched from the database, as a list of dicts.

        Returns:
            A natural language string response.

        Raises:
            Exception: If LLM interaction fails or prompt template cannot be loaded.
        """
        logger.info(f"Synthesizing response for query: {original_query[:100]}...")
        logger.debug(f"Query results received: {query_results}")

        try:
            # Load the prompt template
            prompt_template = self._load_prompt_template(self.retrieval_prompt_template_path)

            # Format the query results for inclusion in the prompt
            formatted_results = self._format_query_results_for_llm(query_results)
            logger.debug(f"Formatted results for LLM:\n{formatted_results}")

            # Construct the full prompt
            # Assuming placeholders like {original_query} and {query_results} in the template
            prompt = prompt_template.format(
                original_query=original_query,
                query_results=formatted_results
            )
            logger.debug(f"Full prompt sent to LLM:\n{prompt[:500]}...")


            # Get completion from the LLM
            # Use a slightly lower temperature for more factual/summarizing responses
            # Pass any relevant kwargs, e.g., max_tokens if needed
            response = self.llm_service.get_completion(
                prompt=prompt,
                temperature=settings.LLM_TEMPERATURE * 0.8 # Slightly cooler than default
            )

            logger.info("Successfully synthesized response using LLM.")
            return response

        except Exception as e:
            logger.error(f"Error during response synthesis: {e}")
            # Re-raise the exception to be handled by the orchestrator
            raise

# Example Usage (for testing the module in isolation if needed)
if __name__ == "__main__":
    # This block requires a running LLMInteractionService and potentially a mock DB result
    # For a simple test, you can mock the LLMInteractionService
    logging.basicConfig(level=logging.DEBUG)
    print("Testing ResponseSynthesisModule (requires LLMInteractionService and prompt file)...")

    # Mock LLMInteractionService for testing
    class MockLLMInteractionService:
        def get_completion(self, prompt: str, **kwargs: Any) -> str:
            print(f"\n--- Mock LLM Call ---")
            print(f"Prompt: {prompt[:500]}...")
            print(f"Kwargs: {kwargs}")
            print(f"--- End Mock LLM Call ---")
            # Simulate a response based on prompt content
            if "sales data" in prompt:
                return "Based on the sales data provided, the total revenue is 15000 SAR and the total number of items sold is 500."
            elif "user accounts" in prompt:
                 return "Here is a summary of the user accounts: John Doe, Jane Smith, etc."
            else:
                return "Mocked response based on provided data."

    # Create a dummy prompt file for testing
    dummy_prompt_content = """
You are an AI assistant tasked with summarizing database query results to answer a user's question.
The user's original question was: "{original_query}"
The data retrieved from the database is provided below:
{query_results}

Please synthesize a concise and helpful natural language response based on the original question and the data.
Focus on directly answering the user's question using the provided data.
If no data was returned, state that the query returned no results.
"""
    dummy_prompt_path = "src/prompts/response_synthesis_retrieval.txt"
    try:
        # Ensure the directory exists
        import os
        os.makedirs(os.path.dirname(dummy_prompt_path), exist_ok=True)
        with open(dummy_prompt_path, "w", encoding="utf-8") as f:
            f.write(dummy_prompt_content)
        print(f"Created dummy prompt file: {dummy_prompt_path}")

        # Instantiate the module with the mock service
        mock_llm_service = MockLLMInteractionService()
        response_synthesizer = ResponseSynthesisModule(llm_service=mock_llm_service)

        # Define some mock query results (list of dicts)
        mock_results_sales = [
            {"product": "Laptop", "quantity_sold": 100, "revenue": 10000.00},
            {"product": "Mouse", "quantity_sold": 400, "revenue": 5000.00},
        ]
        mock_query_sales = "What were the total sales for laptops and mice?"

        mock_results_users = [
            {"user_id": 1, "username": "john_doe"},
            {"user_id": 2, "username": "jane_smith"},
            {"user_id": 3, "username": "peter_jones"},
        ]
        mock_query_users = "List the usernames of all users."

        mock_results_empty = []
        mock_query_empty = "Show me data for non-existent category."


        # Test synthesis with mock data
        print("\n--- Test Case 1: Sales Data ---")
        synthesized_response_sales = response_synthesizer.synthesize_response(
            original_query=mock_query_sales,
            query_results=mock_results_sales
        )
        print(f"\nSynthesized Response (Sales): {synthesized_response_sales}")

        print("\n--- Test Case 2: User Data ---")
        synthesized_response_users = response_synthesizer.synthesize_response(
            original_query=mock_query_users,
            query_results=mock_results_users
        )
        print(f"\nSynthesized Response (Users): {synthesized_response_users}")

        print("\n--- Test Case 3: Empty Data ---")
        synthesized_response_empty = response_synthesizer.synthesize_response(
            original_query=mock_query_empty,
            query_results=mock_results_empty
        )
        print(f"\nSynthesized Response (Empty): {synthesized_response_empty}")


    except Exception as e:
        print(f"\nAn error occurred during the test: {e}")
    finally:
         # Clean up the dummy prompt file
        if os.path.exists(dummy_prompt_path):
             os.remove(dummy_prompt_path)
             print(f"\nCleaned up dummy prompt file: {dummy_prompt_path}")