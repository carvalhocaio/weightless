import sys
from uuid import uuid4

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from .settings import settings


def configure_logging():
    """Configure structured logging for the application"""
    # Configure structlog
    structlog.configure(
        processors=[
            # Filter log level
            structlog.stdlib.filter_by_level,
            # Add the log level and a timestamp to the event_dict
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            # Add correlation ID if available
            structlog.contextvars.merge_contextvars,
            # Stack info for exceptions
            structlog.processors.StackInfoRenderer(),
            # Format exceptions
            structlog.dev.set_exc_info,
            # JSON renderer for production, console for development
            structlog.processors.JSONRenderer()
            if not settings.debug
            else structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure standard library logging
    import logging

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.log_level),
    )


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to add request logging and correlation IDs"""

    async def dispatch(self, request: Request, call_next):
        # Generate correlation ID
        correlation_id = str(uuid4())

        # Bind correlation ID to context
        structlog.contextvars.bind_contextvars(
            correlation_id=correlation_id,
            method=request.method,
            url=str(request.url),
            user_agent=request.headers.get("user-agent", "unknown"),
        )

        logger = structlog.get_logger(__name__)

        # Log request start
        logger.info(
            "Request started",
            path=request.url.path,
            query_params=dict(request.query_params),
        )

        # Process request
        try:
            response: Response = await call_next(request)

            # Log successful response
            logger.info(
                "Request completed",
                status_code=response.status_code,
            )

            # Add correlation ID to response headers
            response.headers["X-Correlation-ID"] = correlation_id

            return response

        except Exception as exc:
            # Log error
            logger.error("Request failed", error=str(exc), exc_info=True)
            raise

        finally:
            # Clear context variables
            structlog.contextvars.clear_contextvars()


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a configured logger instance"""
    return structlog.get_logger(name)
