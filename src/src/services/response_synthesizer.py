import logging
from typing import Any, Dict, List, Union

# Assuming LLMInteractionService is in core
from core.llm_interaction_service import LLMInteractionService
from core.config import settings # Assuming settings is needed for prompt file path

logger = logging.getLogger(__name__)

class ResponseSynthesisModule:
    """
    Module responsible for synthesizing a natural language response
    from the original user query and the database query results.
    Handles both simple data retrieval and complex insight generation.
    """

    def __init__(self, llm_service: LLMInteractionService):
        """
        Initializes the ResponseSynthesisModule.

        Args:
            llm_service: An instance of LLMInteractionService.
        """
        self.llm_service = llm_service
        # Prompt template for simple data retrieval
        self.retrieval_prompt_template_path = "src/prompts/response_synthesis_retrieval.txt"
        # Prompt template for insight generation
        self.insight_prompt_template_path = "src/prompts/response_synthesis_insight.txt"
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
        Formats query results (a single list of dicts) into a string representation
        suitable for the LLM. This is a basic text table format.

        Args:
            results: A list of dictionaries, where each dictionary is a row.

        Returns:
            A string representation of the results.
        """
        if not results:
            return "No data returned."

        # Get headers from the first row keys
        headers = list(results[0].keys()) # Use list() to avoid issues if keys() is not subscriptable
        header_line = "| " + " | ".join(headers) + " |"
        # Basic separator, adjust width based on header length
        separator_parts = []
        for header in headers:
             # Calculate max width for column: header length or max data length in that column
             max_col_width = len(header)
             try:
                 max_data_width = max(len(str(row.get(header, ''))) for row in results)
                 max_col_width = max(max_col_width, max_data_width)
             except Exception:
                 # Handle cases where data might be complex or missing keys
                 pass # Keep header width as minimum

             separator_parts.append("-" * max_col_width)

        separator_line = "|-" + "-|-".join(separator_parts) + "-|"


        # Format rows
        data_lines = []
        for row in results:
            row_data = []
            for header in headers:
                 # Pad data to match separator width for alignment (basic attempt)
                 col_data = str(row.get(header, ''))
                 # Find the corresponding separator part width
                 try:
                     header_index = headers.index(header)
                     col_width = len(separator_parts[header_index])
                     row_data.append(col_data.ljust(col_width)) # Left justify
                 except (ValueError, IndexError):
                     row_data.append(col_data) # Fallback if header not found or index error

            data_lines.append("| " + " | ".join(row_data) + " |")

        formatted_output = "\\n".join([header_line, separator_line] + data_lines)

        # Add a note about potential formatting needs later (handled by I3.T5)
        # This note is primarily for the LLM to understand its role vs the formatter module
        formatted_output += "\\n\\nNOTE: The raw data is provided above. Specific presentation formatting (e.g., currency, counts) will be applied to the final user-facing response by a separate module, but your synthesis should reflect the correct data types."


        return formatted_output

    def _format_insight_data_for_llm(self, compiled_data: Dict[str, List[Dict[str, Any]]]) -> str:
        """
        Formats data from potentially multiple query results for insight synthesis.
        Labels each dataset clearly.

        Args:
            compiled_data: A dictionary where keys are labels for datasets
                           (e.g., "Sales by Product") and values are lists of dicts
                           representing the query results for that dataset.

        Returns:
            A string representation of all compiled data, labeled by dataset.
        """
        if not compiled_data:
            return "No data was compiled for insight generation."

        formatted_parts = []
        for label, results in compiled_data.items():
            formatted_parts.append(f"--- Dataset: {label} ---")
            formatted_parts.append(self._format_query_results_for_llm(results)) # Reuse single result formatter
            formatted_parts.append("") # Add a newline between datasets

        return "\\n".join(formatted_parts)

    def synthesize_response(self, original_query: str, query_results: List[Dict[str, Any]]) -> str:
        """
        Synthesizes a natural language response based on the original query
        and the provided query results using the LLM. This method is typically
        used for simple data retrieval intents.

        Args:
            original_query: The user's original natural language query.
            query_results: The data fetched from the database, as a list of dicts.

        Returns:
            A natural language string response.

        Raises:
            Exception: If LLM interaction fails or prompt template cannot be loaded.
        """
        logger.info(f"Synthesizing retrieval response for query: {original_query[:100]}...")
        logger.debug(f"Query results received: {query_results}")

        try:
            # Load the prompt template
            prompt_template = self._load_prompt_template(self.retrieval_prompt_template_path)

            # Format the query results for inclusion in the prompt
            formatted_results = self._format_query_results_for_llm(query_results)
            logger.debug(f"Formatted results for LLM:\\n{formatted_results}")

            # Construct the full prompt
            # Assuming placeholders like {original_query} and {query_results} in the template
            prompt = prompt_template.format(
                original_query=original_query,
                query_results=formatted_results
            )
            logger.debug(f"Full prompt sent to LLM:\\n{prompt[:500]}...")


            # Get completion from the LLM
            # Use a slightly lower temperature for more factual/summarizing responses
            # Pass any relevant kwargs, e.g., max_tokens if needed
            response = self.llm_service.get_completion(\
                prompt=prompt,\
                temperature=settings.LLM_TEMPERATURE * 0.8 # Slightly cooler than default\
            )

            logger.info("Successfully synthesized retrieval response using LLM.")
            return response

        except Exception as e:
            logger.error(f"Error during retrieval response synthesis: {e}")
            # Re-raise the exception to be handled by the orchestrator
            raise

    def synthesize_insight(self, original_query: str, compiled_data: Dict[str, List[Dict[str, Any]]]) -> str:
        """
        Synthesizes a comprehensive natural language insight based on the original query
        and data compiled from potentially multiple query results using the LLM.
        This method is typically used for insight generation intents.

        Args:
            original_query: The user's original natural language query.
            compiled_data: A dictionary where keys are labels for datasets
                           (e.g., "Sales by Product") and values are lists of dicts
                           representing the query results for that dataset.

        Returns:
            A natural language string representing the synthesized insight.

        Raises:
            Exception: If LLM interaction fails or prompt template cannot be loaded.
        """
        logger.info(f"Synthesizing insight for query: {original_query[:100]}...")
        logger.debug(f"Compiled data received for insight: {compiled_data}")

        try:
            # Load the insight prompt template
            prompt_template = self._load_prompt_template(self.insight_prompt_template_path)

            # Format the compiled data for inclusion in the prompt
            formatted_data = self._format_insight_data_for_llm(compiled_data)
            logger.debug(f"Formatted insight data for LLM:\\n{formatted_data}")

            # Construct the full prompt
            # Assuming placeholders like {original_query} and {compiled_data} in the template
            prompt = prompt_template.format(
                original_query=original_query,
                compiled_data=formatted_data
            )
            logger.debug(f"Full insight prompt sent to LLM:\\n{prompt[:500]}...")

            # Get completion from the LLM
            # Use a slightly lower temperature for more analytical/synthesizing responses
            response = self.llm_service.get_completion(
                prompt=prompt,
                temperature=settings.LLM_TEMPERATURE * 0.7 # Slightly cooler for analysis
            )

            logger.info("Successfully synthesized insight using LLM.")
            return response

        except Exception as e:
            logger.error(f"Error during insight synthesis: {e}")
            # Re-raise the exception to be handled by the orchestrator
            raise


# Example Usage (for testing the module in isolation if needed)
if __name__ == "__main__":
    # This block requires a running LLMInteractionService and potentially mock DB results
    # For a simple test, you can mock the LLMInteractionService
    import os
    import sys
    import inspect

    # Add the project root to the sys.path to allow importing core.config
    currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
    parentdir = os.path.dirname(currentdir)
    grandparentdir = os.path.dirname(parentdir)
    sys.path.insert(0, grandparentdir)


    logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)
    print("Testing ResponseSynthesisModule (requires LLMInteractionService and prompt files)...")

    # Mock LLMInteractionService for testing
    class MockLLMInteractionService:
        def get_completion(self, prompt: str, **kwargs: Any) -> str:
            print(f"\\n--- Mock LLM Call ---")
            print(f"Prompt: {prompt[:800]}...") # Print a bit more of the prompt
            print(f"Kwargs: {kwargs}")
            print(f"--- End Mock LLM Call ---")
            # Simulate a response based on prompt content
            if "Synthesize the insight now:" in prompt:
                 return "Based on the provided data, here is a synthesized insight..."
            elif "Synthesize a concise and helpful natural language response" in prompt:
                 return "Based on the sales data provided, the total revenue is 15000 SAR and the total number of items sold is 500."
            else:
                return "Mocked response based on provided data."

    # Mock Settings for testing
    class MockSettings:
        LLM_TEMPERATURE: float = 0.5
        # Add other required settings if BaseSettings validation was strict
        OPENAI_API_KEY: str = "sk-mock-key-1234"
        LLM_MODEL: str = "gpt-4o-mini"
        LLM_TIMEOUT_SECONDS: int = 30
        LLM_MAX_RETRIES: int = 1
        APP_NAME: str = "Mock App"
        APP_VERSION: str = "0.0.1"
        ENVIRONMENT: str = "test"
        API_V1_STR: str = "/api/v1"
        HOST: str = "0.0.0.0"
        PORT: int = 8000
        DATABASE_URL: Union[str, None] = None
        DB_HOST: Union[str, None] = None
        DB_PORT: Union[int, None] = 5432
        DB_NAME: Union[str, None] = None
        DB_USER: Union[str, None] = None
        DB_PASSWORD: Union[str, None] = None
        SQL_TIMEOUT_SECONDS: int = 30
        SQL_MAX_ROWS_RETURNED: int = 1000
        SQL_ERROR_CORRECTION_MAX_ATTEMPTS: int = 2
        _CONFIG_FILE_PATH: str = "config.yaml"


    # Create dummy prompt files for testing
    dummy_retrieval_prompt_content = """
You are an AI assistant tasked with summarizing database query results to answer a user's question.
The user's original question was: "{original_query}"
The data retrieved from the database is provided below:
{query_results}

Please synthesize a concise and helpful natural language response based on the original question and the data.
Focus on directly answering the user's question using the provided data.
If no data was returned, state that the query returned no results.
"""
    dummy_insight_prompt_content = """
You are an expert data analyst and business consultant. Your task is to synthesize a comprehensive insight based on the user's original question and the data provided from one or more database queries.

The user's original question was: "{original_query}"

You have been provided with the following data, compiled from potentially multiple queries. Each dataset is labeled to indicate its source or purpose. Analyze this data to identify key trends, patterns, correlations, or summaries that directly address the user's question.

--- Data Provided ---
{compiled_data}
--- End Data Provided ---

Based on the original question and the compiled data, provide a clear, concise, and insightful response.
Your response should:
1. Directly address the user's original question.
2. Synthesize information across the different datasets if applicable.
3. Highlight key findings, trends, or summaries.
4. Avoid simply listing the raw data.
5. Present numerical data clearly, ensuring counts are whole numbers and monetary values (like revenue) are formatted in SAR currency (e.g., "1,234.50 SAR"). Note that raw data formatting might not be final; focus on presenting the *insight* clearly.
6. If the data is insufficient or contradictory, state this clearly.
7. If no data was returned for a specific dataset, mention that dataset yielded no results but still attempt to synthesize insights from any data that *was* returned.

Synthesize the insight now:
"""

    dummy_retrieval_prompt_path = "src/prompts/response_synthesis_retrieval.txt"
    dummy_insight_prompt_path = "src/prompts/response_synthesis_insight.txt"

    try:
        # Ensure the directory exists
        os.makedirs(os.path.dirname(dummy_retrieval_prompt_path), exist_ok=True)
        os.makedirs(os.path.dirname(dummy_insight_prompt_path), exist_ok=True)

        with open(dummy_retrieval_prompt_path, "w", encoding="utf-8") as f:
            f.write(dummy_retrieval_prompt_content)
        print(f"Created dummy retrieval prompt file: {dummy_retrieval_prompt_path}")

        with open(dummy_insight_prompt_path, "w", encoding="utf-8") as f:
            f.write(dummy_insight_prompt_content)
        print(f"Created dummy insight prompt file: {dummy_insight_prompt_path}")

        # Use mock settings
        settings = MockSettings()

        # Instantiate the module with the mock service
        mock_llm_service = MockLLMInteractionService()
        response_synthesizer = ResponseSynthesisModule(llm_service=mock_llm_service)

        # --- Test Case 1: Simple Data Retrieval ---
        print("\\n--- Test Case 1: Simple Data Retrieval ---")
        mock_results_sales = [\
            {"product": "Laptop", "quantity_sold": 100, "revenue": 10000.00},\
            {"product": "Mouse", "quantity_sold": 400, "revenue": 5000.00},\
        ]
        mock_query_sales = "What were the total sales for laptops and mice?"

        synthesized_response_sales = response_synthesizer.synthesize_response(\
            original_query=mock_query_sales,\
            query_results=mock_results_sales\
        )
        print(f"\\nSynthesized Response (Sales): {synthesized_response_sales}")

        # --- Test Case 2: Insight Generation with Multiple Datasets ---
        print("\\n--- Test Case 2: Insight Generation with Multiple Datasets ---")
        mock_compiled_data_insight = {
            "Sales Summary by Product": [
                {"product": "Laptop", "total_revenue": 10000.00, "units_sold": 100},
                {"product": "Mouse", "total_revenue": 5000.00, "units_sold": 400},
                {"product": "Keyboard", "total_revenue": 3000.00, "units_sold": 150},
            ],
            "Customer Demographics (Top 3 Cities)": [
                {"city": "Riyadh", "customer_count": 500, "total_spend": 12000.00},
                {"city": "Jeddah", "customer_count": 300, "total_spend": 8000.00},
                {"city": "Dammam", "customer_count": 200, "total_spend": 5000.00},
            ],
             "Monthly Sales Trend (Last 3 Months)": [
                {"month": "2023-08", "monthly_revenue": 7000.00},
                {"month": "2023-09", "monthly_revenue": 9000.00},
                {"month": "2023-10", "monthly_revenue": 12000.00},
            ]
        }
        mock_query_insight = "Provide insights into recent sales performance and customer distribution."

        synthesized_insight = response_synthesizer.synthesize_insight(
            original_query=mock_query_insight,
            compiled_data=mock_compiled_data_insight
        )
        print(f"\\nSynthesized Insight: {synthesized_insight}")

        # --- Test Case 3: Empty Data Retrieval ---
        print("\\n--- Test Case 3: Empty Data Retrieval ---")
        mock_results_empty = []
        mock_query_empty = "Show me data for non-existent category."

        synthesized_response_empty = response_synthesizer.synthesize_response(
            original_query=mock_query_empty,
            query_results=mock_results_empty
        )
        print(f"\\nSynthesized Response (Empty): {synthesized_response_empty}")

        # --- Test Case 4: Insight Generation with Partial/Empty Data ---
        print("\\n--- Test Case 4: Insight Generation with Partial/Empty Data ---")
        mock_compiled_data_partial = {
            "Sales Summary by Product": [
                {"product": "Laptop", "total_revenue": 10000.00, "units_sold": 100},
                {"product": "Mouse", "total_revenue": 5000.00, "units_sold": 400},
            ],
            "Customer Demographics (Top 3 Cities)": [], # Empty dataset
             "Monthly Sales Trend (Last 3 Months)": [
                {"month": "2023-08", "monthly_revenue": 7000.00},
                {"month": "2023-09", "monthly_revenue": 9000.00},
            ]
        }
        mock_query_partial_insight = "Provide insights into recent sales performance and customer distribution."

        synthesized_partial_insight = response_synthesizer.synthesize_insight(
            original_query=mock_query_partial_insight,
            compiled_data=mock_compiled_data_partial
        )
        print(f"\\nSynthesized Partial Insight: {synthesized_partial_insight}")


    except Exception as e:
        print(f"\\nAn error occurred during the test: {e}")
        logging.exception("An error occurred during test execution")
    finally:
         # Clean up the dummy prompt files
        if os.path.exists(dummy_retrieval_prompt_path):
             os.remove(dummy_retrieval_prompt_path)
             print(f"\\nCleaned up dummy retrieval prompt file: {dummy_retrieval_prompt_path}")
        if os.path.exists(dummy_insight_prompt_path):
             os.remove(dummy_insight_prompt_path)
             print(f"Cleaned up dummy insight prompt file: {dummy_insight_prompt_path}")