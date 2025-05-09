from pydantic import BaseModel

class QueryRequest(BaseModel):
    """
    Represents the request body for a natural language query.
    """
    query: str
    """The natural language query string provided by the user."""

class QueryResponse(BaseModel):
    """
    Represents the response body containing the system's answer.
    """
    response: str
    """The system's natural language response to the query."""