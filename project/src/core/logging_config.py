import logging
import sys
from pythonjsonlogger import jsonlogger
from core.config import settings # Assuming config is in core

def configure_logging():
    """Configures the root logger with a JSON formatter."""
    root_logger = logging.getLogger()
    root_logger.setLevel(settings.LOG_LEVEL)

    # Prevent adding multiple handlers if called multiple times
    if not root_logger.handlers:
        if settings.LOG_FORMAT == "json":
            formatter = jsonlogger.JsonFormatter(
                fmt='%(asctime)s %(levelname)s %(name)s %(message)s %(pathname)s %(lineno)d',
                datefmt='%Y-%m-%dT%H:%M:%SZ'
            )
            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(formatter)
            root_logger.addHandler(handler)
        else: # Basic format
            logging.basicConfig(level=settings.LOG_LEVEL, stream=sys.stdout)

    # Optional: Configure loggers for specific libraries if needed
    # logging.getLogger("uvicorn").setLevel(logging.WARNING)
    # logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    # logging.getLogger("httpx").setLevel(logging.WARNING)
    # logging.getLogger("openai").setLevel(logging.WARNING) # Adjust based on desired verbosity

    root_logger.info("Logging configured", extra={'log_level': logging.getLevelName(settings.LOG_LEVEL), 'log_format': settings.LOG_FORMAT})