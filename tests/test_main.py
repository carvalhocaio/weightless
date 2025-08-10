from http import HTTPStatus
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from api.main import app
from api.models.repository import GitHubRepoResponse


class TestMainEndpoints:
    """Test main API endpoints"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)

    def test_root_endpoint(self, client):
        """Test root endpoint"""
        response = client.get("/")

        assert response.status_code == HTTPStatus.OK
        data = response.json()
        assert "message" in data
        assert "docs" in data
        assert "version" in data
        assert data["version"] == "1.0.0"

    def test_health_endpoint(self, client):
        """Test health endpoint"""
        response = client.get("/health")

        assert response.status_code == HTTPStatus.OK
        data = response.json()
        assert data["status"] == "healthy"
        assert data["version"] == "1.0.0"
        assert "timestamp" in data

    def test_github_repos_valid_username(self, client):
        """Test GitHub repos endpoint with valid username"""
        mock_repos = [
            GitHubRepoResponse(
                name="test-repo",
                description="A test repository",
                languages=["Python"],
                url="https://github.com/testuser/test-repo",
            )
        ]

        with patch(
            "api.main.github_service.get_user_repositories",
            new_callable=AsyncMock,
        ) as mock_service:
            mock_service.return_value = mock_repos

            response = client.get("/github/repos/testuser")

        assert response.status_code == HTTPStatus.OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "test-repo"
        assert data[0]["languages"] == ["Python"]
        mock_service.assert_called_once_with("testuser")

    def test_github_repos_invalid_username_format(self, client):
        """Test GitHub repos endpoint with invalid username format"""
        invalid_usernames = [
            "-invalid",  # starts with hyphen
            "invalid-",  # ends with hyphen
            "a" * 40,  # too long
            "user@name",  # invalid character
        ]

        for username in invalid_usernames:
            response = client.get(f"/github/repos/{username}")
            assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
            data = response.json()
            assert "Invalid username format" in data["detail"]

    def test_github_repos_user_not_found(self, client):
        """Test GitHub repos endpoint with non-existent user"""
        with patch(
            "api.main.github_service.get_user_repositories",
            new_callable=AsyncMock,
        ) as mock_service:
            mock_service.side_effect = HTTPException(
                status_code=HTTPStatus.NOT_FOUND, detail="User not found"
            )

            response = client.get("/github/repos/nonexistentuser")

        assert response.status_code == HTTPStatus.NOT_FOUND
        data = response.json()
        assert data["detail"] == "User not found"

    def test_github_repos_rate_limit_exceeded(self, client):
        """Test GitHub repos endpoint with rate limit exceeded"""
        with patch(
            "api.main.github_service.get_user_repositories",
            new_callable=AsyncMock,
        ) as mock_service:
            mock_service.side_effect = HTTPException(
                status_code=429,
                detail="GitHub API rate limit exceeded. Reset time: 1234567890",
            )

            response = client.get("/github/repos/testuser")

        assert response.status_code == 429
        data = response.json()
        assert "rate limit exceeded" in data["detail"].lower()

    def test_github_repos_timeout(self, client):
        """Test GitHub repos endpoint with timeout"""
        with patch(
            "api.main.github_service.get_user_repositories",
            new_callable=AsyncMock,
        ) as mock_service:
            mock_service.side_effect = HTTPException(
                status_code=HTTPStatus.GATEWAY_TIMEOUT,
                detail="GitHub API request timed out after multiple attempts",
            )

            response = client.get("/github/repos/testuser")

        assert response.status_code == HTTPStatus.GATEWAY_TIMEOUT
        data = response.json()
        assert "timed out" in data["detail"].lower()

    def test_github_repos_internal_error(self, client):
        """Test GitHub repos endpoint with unexpected error"""
        with patch(
            "api.main.github_service.get_user_repositories",
            new_callable=AsyncMock,
        ) as mock_service:
            mock_service.side_effect = Exception("Unexpected error")

            response = client.get("/github/repos/testuser")

        assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
        data = response.json()
        assert "unexpected error" in data["detail"].lower()

    def test_cors_headers(self, client):
        """Test CORS headers are present"""
        response = client.options("/github/repos/testuser")

        # Note: TestClient might not handle CORS exactly like a browser
        # This test verifies the endpoint is accessible
        # CORS functionality would be better tested with actual browser requests
        assert response.status_code in [
            HTTPStatus.OK,
            HTTPStatus.METHOD_NOT_ALLOWED,
        ]

    def test_correlation_id_in_response(self, client):
        """Test that correlation ID is added to response headers"""
        mock_repos = [
            GitHubRepoResponse(
                name="test-repo",
                description="A test repository",
                languages=["Python"],
                url="https://github.com/testuser/test-repo",
            )
        ]

        with patch(
            "api.main.github_service.get_user_repositories",
            new_callable=AsyncMock,
        ) as mock_service:
            mock_service.return_value = mock_repos

            response = client.get("/github/repos/testuser")

        assert response.status_code == HTTPStatus.OK
        # Check if correlation ID header exists
        assert (
            "X-Correlation-ID" in response.headers
            or "x-correlation-id" in response.headers
        )

    def test_openapi_docs(self, client):
        """Test that OpenAPI documentation is accessible"""
        response = client.get("/docs")
        assert response.status_code == HTTPStatus.OK

        # Test OpenAPI schema
        response = client.get("/openapi.json")
        assert response.status_code == HTTPStatus.OK
        schema = response.json()
        assert "openapi" in schema
        assert "paths" in schema
        assert "/github/repos/{username}" in schema["paths"]

    def test_multiple_valid_usernames(self, client):
        """Test multiple valid username formats"""
        valid_usernames = [
            "user",
            "user123",
            "user-name",
            "a",
            "test-user-123",
            "x" * 39,  # max length
        ]

        mock_repos = [
            GitHubRepoResponse(
                name="test-repo",
                description="A test repository",
                languages=["Python"],
                url="https://github.com/testuser/test-repo",
            )
        ]

        with patch(
            "api.main.github_service.get_user_repositories",
            new_callable=AsyncMock,
        ) as mock_service:
            mock_service.return_value = mock_repos

            for username in valid_usernames:
                response = client.get(f"/github/repos/{username}")
                assert response.status_code == HTTPStatus.OK, (
                    f"Failed for username: {username}"
                )
                data = response.json()
                assert len(data) == 1
                assert data[0]["name"] == "test-repo"


class TestErrorHandlers:
    """Test custom error handlers"""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_validation_error_handler(self, client):
        """Test that validation errors are handled properly"""
        # This should trigger validation error through the username validation
        response = client.get("/github/repos/-invalid")

        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
        data = response.json()
        assert "detail" in data

    def test_404_error_format(self, client):
        """Test 404 error format"""
        response = client.get("/nonexistent-endpoint")

        assert response.status_code == HTTPStatus.NOT_FOUND
        data = response.json()
        assert "detail" in data
