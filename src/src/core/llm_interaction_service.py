import logging
from openai import OpenAI
from openai import APIError, APIConnectionError, RateLimitError
from core.config import settings
import time

logger = logging.getLogger(__name__)

class LLMInteractionService:
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.LLM_MODEL

    async def get_completion(self, prompt: str, prompt_type: str = "general", request_id: str = None) -> str:
        """
        Sends a prompt to the LLM and returns the completion.
        Logs prompt/response metadata.
        """
        log_extra = {'request_id': request_id, 'prompt_type': prompt_type, 'model': self.model}
        if settings.LLM_LOG_PROMPT_RESPONSE_CONTENT:
             log_extra['prompt_truncated'] = prompt[:settings.LLM_LOG_CONTENT_MAX_LENGTH]

        logger.info("Calling LLM API", extra=log_extra)
        start_time = time.time()

        try:
            # Assuming a simple text completion or chat completion call
            # For chat models like gpt-4o, use chat.completions.create
            messages = [{"role": "user", "content": prompt}] # Basic message structure

            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                # Add other parameters as needed (temperature, max_tokens, etc.)
            )

            end_time = time.time()
            duration = end_time - start_time

            completion_text = response.choices[0].message.content.strip()
            usage = response.usage # Contains token counts

            log_extra = {
                'request_id': request_id,
                'prompt_type': prompt_type,
                'model': self.model,
                'duration_seconds': duration,
                'prompt_tokens': usage.prompt_tokens,
                'completion_tokens': usage.completion_tokens,
                'total_tokens': usage.total_tokens,
            }
            if settings.LLM_LOG_PROMPT_RESPONSE_CONTENT:
                 log_extra['response_truncated'] = completion_text[:settings.LLM_LOG_CONTENT_MAX_LENGTH]


            logger.info("LLM API call successful", extra=log_extra)

            return completion_text

        except RateLimitError as e:
            logger.error("LLM API Rate limit exceeded", extra={'request_id': request_id, 'prompt_type': prompt_type, 'error': str(e)}, exc_info=True)
            raise # Re-raise the exception for handling upstream
        except APIConnectionError as e:
            logger.error("LLM API Connection Error", extra={'request_id': request_id, 'prompt_type': prompt_type, 'error': str(e)}, exc_info=True)
            raise
        except APIError as e:
            logger.error("LLM API Error", extra={'request_id': request_id, 'prompt_type': prompt_type, 'status_code': e.status_code, 'error': str(e)}, exc_info=True)
            raise
        except Exception as e:
            logger.error("An unexpected error occurred during LLM API call", extra={'request_id': request_id, 'prompt_type': prompt_type, 'error': str(e)}, exc_info=True)
            raise