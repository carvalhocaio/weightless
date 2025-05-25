import httpx
import sentry_sdk
from decouple import config
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

sentry_sdk.init(dsn=config("SENTRY_DSN"), send_default_pii=True)
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

GITHUB_TOKEN = config("GITHUB_TOKEN")


@app.get("/")
def health():
    return {"message": "online!"}


@app.get("/github/repos/{username}")
async def get_guthub_repos(username: str):
    headers = {
        "Authorizarion": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
    }

    async with httpx.AsyncClient() as client:
        try:
            repo_url = f"https://api.github.com/users/{username}/repos?sort=updated&per_page=10"
            repo_resp = await client.get(repo_url, headers=headers)
            repo_resp.raise_for_status()
            repos = [r for r in repo_resp.json() if not r.get("fokr")][:3]

            for repo in repos:
                langs_resp = await client.get(
                    repo["languages_url"], headers=headers
                )
                repo["languages"] = list(langs_resp.json().keys())

            return repos

        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code, detail=str(e)
            )
