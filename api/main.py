import asyncio
import logging
import re
from http import HTTPStatus
from typing import List, Optional

import httpx
import sentry_sdk
from decouple import config
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator

sentry_sdk.init(dsn=config("SENTRY_DSN"), send_default_pii=True)
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

GITHUB_TOKEN = config("GITHUB_TOKEN")
TIMEOUT = 30.0  # seconds
MAX_RETRIES = 3

logger = logging.getLogger(__name__)


class UsernameModel(BaseModel):
    username: str

    @field_validator("username")
    def validate_username(cls, v):
        if not re.match(r"^[a-zA-Z0-9]([a-zA-Z0-9-]{0,37}[a-zA-Z0-9])?$", v):
            raise ValueError(
                "Username must be 1-39 characters, alphanumeric with hyphens allowed, but not at start/end"
            )
        return v


class GitHubRepoResponse(BaseModel):
    name: str
    description: Optional[str]
    languages: List[str]
    url: str


async def make_github_request_with_retry(
    client: httpx.AsyncClient, url: str, headers: dict
) -> httpx.Response:
    """Make GitHub API request with exponential backoff retry on rate limiting"""
    for attempt in range(MAX_RETRIES + 1):
        try:
            response = await client.get(url, headers=headers, timeout=TIMEOUT)

            if (
                response.status_code == HTTPStatus.FORBIDDEN
                and "X-RateLimit-Remaining" in response.headers
            ):
                if response.headers.get("X-RateLimit-Remaining") == "0":
                    if attempt < MAX_RETRIES:
                        wait_time = 2**attempt
                        logger.warning(
                            f"Rate limited, retrying in {wait_time}s (attempt {attempt + 1}/{MAX_RETRIES + 1})"
                        )
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        reset_time = response.headers.get(
                            "X-RateLimit-Reset", "unknown"
                        )
                        raise HTTPException(
                            status_code=429,
                            detail=f"GitHub API rate limit exceeded. Reset time: {reset_time}",
                        )

            response.raise_for_status()
            return response

        except httpx.TimeoutException:
            if attempt < MAX_RETRIES:
                wait_time = 2**attempt
                logger.warning(
                    f"Request timeout, retrying in {wait_time}s (attempt {attempt + 1}/{MAX_RETRIES + 1})"
                )
                await asyncio.sleep(wait_time)
                continue
            else:
                raise HTTPException(
                    status_code=HTTPStatus.GATEWAY_TIMEOUT,
                    detail="GitHub API request timed out after multiple attempts",
                )
        except httpx.HTTPStatusError as e:
            if e.response.status_code == HTTPStatus.NOT_FOUND:
                raise HTTPException(
                    status_code=HTTPStatus.NOT_FOUND, detail="User not found"
                )
            elif e.response.status_code >= 500:
                if attempt < MAX_RETRIES:
                    wait_time = 2**attempt
                    logger.warning(
                        f"Server error {e.response.status_code}, retrying in {wait_time}s"
                    )
                    await asyncio.sleep(wait_time)
                    continue
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"GitHub API error: {e.response.status_code}",
            )

    raise HTTPException(status_code=500, detail="Maximum retries exceeded")


@app.get("/", status_code=HTTPStatus.OK)
def root(request: Request):
    base_url = str(request.base_url).rstrip("/")
    return {"message": "Weightless API", "docs": f"{base_url}/docs"}


@app.get("/github/repos/{username}")
async def get_github_repos(username: str) -> List[GitHubRepoResponse]:
    # Validate username
    try:
        UsernameModel(username=username)
    except ValueError as e:
        raise HTTPException(
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            detail=f"Invalid username: {str(e)}",
        )

    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
    }

    async with httpx.AsyncClient() as client:
        repo_url = f"https://api.github.com/users/{username}/repos?sort=updated&per_page=3"
        repo_resp = await make_github_request_with_retry(
            client, repo_url, headers
        )
        repos = repo_resp.json()

        # Fetch languages for each repo with graceful error handling
        filtered_repos = []
        for repo in repos:
            try:
                langs_resp = await make_github_request_with_retry(
                    client, repo["languages_url"], headers
                )
                languages = list(langs_resp.json().keys())
            except Exception as e:
                logger.warning(
                    f"Failed to fetch languages for {repo['name']}: {str(e)}"
                )
                languages = []

            filtered_repos.append(
                GitHubRepoResponse(
                    name=repo["name"],
                    description=repo.get("description"),
                    languages=languages,
                    url=repo["html_url"],
                )
            )

        return filtered_repos
