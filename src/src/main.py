import logging
from fastapi import FastAPI
from api.v1.query_router import router as query_router
from core.logging_config import configure_logging
from core.config import settings # Import settings if needed elsewhere

# Configure logging as early as possible
configure_logging()

logger = logging.getLogger(__name__)

app = FastAPI(
    title="LLM-Powered Q&A System",
    description="API for natural language interaction with PostgreSQL",
    version="1.0.0",
)

@app.on_event("startup")
async def startup_event():
    logger.info("Application startup initiated")
    # Add any startup logic here (e.g., DB connection pool init)
    # Note: DB connection for user's DB is handled per query or by schema manager
    pass

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Application shutdown initiated")
    # Add any shutdown logic here (e.g., close DB connection pool)
    pass

app.include_router(query_router, prefix="/api/v1")

@app.get("/")
async def read_root():
    logger.debug("Root endpoint accessed")
    return {"message": "LLM-Powered Q&A System API is running"}

# Example of logging an error
@app.get("/test-error")
async def test_error():
    try:
        1 / 0
    except Exception as e:
        logger.error("An intentional test error occurred", exc_info=True)
        return {"message": "Test error logged"}