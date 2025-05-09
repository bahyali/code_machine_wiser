# API router for the /api/v1/query endpoint.

from fastapi import APIRouter
from models.query_models import QueryRequest, QueryResponse
from core.orchestrator import QueryOrchestrator

router = APIRouter()

# Instantiate the orchestrator shell
# In a real application, this might be managed via dependency injection
orchestrator = QueryOrchestrator()

@router.post("/query", response_model=QueryResponse)
async def handle_query(query_request: QueryRequest):
    """
    Handles incoming natural language queries.
    Passes the query to the Query Orchestrator for processing.
    """
    print(f"API received query: {query_request.query}")
    response = orchestrator.process_query(query_request)
    return response