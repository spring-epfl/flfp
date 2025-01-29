from datetime import datetime
import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from csv import writer

import requests
import tqdm

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")


class IssueListError(Exception):
    pass


def _is_valid_issue_list_resp(resp: requests.Response) -> bool:
    return (
        resp.status_code == 200
        and resp.headers["Content-Type"] == "application/json; charset=utf-8"
        and isinstance(resp.json(), list)
        and len(resp.json()) > 0
        and "url" in resp.json()[0]
    )


def scrape_issues_iter(
    repo: str,
    url_args: Optional[dict] = None,
    page_start=1,
    pages_limit: Optional[int] = None,
    date_limit: Optional[datetime] = None,
):

    if url_args is None:
        url_args = {}

    page = page_start

    resp = requests.get(
        f"https://api.github.com/repos/{repo}/issues",
        params={**url_args, "page": page},
        headers={
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Accept": "application/vnd.github+json",
        },
    )
    
    tqdm.tqdm.write(resp.request.url)

    if not _is_valid_issue_list_resp(resp):
        raise IssueListError(f"Invalid response: {resp} - {resp.text}")

    while _is_valid_issue_list_resp(resp):
        for issue in resp.json():
            if (
                date_limit
                and datetime.strptime(issue["created_at"], "%Y-%m-%dT%H:%M:%SZ")
                < date_limit
            ):
                return

            yield issue

        if pages_limit and page >= pages_limit:
            return

        page += 1
        resp = requests.get(
            f"https://api.github.com/repos/{repo}/issues",
            params={**url_args, "page": page},
            headers={"Authorization": f"token {GITHUB_TOKEN}"},
        )

        tqdm.tqdm.write(resp.request.url)
