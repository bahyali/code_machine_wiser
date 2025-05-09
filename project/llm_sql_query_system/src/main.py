from fastapi import FastAPI

app = FastAPI(
    title="LLM-Powered SQL Query System",
    description="API for interacting with a PostgreSQL database using natural language.",
    version="0.1.0",
)

@app.get("/")
async def read_root():
    """Basic health check / hello world endpoint."""
    return {"message": "LLM-Powered SQL Query System is running!"}

# Include routers from api/v1 (will be created in later tasks)
# from .api.v1 import query_router
# app.include_router(query_router.router, prefix="/api/v1", tags=["query"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)