import logging
from fastapi import APIRouter, Request
from models.query_models import QueryRequest, QueryResponse
from core.orchestrator import QueryOrchestrator # Assuming orchestrator is in core

logger = logging.getLogger(__name__)

router = APIRouter()

# Assuming QueryOrchestrator is initialized elsewhere or is a class
# For simplicity in this example, let's assume it's a class that can be instantiated or is a singleton
# A better approach might be dependency injection in FastAPI
orchestrator = QueryOrchestrator()

@router.post("/query", response_model=QueryResponse)
async def process_user_query(request: Request, query_request: QueryRequest):
    """
    Processes a natural language query from the user.
    """
    user_query = query_request.query
    request_id = str(id(request)) # Simple request ID for logging correlation

    logger.info("Received incoming query", extra={'request_id': request_id, 'user_query': user_query})

    try:
        # Delegate processing to the orchestrator
        response_text = await orchestrator.process_query(user_query, request_id)

        logger.info("Finished processing query", extra={'request_id': request_id, 'status': 'success'})
        return QueryResponse(response=response_text)

    except Exception as e:
        logger.error("Error processing query", extra={'request_id': request_id, 'user_query': user_query, 'error': str(e)}, exc_info=True)
        # Return a generic error response to the user
        return QueryResponse(response=f"An error occurred while processing your request: {e}") # Or a more user-friendly message