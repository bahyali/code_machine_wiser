# Pydantic models for API requests/responses - will be defined in I1.T4
from pydantic import BaseModel

class QueryRequest(BaseModel):
    """Request model for the /query endpoint."""
    query: str

class QueryResponse(BaseModel):
    """Response model for the /query endpoint."""
    response: str
    # Potentially add other fields later, e.g., data, sql_executed, etc.