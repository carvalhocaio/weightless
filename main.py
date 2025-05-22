import httpx
from decouple import Csv, config
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=config("ALLOW_ORIGINS", default="*"),
    allow_methods=config("ALLOW_METHODS", default="*"),
    allow_headers=config("ALLOW_HEADERS", default="*"),
)

GITHUB_USERNAME = "carvalhocaio"
GITHUB_TOKEN = config("GITHUB_TOKEN")


@app.get("/github/repos")
async def get_guthub_repos():
    headers = {
        "Authorizarion": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
    }

    async with httpx.AsyncClient() as client:
        try:
            repo_url = f"https://api.github.com/users/{GITHUB_USERNAME}/repos?sort=updated&per_page=10"
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


# the song that inspired the name for this project
# https://www.youtube.com/watch?v=DOT1LmQbFFA&pp=ygUKd2VpZ2h0bGVzcw%3D%3D
