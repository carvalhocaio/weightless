from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient

from api.config.settings import Settings
from api.main import app


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def mock_settings():
    """Mock settings for testing"""
    return Settings(
        github_token="test_token",
        cors_origins="http://localhost:3000",
        api_timeout=30.0,
        max_retries=3,
        cache_ttl_repos=300,
        cache_ttl_languages=600,
        sentry_dsn=None,
        log_level="DEBUG",
        debug=True,
    )


@pytest.fixture
def sample_github_repos():
    """Sample GitHub repository data"""
    return [
        {
            "name": "test-repo-1",
            "full_name": "testuser/test-repo-1",
            "description": "A test repository",
            "html_url": "https://github.com/testuser/test-repo-1",
            "languages_url": "https://api.github.com/repos/testuser/test-repo-1/languages",
            "updated_at": "2023-12-01T10:00:00Z",
            "created_at": "2023-01-01T10:00:00Z",
            "pushed_at": "2023-11-30T10:00:00Z",
            "stargazers_count": 10,
            "forks_count": 2,
            "open_issues_count": 1,
            "private": False,
            "fork": False,
        },
        {
            "name": "test-repo-2",
            "full_name": "testuser/test-repo-2",
            "description": "Another test repository",
            "html_url": "https://github.com/testuser/test-repo-2",
            "languages_url": "https://api.github.com/repos/testuser/test-repo-2/languages",
            "updated_at": "2023-11-01T10:00:00Z",
            "created_at": "2023-02-01T10:00:00Z",
            "pushed_at": "2023-10-30T10:00:00Z",
            "stargazers_count": 5,
            "forks_count": 1,
            "open_issues_count": 0,
            "private": False,
            "fork": False,
        },
    ]


@pytest.fixture
def sample_languages():
    """Sample language data for repositories"""
    return {
        "test-repo-1": {"Python": 100, "JavaScript": 50},
        "test-repo-2": {"TypeScript": 200, "CSS": 30},
    }


@pytest.fixture
def mock_httpx_response():
    """Mock httpx Response factory"""

    def _create_response(
        status_code: int = 200,
        json_data: Any = None,
        headers: Dict[str, str] = None,
    ):
        response = MagicMock()
        response.status_code = status_code
        response.json.return_value = json_data or {}
        response.headers = headers or {}
        response.raise_for_status.return_value = None
        return response

    return _create_response


@pytest.fixture
def mock_github_client():
    """Mock GitHub API client"""
    with patch("api.services.github.httpx.AsyncClient") as mock_client:
        yield mock_client


@pytest.fixture
def clear_cache():
    """Clear cache before each test"""
    from api.services.github import _cache

    _cache.clear()
    yield
    _cache.clear()


@pytest.fixture(autouse=True)
def reset_structlog():
    """Reset structlog context before each test"""
    import structlog

    structlog.contextvars.clear_contextvars()
    yield
    structlog.contextvars.clear_contextvars()


@pytest_asyncio.fixture
async def async_client():
    """Create async test client"""
    from httpx import AsyncClient

    from api.main import app

    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
