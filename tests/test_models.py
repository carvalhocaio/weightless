from datetime import datetime

import pytest
from pydantic import ValidationError

from api.models.repository import (
    APIInfoResponse,
    ErrorDetail,
    ErrorResponse,
    HealthResponse,
    Repository,
    UsernameModel,
)


class TestUsernameModel:
    """Test UsernameModel validation"""

    def test_valid_usernames(self):
        """Test valid username formats"""
        valid_usernames = ["user", "user123", "user-name", "a", "a" * 39]

        for username in valid_usernames:
            model = UsernameModel(username=username)
            assert model.username == username

    def test_invalid_usernames(self):
        """Test invalid username formats"""
        invalid_usernames = [
            "",  # empty
            "-user",  # starts with hyphen
            "user-",  # ends with hyphen
            "a" * 40,  # too long
            "user@name",  # invalid character
            "user.name",  # invalid character
            "user_name",  # underscore not allowed
        ]

        for username in invalid_usernames:
            with pytest.raises(ValidationError):
                UsernameModel(username=username)


class TestRepository:
    """Test Repository model"""

    def test_valid_repository(self):
        """Test valid repository model creation"""
        data = {
            "name": "test-repo",
            "full_name": "user/test-repo",
            "description": "A test repository",
            "html_url": "https://github.com/user/test-repo",
            "languages": ["Python", "JavaScript"],
            "updated_at": "2023-12-01T10:00:00Z",
            "created_at": "2023-01-01T10:00:00Z",
            "pushed_at": "2023-11-30T10:00:00Z",
            "stargazers_count": 10,
            "forks_count": 2,
            "open_issues_count": 1,
            "is_private": False,
            "is_fork": False,
        }

        repo = Repository(**data)
        assert repo.name == "test-repo"
        assert repo.full_name == "user/test-repo"
        assert repo.languages == ["Python", "JavaScript"]
        assert repo.stargazers_count == 10

    def test_repository_with_minimal_data(self):
        """Test repository with minimal required fields"""
        data = {
            "name": "test-repo",
            "full_name": "user/test-repo",
            "html_url": "https://github.com/user/test-repo",
            "updated_at": "2023-12-01T10:00:00Z",
            "created_at": "2023-01-01T10:00:00Z",
            "stargazers_count": 0,
            "forks_count": 0,
            "open_issues_count": 0,
            "is_private": False,
            "is_fork": False,
        }

        repo = Repository(**data)
        assert repo.description is None
        assert repo.languages == []
        assert repo.pushed_at is None

    def test_invalid_counts(self):
        """Test validation of negative counts"""
        base_data = {
            "name": "test-repo",
            "full_name": "user/test-repo",
            "html_url": "https://github.com/user/test-repo",
            "updated_at": "2023-12-01T10:00:00Z",
            "created_at": "2023-01-01T10:00:00Z",
            "is_private": False,
            "is_fork": False,
        }

        # Test negative stargazers_count
        with pytest.raises(ValidationError):
            Repository(
                **{
                    **base_data,
                    "stargazers_count": -1,
                    "forks_count": 0,
                    "open_issues_count": 0,
                }
            )

        # Test negative forks_count
        with pytest.raises(ValidationError):
            Repository(
                **{
                    **base_data,
                    "stargazers_count": 0,
                    "forks_count": -1,
                    "open_issues_count": 0,
                }
            )

        # Test negative open_issues_count
        with pytest.raises(ValidationError):
            Repository(
                **{
                    **base_data,
                    "stargazers_count": 0,
                    "forks_count": 0,
                    "open_issues_count": -1,
                }
            )



class TestErrorResponse:
    """Test ErrorResponse model"""

    def test_basic_error_response(self):
        """Test basic error response"""
        error = ErrorResponse(detail="Something went wrong")
        assert error.error is True
        assert error.detail == "Something went wrong"
        assert error.errors is None
        assert error.correlation_id is None

    def test_detailed_error_response(self):
        """Test error response with details"""
        error_details = [
            ErrorDetail(
                type="validation_error",
                message="Field is required",
                code="required",
            )
        ]

        error = ErrorResponse(
            detail="Validation failed",
            errors=error_details,
            correlation_id="test-123",
        )

        assert error.error is True
        assert error.detail == "Validation failed"
        assert len(error.errors) == 1
        assert error.errors[0].type == "validation_error"
        assert error.correlation_id == "test-123"


class TestHealthResponse:
    """Test HealthResponse model"""

    def test_default_health_response(self):
        """Test default health response"""
        health = HealthResponse()
        assert health.status == "healthy"
        assert health.version == "1.0.0"
        assert isinstance(health.timestamp, datetime)


class TestAPIInfoResponse:
    """Test APIInfoResponse model"""

    def test_api_info_response(self):
        """Test API info response"""
        info = APIInfoResponse(
            message="Welcome to API",
            docs="http://localhost/docs",
            version="1.0.0",
        )

        assert info.message == "Welcome to API"
        assert info.docs == "http://localhost/docs"
        assert info.version == "1.0.0"
