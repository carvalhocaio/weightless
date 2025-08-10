import re
from datetime import UTC, datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class UsernameModel(BaseModel):
    """Model for validating GitHub usernames"""

    username: str = Field(..., description="GitHub username to validate")

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        """Validate GitHub username format"""
        if not re.match(r"^[a-zA-Z0-9]([a-zA-Z0-9-]{0,37}[a-zA-Z0-9])?$", v):
            raise ValueError(
                "Username must be 1-39 characters, alphanumeric with hyphens allowed, but not at start/end"
            )
        return v


class Repository(BaseModel):
    """Enhanced model for a GitHub repository"""

    name: str = Field(..., description="Repository name")
    full_name: str = Field(
        ..., description="Full repository name (owner/repo)"
    )
    description: Optional[str] = Field(
        None, description="Repository description"
    )
    html_url: str = Field(..., description="Repository HTML URL")
    languages: List[str] = Field(
        default_factory=list, description="Programming languages used"
    )
    updated_at: datetime = Field(..., description="Last update timestamp")
    created_at: datetime = Field(..., description="Creation timestamp")
    pushed_at: Optional[datetime] = Field(
        None, description="Last push timestamp"
    )
    stargazers_count: int = Field(..., ge=0, description="Number of stars")
    forks_count: int = Field(..., ge=0, description="Number of forks")
    open_issues_count: int = Field(
        ..., ge=0, description="Number of open issues"
    )
    is_private: bool = Field(..., description="Whether repository is private")
    is_fork: bool = Field(..., description="Whether repository is a fork")


class ErrorDetail(BaseModel):
    """Model for error details"""

    type: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    code: Optional[str] = Field(None, description="Error code")


class ErrorResponse(BaseModel):
    """Standard error response model"""

    error: bool = Field(True, description="Always true for error responses")
    detail: str = Field(..., description="Error description")
    errors: Optional[List[ErrorDetail]] = Field(
        None, description="Detailed error information"
    )
    correlation_id: Optional[str] = Field(
        None, description="Request correlation ID"
    )


class HealthResponse(BaseModel):
    """Health check response model"""

    status: str = Field("healthy", description="Service status")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Check timestamp",
    )
    version: str = Field("1.0.0", description="API version")


class APIInfoResponse(BaseModel):
    """Root endpoint response model"""

    message: str = Field(..., description="API welcome message")
    docs: str = Field(..., description="Documentation URL")
    version: str = Field("1.0.0", description="API version")
