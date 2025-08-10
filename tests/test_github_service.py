from http import HTTPStatus
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi import HTTPException

from api.models.repository import GitHubRepoResponse
from api.services.github import GitHubService, _cache


class TestGitHubService:
    """Test GitHubService functionality"""

    @pytest.fixture
    def service(self, mock_settings):
        """Create GitHubService instance with mock settings"""
        with patch("api.services.github.settings", mock_settings):
            return GitHubService()

    def test_cache_operations(self, service, clear_cache):
        """Test cache get/set operations"""
        key = "test:key"
        value = {"test": "data"}
        ttl = 300

        # Test cache miss
        result = service._get_from_cache(key)
        assert result is None

        # Test cache set and hit
        service._set_cache(key, value, ttl)
        result = service._get_from_cache(key)
        assert result == value

        # Test cache expiration
        service._set_cache(key, value, -1)  # Expired
        result = service._get_from_cache(key)
        assert result is None
        assert key not in _cache

    @pytest.mark.asyncio
    async def test_make_request_with_retry_success(self, service):
        """Test successful API request"""
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.raise_for_status.return_value = None

        mock_client.get.return_value = mock_response

        result = await service.make_request_with_retry(
            mock_client, "https://api.github.com/test"
        )

        assert result == mock_response
        mock_client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_make_request_with_retry_rate_limit(self, service):
        """Test rate limit handling with retry"""
        mock_client = AsyncMock()

        # First response: rate limited
        rate_limited_response = MagicMock()
        rate_limited_response.status_code = HTTPStatus.FORBIDDEN
        rate_limited_response.headers = {"X-RateLimit-Remaining": "0"}

        # Second response: success
        success_response = MagicMock()
        success_response.status_code = 200
        success_response.headers = {}
        success_response.raise_for_status.return_value = None

        mock_client.get.side_effect = [rate_limited_response, success_response]

        with patch(
            "api.services.github.asyncio.sleep", new_callable=AsyncMock
        ):
            result = await service.make_request_with_retry(
                mock_client, "https://api.github.com/test"
            )

        assert result == success_response
        assert mock_client.get.call_count == 2

    @pytest.mark.asyncio
    async def test_make_request_with_retry_rate_limit_exceeded(self, service):
        """Test rate limit exceeded after max retries"""
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = HTTPStatus.FORBIDDEN
        mock_response.headers = {
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Reset": "1234567890",
        }

        mock_client.get.return_value = mock_response

        with patch(
            "api.services.github.asyncio.sleep", new_callable=AsyncMock
        ):
            with pytest.raises(HTTPException) as exc_info:
                await service.make_request_with_retry(
                    mock_client, "https://api.github.com/test"
                )

        assert exc_info.value.status_code == 429
        assert "rate limit exceeded" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_make_request_with_retry_timeout(self, service):
        """Test timeout handling"""
        mock_client = AsyncMock()
        mock_client.get.side_effect = httpx.TimeoutException(
            "Request timed out"
        )

        with patch(
            "api.services.github.asyncio.sleep", new_callable=AsyncMock
        ):
            with pytest.raises(HTTPException) as exc_info:
                await service.make_request_with_retry(
                    mock_client, "https://api.github.com/test"
                )

        assert exc_info.value.status_code == HTTPStatus.GATEWAY_TIMEOUT
        assert "timed out" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_make_request_with_retry_not_found(self, service):
        """Test 404 error handling"""
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = HTTPStatus.NOT_FOUND

        error = httpx.HTTPStatusError(
            "Not found", request=MagicMock(), response=mock_response
        )
        mock_client.get.side_effect = error

        with pytest.raises(HTTPException) as exc_info:
            await service.make_request_with_retry(
                mock_client, "https://api.github.com/test"
            )

        assert exc_info.value.status_code == HTTPStatus.NOT_FOUND
        assert exc_info.value.detail == "User not found"

    @pytest.mark.asyncio
    async def test_fetch_repository_languages_success(
        self, service, sample_languages
    ):
        """Test successful language fetching"""
        repo = {
            "name": "test-repo",
            "languages_url": "https://api.github.com/repos/user/test-repo/languages",
        }

        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = sample_languages["test-repo-1"]

        with patch.object(
            service, "make_request_with_retry", return_value=mock_response
        ):
            repo_name, languages = await service.fetch_repository_languages(
                mock_client, repo
            )

        assert repo_name == "test-repo"
        assert languages == ["Python", "JavaScript"]

    @pytest.mark.asyncio
    async def test_fetch_repository_languages_cached(
        self, service, clear_cache
    ):
        """Test cached language fetching"""
        repo = {
            "name": "test-repo",
            "languages_url": "https://api.github.com/repos/user/test-repo/languages",
        }

        # Pre-populate cache
        cache_key = f"languages:{repo['languages_url']}"
        service._set_cache(cache_key, ["Python", "JavaScript"], 300)

        mock_client = AsyncMock()

        repo_name, languages = await service.fetch_repository_languages(
            mock_client, repo
        )

        assert repo_name == "test-repo"
        assert languages == ["Python", "JavaScript"]
        # Should not make any API calls
        mock_client.get.assert_not_called()

    @pytest.mark.asyncio
    async def test_fetch_repository_languages_error(self, service):
        """Test language fetching with error"""
        repo = {
            "name": "test-repo",
            "languages_url": "https://api.github.com/repos/user/test-repo/languages",
        }

        mock_client = AsyncMock()

        with patch.object(
            service,
            "make_request_with_retry",
            side_effect=Exception("API Error"),
        ):
            repo_name, languages = await service.fetch_repository_languages(
                mock_client, repo
            )

        assert repo_name == "test-repo"
        assert languages == []

    @pytest.mark.asyncio
    async def test_get_user_repositories_success(
        self, service, sample_github_repos, sample_languages, clear_cache
    ):
        """Test successful repository fetching"""
        username = "testuser"

        mock_client = AsyncMock()

        # Mock repos response
        repos_response = MagicMock()
        repos_response.json.return_value = sample_github_repos

        # Mock language responses
        async def mock_fetch_languages(client, repo):
            repo_name = repo["name"]
            if repo_name in ["test-repo-1", "test-repo-2"]:
                languages = list(sample_languages.get(repo_name, {}).keys())
                return repo_name, languages
            return repo_name, []

        with patch.object(
            service, "make_request_with_retry", return_value=repos_response
        ):
            with patch.object(
                service,
                "fetch_repository_languages",
                side_effect=mock_fetch_languages,
            ):
                repositories = await service.get_user_repositories(username)

        assert len(repositories) == 2
        assert isinstance(repositories[0], GitHubRepoResponse)
        assert repositories[0].name == "test-repo-1"
        assert repositories[0].languages == ["Python", "JavaScript"]
        assert repositories[1].name == "test-repo-2"
        assert repositories[1].languages == ["TypeScript", "CSS"]

    @pytest.mark.asyncio
    async def test_get_user_repositories_cached(self, service, clear_cache):
        """Test cached repository fetching"""
        username = "testuser"
        cached_repos = [
            GitHubRepoResponse(
                name="cached-repo",
                description="Cached repository",
                languages=["Python"],
                url="https://github.com/testuser/cached-repo",
            )
        ]

        # Pre-populate cache
        cache_key = f"repos:{username}"
        service._set_cache(cache_key, cached_repos, 300)

        repositories = await service.get_user_repositories(username)

        assert repositories == cached_repos

    @pytest.mark.asyncio
    async def test_get_user_repositories_with_language_errors(
        self, service, sample_github_repos
    ):
        """Test repository fetching with some language fetch errors"""
        username = "testuser"

        mock_client = AsyncMock()

        # Mock repos response
        repos_response = MagicMock()
        repos_response.json.return_value = sample_github_repos[
            :1
        ]  # Only one repo

        # Mock language fetch with error
        async def mock_fetch_languages_with_error(client, repo):
            if repo["name"] == "test-repo-1":
                raise Exception("Language fetch failed")
            return repo["name"], []

        with patch.object(
            service, "make_request_with_retry", return_value=repos_response
        ):
            with patch.object(
                service,
                "fetch_repository_languages",
                side_effect=mock_fetch_languages_with_error,
            ):
                repositories = await service.get_user_repositories(username)

        assert len(repositories) == 1
        assert repositories[0].name == "test-repo-1"
        assert repositories[0].languages == []  # Empty due to fetch error
