# Main FastAPI application entry point.

from fastapi import FastAPI

# Import routers
from api.v1 import query_router

# Create FastAPI app instance
app = FastAPI(
    title="LLM-Powered Q&A System API",
    description="API for interacting with the LLM-Powered Q&A System using natural language queries.",
    version="1.0.0",
    # Add OpenAPI tags or other metadata if needed
)

# Include routers
app.include_router(query_router.router, prefix="/api/v1", tags=["query"])

@app.get("/")
async def read_root():
    """
    Root endpoint for basic health check.
    """
    return {"message": "LLM-Powered Q&A System API is running"}

# Example of how to run the app (for development)
# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=8000)