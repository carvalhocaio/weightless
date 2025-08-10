from http import HTTPStatus
from typing import List

import sentry_sdk
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError

from .config.logging import LoggingMiddleware, configure_logging, get_logger
from .config.settings import settings
from .models.repository import (
    APIInfoResponse,
    ErrorResponse,
    Repository,
    HealthResponse,
    UsernameModel,
)
from .services.github import github_service

# Configure logging before anything else
configure_logging()
logger = get_logger(__name__)

# Initialize Sentry if DSN is provided
if settings.sentry_dsn:
    sentry_sdk.init(dsn=settings.sentry_dsn, send_default_pii=True)
    logger.info("Sentry initialized")

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="GitHub repository API with caching and rate limiting support",
)

# Add middlewares
app.add_middleware(LoggingMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET"],
    allow_headers=[
        "Accept",
        "Accept-Language",
        "Content-Language",
        "Content-Type",
        "X-Correlation-ID",
    ],
    allow_credentials=False,
    expose_headers=["X-Correlation-ID"],
)

logger.info(
    "Application startup complete",
    app_name=settings.app_name,
    version=settings.app_version,
)


@app.get("/", response_model=APIInfoResponse, status_code=HTTPStatus.OK)
def root(request: Request) -> APIInfoResponse:
    """Root endpoint providing API information"""
    base_url = str(request.base_url).rstrip("/")
    logger.debug("Root endpoint accessed", base_url=base_url)

    return APIInfoResponse(
        message=f"Welcome to {settings.app_name}",
        docs=f"{base_url}/docs",
        version=settings.app_version,
    )


@app.get("/health", response_model=HealthResponse, status_code=HTTPStatus.OK)
def health() -> HealthResponse:
    """Health check endpoint"""
    logger.debug("Health check accessed")
    return HealthResponse()


@app.get(
    "/github/repos/{username}",
    response_model=List[Repository],
    responses={
        404: {"model": ErrorResponse, "description": "User not found"},
        422: {
            "model": ErrorResponse,
            "description": "Invalid username format",
        },
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
        502: {"model": ErrorResponse, "description": "GitHub API error"},
        504: {"model": ErrorResponse, "description": "Request timeout"},
    },
)
async def get_github_repos(username: str) -> List[Repository]:
    """
    Get user's GitHub repositories

    Returns the 3 most recently updated repositories for the specified user,
    including programming languages used in each repository.

    - **username**: GitHub username (1-39 characters, alphanumeric with hyphens)
    """
    logger.info("Repository request received", username=username)

    # Validate username
    try:
        UsernameModel(username=username)
    except ValidationError as e:
        logger.warning(
            "Invalid username format", username=username, errors=e.errors()
        )
        raise HTTPException(
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            detail=f"Invalid username format: {e.errors()[0]['msg']}",
        )

    try:
        # Fetch repositories using the service
        repositories = await github_service.get_user_repositories(username)

        logger.info(
            "Successfully returned repositories",
            username=username,
            repo_count=len(repositories),
        )

        return repositories

    except HTTPException:
        # Re-raise HTTP exceptions (they're already properly formatted)
        raise

    except Exception as exc:
        logger.error(
            "Unexpected error fetching repositories",
            username=username,
            error=str(exc),
            exc_info=True,
        )
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while fetching repositories",
        )


@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
    """Handle Pydantic validation errors"""
    logger.warning(
        "Validation error", url=str(request.url), errors=exc.errors()
    )
    return ErrorResponse(
        error=True,
        detail="Validation error",
        errors=[
            {"type": err["type"], "message": err["msg"]}
            for err in exc.errors()
        ],
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc: Exception):
    """Handle internal server errors"""
    logger.error(
        "Internal server error",
        url=str(request.url),
        error=str(exc),
        exc_info=True,
    )
    return ErrorResponse(error=True, detail="Internal server error occurred")
