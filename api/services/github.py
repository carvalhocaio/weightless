import asyncio
import time
from http import HTTPStatus
from typing import Any, Dict, List, Optional, Tuple

import httpx
import structlog
from fastapi import HTTPException

from ..config.settings import settings
from ..models.repository import Repository

logger = structlog.get_logger(__name__)

# In-memory cache
_cache: Dict[str, Tuple[float, Any]] = {}


class GitHubService:
    """Service for interacting with GitHub API"""

    def __init__(self):
        self.github_token = settings.github_token
        self.timeout = settings.api_timeout
        self.max_retries = settings.max_retries
        self.cache_ttl_repos = settings.cache_ttl_repos
        self.cache_ttl_languages = settings.cache_ttl_languages

        self.headers = {
            "Authorization": f"Bearer {self.github_token}",
            "Accept": "application/vnd.github+json",
        }

    def _get_from_cache(self, key: str) -> Optional[Any]:
        """Get item from cache if not expired"""
        if key in _cache:
            expires_at, value = _cache[key]
            if time.time() < expires_at:
                logger.debug("Cache hit", cache_key=key)
                return value
            else:
                logger.debug("Cache expired", cache_key=key)
                del _cache[key]
        logger.debug("Cache miss", cache_key=key)
        return None

    def _set_cache(self, key: str, value: Any, ttl: int) -> None:
        """Set item in cache with TTL in seconds"""
        expires_at = time.time() + ttl
        _cache[key] = (expires_at, value)
        logger.debug("Cache set", cache_key=key, ttl=ttl)

    async def make_request_with_retry(
        self, client: httpx.AsyncClient, url: str
    ) -> httpx.Response:
        """Make GitHub API request with exponential backoff retry on rate limiting"""
        for attempt in range(self.max_retries + 1):
            try:
                logger.debug(
                    "Making GitHub API request",
                    url=url,
                    attempt=attempt + 1,
                    max_attempts=self.max_retries + 1,
                )

                response = await client.get(
                    url, headers=self.headers, timeout=self.timeout
                )

                # Handle rate limiting
                if (
                    response.status_code == HTTPStatus.FORBIDDEN
                    and "X-RateLimit-Remaining" in response.headers
                ):
                    if response.headers.get("X-RateLimit-Remaining") == "0":
                        if attempt < self.max_retries:
                            wait_time = 2**attempt
                            logger.warning(
                                "Rate limited, retrying",
                                wait_time=wait_time,
                                attempt=attempt + 1,
                                max_attempts=self.max_retries + 1,
                            )
                            await asyncio.sleep(wait_time)
                            continue
                        else:
                            reset_time = response.headers.get(
                                "X-RateLimit-Reset", "unknown"
                            )
                            logger.error(
                                "GitHub API rate limit exceeded",
                                reset_time=reset_time,
                            )
                            raise HTTPException(
                                status_code=429,
                                detail=f"GitHub API rate limit exceeded. Reset time: {reset_time}",
                            )

                response.raise_for_status()
                logger.debug(
                    "GitHub API request successful",
                    status_code=response.status_code,
                )
                return response

            except httpx.TimeoutException:
                if attempt < self.max_retries:
                    wait_time = 2**attempt
                    logger.warning(
                        "Request timeout, retrying",
                        wait_time=wait_time,
                        attempt=attempt + 1,
                        max_attempts=self.max_retries + 1,
                    )
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    logger.error(
                        "GitHub API request timed out after multiple attempts"
                    )
                    raise HTTPException(
                        status_code=HTTPStatus.GATEWAY_TIMEOUT,
                        detail="GitHub API request timed out after multiple attempts",
                    )

            except httpx.HTTPStatusError as e:
                logger.error(
                    "GitHub API HTTP error",
                    status_code=e.response.status_code,
                    url=url,
                )

                if e.response.status_code == HTTPStatus.NOT_FOUND:
                    raise HTTPException(
                        status_code=HTTPStatus.NOT_FOUND,
                        detail="User not found",
                    )
                elif e.response.status_code >= 500:
                    if attempt < self.max_retries:
                        wait_time = 2**attempt
                        logger.warning(
                            "Server error, retrying",
                            status_code=e.response.status_code,
                            wait_time=wait_time,
                        )
                        await asyncio.sleep(wait_time)
                        continue

                raise HTTPException(
                    status_code=e.response.status_code,
                    detail=f"GitHub API error: {e.response.status_code}",
                )

        logger.error("Maximum retries exceeded")
        raise HTTPException(status_code=500, detail="Maximum retries exceeded")

    async def fetch_repository_languages(
        self, client: httpx.AsyncClient, repo: dict
    ) -> Tuple[str, List[str]]:
        """Fetch languages for a single repository"""
        repo_name = repo["name"]
        cache_key = f"languages:{repo['languages_url']}"

        # Check cache first
        cached_languages = self._get_from_cache(cache_key)
        if cached_languages is not None:
            return repo_name, cached_languages

        try:
            logger.debug(
                "Fetching languages for repository", repo_name=repo_name
            )
            langs_resp = await self.make_request_with_retry(
                client, repo["languages_url"]
            )
            languages = list(langs_resp.json().keys())

            # Cache the result
            self._set_cache(cache_key, languages, self.cache_ttl_languages)

            logger.debug(
                "Fetched languages successfully",
                repo_name=repo_name,
                languages_count=len(languages),
            )
            return repo_name, languages

        except Exception as e:
            logger.warning(
                "Failed to fetch languages for repository",
                repo_name=repo_name,
                error=str(e),
            )
            return repo_name, []

    async def get_user_repositories(self, username: str) -> List[Repository]:
        """Get user's repositories with languages"""
        # Check cache first
        cache_key = f"repos:{username}"
        cached_result = self._get_from_cache(cache_key)
        if cached_result is not None:
            logger.info("Returning cached repositories", username=username)
            return cached_result

        logger.info("Fetching repositories from GitHub", username=username)

        async with httpx.AsyncClient() as client:
            # Fetch repositories
            repo_url = f"https://api.github.com/users/{username}/repos?sort=updated&per_page=3"
            repo_resp = await self.make_request_with_retry(client, repo_url)
            repos = repo_resp.json()

            logger.debug(
                "Fetched repositories",
                username=username,
                repo_count=len(repos),
            )

            # Fetch languages for all repos concurrently
            language_tasks = [
                self.fetch_repository_languages(client, repo) for repo in repos
            ]
            language_results = await asyncio.gather(
                *language_tasks, return_exceptions=True
            )

            # Build language mapping
            language_map = {}
            for result in language_results:
                if isinstance(result, Exception):
                    logger.warning("Language fetch failed", error=str(result))
                    continue
                repo_name, languages = result
                language_map[repo_name] = languages

            # Build response
            filtered_repos = [
                Repository(
                    name=repo["name"],
                    full_name=repo["full_name"],
                    description=repo.get("description"),
                    html_url=repo["html_url"],
                    languages=language_map.get(repo["name"], []),
                    updated_at=repo["updated_at"],
                    created_at=repo["created_at"],
                    pushed_at=repo.get("pushed_at"),
                    stargazers_count=repo["stargazers_count"],
                    forks_count=repo["forks_count"],
                    open_issues_count=repo["open_issues_count"],
                    is_private=repo["private"],
                    is_fork=repo["fork"],
                )
                for repo in repos
            ]

            # Cache the result
            self._set_cache(cache_key, filtered_repos, self.cache_ttl_repos)

            logger.info(
                "Successfully fetched and cached repositories",
                username=username,
                repo_count=len(filtered_repos),
            )

            return filtered_repos


# Global service instance
github_service = GitHubService()
