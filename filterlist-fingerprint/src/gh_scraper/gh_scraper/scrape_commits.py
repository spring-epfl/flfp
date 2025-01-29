"""
This part is used to check the update frequency of various types of rules

In the end we want to get a snapshot of the updates happening. columns:
- commit_id
- prev_rule
- new_rule
- file_path
- change_type: added, removed, modified
- timestamp
- message

Later with other modules we will parse the "changed rule" and identify scope and type

Used for stability experimendt

Ref for parsing diffs:
- https://stackoverflow.com/questions/39423122/python-git-diff-parser

# Limitations of determining modified:
- could be moving lines across files or something, we are not considering that
- so modifications are a lower bound, additions and removals upper bound
"""

from collections import defaultdict
from datetime import datetime, timedelta
from io import StringIO
import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Set
from dotenv import load_dotenv

from filterlist_parser.utils import slug
from gh_scraper.logging import CSVExperimentLogger
import pandas as pd
import requests
from tqdm import tqdm
from unidiff import PatchSet

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REQ_TIMEOUT_S = 20


class CommitListError(Exception):
    """Raised when the commit list is invalid"""


def _is_valid_commit_list_resp(resp: requests.Response, check_length=True) -> bool:
    return (
        resp.status_code == 200
        and resp.headers["Content-Type"] == "application/json; charset=utf-8"
        and isinstance(resp.json(), list)
        and (not check_length or len(resp.json()) > 0)
        and (not check_length or "url" in resp.json()[0])
    )


def _try_reach_github_fp(repo: str, fp: str, branch: str = "master") -> bool:
    try:
        return (
            requests.get(
                f"https://raw.githubusercontent.com/{repo}/{branch}/{fp}",
                timeout=REQ_TIMEOUT_S,
            ).status_code
            == 200
        )
    except:  # pylint: disable=bare-except
        return False


def _get_latest_commit_until(repo: str, date_max: datetime, branch: str = "master"):
    """Get the latest commit until a specific date"""

    if branch in {"master", "main"}:
        branch = None

    req = f"https://api.github.com/repos/{repo}/commits"
    params = {
        "per_page": 1,
        "until": date_max.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sha": branch,
    }
    resp = requests.get(
        req,
        params=params,
        headers={"Authorization": f"token {GITHUB_TOKEN}"},
        timeout=REQ_TIMEOUT_S,
    )

    if not _is_valid_commit_list_resp(resp):
        if resp.status_code == 200:
            raise ValueError("Empty List")
        else:
            raise CommitListError(f"Invalid response: {resp} - {resp.text}")

    return resp.json()[0]


def _get_filterlist_content_at_commit(
    repo: str, commit_sha: str, file_paths: List[str], raise_error=True
):
    """Get the content of the filterlist at a specific commit"""

    filterlist_content = ""

    for file_path in file_paths:

        resp = requests.get(
            f"https://raw.githubusercontent.com/{repo}/{commit_sha}/{file_path}",
            timeout=REQ_TIMEOUT_S,
        )

        if resp.status_code != 200:
            if raise_error:
                raise ValueError(
                    f"Could not reach file: {file_path} in commit: {commit_sha}. error message: {resp.text}"
                )
            else:
                content = ""

        else:
            content = resp.text

        filterlist_content += content + "\n"

    return filterlist_content


def _get_filterlist_version_control(filterlist: dict) -> dict:
    """
    Get the version control information for a filterlist including repo, branch, and file paths
    """

    if "version_control" in filterlist:
        vc = dict(filterlist["version_control"])
        if "branch" not in vc:
            vc["branch"] = "master"
        return vc

    if filterlist["url"].startswith("https://raw.githubusercontent.com/"):

        _split = filterlist["url"].split("/")

        return {
            "repo": "/".join(_split[3:5]),
            "branch": _split[5],
            "files": [
                "/".join(_split[6:]),
            ],
        }


def _get_downloaded_fl_timestamp(
    filterlist: dict,
    downloaded_filterlists_fp: Path,
):
    with open(
        downloaded_filterlists_fp / f"{slug(filterlist)}.txt", encoding="utf-8"
    ) as f:

        downloaded_rules = f.readlines()

        timestamp = downloaded_rules[2].split(" = ")[1].strip()
        timestamp = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S.%f")

    return timestamp


def _does_published_filterlist_match_version(
    filterlist: dict,
    downloaded_filterlists_fp: Path,
    version_controls: dict,
    logger=logging.getLogger(__name__),
):
    with open(
        downloaded_filterlists_fp / f"{slug(filterlist)}.txt", encoding="utf-8"
    ) as f:

        downloaded_rules = f.readlines()

        timestamp = downloaded_rules[2].split(" = ")[1].strip()
        timestamp = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S.%f")

        commit = _get_latest_commit_until(
            version_controls[filterlist]["repo"],
            timestamp,
            branch=version_controls[filterlist]["branch"],
        )

        logger.info("%s: %s: %s", filterlist, commit["sha"], timestamp)

        filterlist_at_commit = _get_filterlist_content_at_commit(
            version_controls[filterlist]["repo"],
            commit["sha"],
            version_controls[filterlist]["files"],
        )

        filterlist_at_commit = filterlist_at_commit.split("\n")

        # remove comments
        filterlist_at_commit = {
            f.strip("\n\r\t ")
            for f in filterlist_at_commit
            if not f.startswith("!")
            and len(f.strip("\n\r\t ")) > 0
            and not f.startswith("[Adblock")
        }
        downloaded_filterlist = {
            f.strip("\n\r\t ")
            for f in downloaded_rules[3:]
            if not f.startswith("!")
            and len(f.strip("\n\r\t ")) > 0
            and not f.startswith("[Adblock")
        }

        # check if the downloaded version is a subset of the version at the commit
        return downloaded_filterlist.issubset(filterlist_at_commit)


def _track_rules_history_for_repo(
    repo: str,
    file_paths: Dict[str, List[str]],  # {file_path: [filterlists...]}
    watched_rules: Dict[str, List[str]],  # {file_path: [rules...]}
    filterlist_timestamp: Dict[str, datetime],
    timedeltas: List[timedelta],
    branch: str = "master",
):
    """
    Get the last seen timestamp for each rule in the watched_rules

    Args:
    - repo: str: repo name
    - file_paths: Dict[str, List[str]]: File paths to watch for each filterlist
    - watched_rules: Dict[str, List[str]]: Rules to watch for each filterlist
    - filterlist_timestamp: Dict[str, datetime]: Timestamp of the downloaded filterlist
    - timedeltas: List[timedelta]: List of timedeltas to check
    - branch: str: branch name
    """

    file_paths_set = set(file_paths.keys())
    filterlist = list(file_paths.values())[0][0]
    rules_last_seen = {rule: None for rule in watched_rules}
    rules_removed = {rule: False for rule in watched_rules}

    # approximation; just take the first timestamp to a participating filterlist
    download_timestamp = filterlist_timestamp[filterlist]

    for timedelta in tqdm(timedeltas, desc="Time deltas"):

        try:
            closest_commit = _get_latest_commit_until(
                repo, download_timestamp - timedelta, branch
            )
        except ValueError:
            # no commits before this date
            tqdm.write(f"No commits before {download_timestamp - timedelta}")
            break

        filterlists_content = _get_filterlist_content_at_commit(
            repo, closest_commit["sha"], file_paths_set, raise_error=False
        )

        filterlists_content = set(
            [r.strip("\n\r\t") for r in filterlists_content.split("\n")]
        )

        for rule in watched_rules:
            if rule in filterlists_content and not rules_removed[rule]:
                rules_last_seen[rule] = closest_commit["commit"]["committer"]["date"]
            else:
                rules_removed[rule] = True

    unseen = [k for k, v in rules_last_seen.items() if v is None]
    tqdm.write(f"Unseen rules: {len(unseen)}")

    tqdm.write(
        f"Min timestamp: {min([v for v in rules_last_seen.values() if v is not None])}"
    )

    # turn the last_seen of rules not removed into None
    for rule in rules_last_seen:
        if not rules_removed[rule]:
            rules_last_seen[rule] = None

    return rules_last_seen


def track_rules_history(
    filterlists: List[dict],
    timedeltas: List[timedelta],
    downloaded_filterlists_fp: Path,
    important_rules: pd.DataFrame,
    logger=logging.getLogger(__name__),
    health_check: bool = False,
):
    """
    This function tracks the history of the rules in filterlists from version control (e.g. github)

    Args:
    - filterlists: List[dict]: list of dictionaries from the configuration file for the adblocker, has a `version_control` key
    - timestamps: List[datetime]: list of timestamps for which to track the history
    - downloaded_filterlists_fp: Path: path to the downloaded filterlists
    - important_rules: pd.DataFrame: columns: rule, filterlists
    - logger: logging.Logger: logger object
    - health_check: bool: whether to perform a health check

    Returns:
    - pd.DataFrame: columns: rule, last_seen
    """

    # get the version control for each list
    version_controls = {
        f["name"]: _get_filterlist_version_control(f) for f in filterlists
    }
    filterlists_no_vc = [k for k, v in version_controls.items() if v is None]
    version_controls = {k: v for k, v in version_controls.items() if v is not None}

    logger.info(
        f"Filterlists without version control: N={len(filterlists_no_vc)} ({len(filterlists_no_vc)/len(filterlists)*100:.2f}%): {filterlists_no_vc}"
    )

    # group by repo and check file paths are reachable
    filepaths_to_watch = defaultdict(lambda: defaultdict(list))
    filterlist_timestamp = {}
    branches = defaultdict(str)
    # filepaths_to_watch: {repo: {filepath: [filterlists...]}}

    for filterlist, version_control in version_controls.items():

        branches[version_control["repo"]] = version_control["branch"]
        for file in version_control["files"]:
            if health_check and not _try_reach_github_fp(
                version_control["repo"],
                file,
                branch=version_control["branch"],
            ):
                raise ValueError(
                    f"Could not reach file: {file} in repo: {version_control['repo']}"
                )
            filepaths_to_watch[version_control["repo"]][file].append(filterlist)

    # verify that the downloaded version for each filterlist is not far of from the versioned one
    for filterlist in version_controls:
        if health_check and not _does_published_filterlist_match_version(
            filterlist,
            downloaded_filterlists_fp,
            version_controls,
            logger=logger,
        ):
            raise ValueError(
                f"Published filterlist does not match version: {filterlist}"
            )

        filterlist_timestamp[filterlist] = _get_downloaded_fl_timestamp(
            filterlist, downloaded_filterlists_fp
        )

    # track histories
    rules_last_seen = []

    for repo in tqdm(filepaths_to_watch, desc="Repos"):

        df = pd.DataFrame(columns=["rule", "last_seen"])

        repo_filterlists = sum(filepaths_to_watch[repo].values(), [])

        watched_rules = (
            important_rules[
                important_rules["filterlists"].apply(
                    lambda x: any(f in x for f in repo_filterlists)
                )
            ]["rule"]
            .apply(lambda x: json.loads(f'"{x}"').strip("\n\r\t "))
            .values
        )

        if len(watched_rules) == 0:
            tqdm.write(f"No important rules to watch for repo: {repo}")
            continue

        tqdm.write(f"{repo}:\t\t watching {len(watched_rules)} rules")

        _rules_last_seen = _track_rules_history_for_repo(
            repo,
            filepaths_to_watch[repo],
            watched_rules,
            filterlist_timestamp,
            timedeltas,
            branch=branches[repo],
        )

        os.makedirs("per_repo", exist_ok=True)
        _df = pd.DataFrame(_rules_last_seen.items(), columns=["rule", "last_seen"])
        df = pd.concat([df, _df])

        rules_last_seen.append(df)
        df.to_csv(f"per_repo/{slug(repo)}.csv", index=False)

    return pd.concat(rules_last_seen)


def scrape_commits_iter(
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
        f"https://api.github.com/repos/{repo}/commits",
        params={"per_page": url_args["per_page"], "page": page},
        headers={"Authorization": f"token {GITHUB_TOKEN}"},
    )

    tqdm.write(resp.request.url)

    if not _is_valid_commit_list_resp(resp):
        raise CommitListError(f"Invalid response: {resp} - {resp.text}")

    while _is_valid_commit_list_resp(resp):
        for commit in resp.json():

            if (
                date_limit
                and datetime.strptime(
                    commit["commit"]["author"]["date"], "%Y-%m-%dT%H:%M:%SZ"
                )
                < date_limit
            ):
                return

            yield commit

        if pages_limit and page >= pages_limit:
            return

        page += 1
        resp = requests.get(
            f"https://api.github.com/repos/{repo}/commits",
            params={"per_page": url_args["per_page"], "page": page},
            headers={"Authorization": f"token {GITHUB_TOKEN}"},
        )

        tqdm.write(resp.request.url)

        if not _is_valid_commit_list_resp(resp):
            raise CommitListError(f"Invalid response: {resp} - {resp.text}")


def unpack_commit(repo, commit_data):

    # each commit contains a list of files changed
    changes = []

    patches_resp = requests.get(
        f"https://github.com/{repo}/commit/{commit_data['sha']}.patch"
    )

    patch_set = PatchSet(StringIO(patches_resp.text))

    for patched_file in patch_set:
        file_path = patched_file.path  # file name

        for hunk in patched_file:

            # modified: if a removal directly followed by an addition
            # added and removed otherwise

            prev_removed = None

            for line in hunk:

                if line.is_added:

                    if prev_removed is not None:
                        changes.append(
                            {
                                "commit_id": commit_data["sha"],
                                "file_path": file_path,
                                "change_type": "modified",
                                "timestamp": commit_data["commit"]["author"]["date"],
                                "prev_rule": prev_removed.value,
                                "new_rule": line.value,
                            }
                        )

                    else:
                        changes.append(
                            {
                                "commit_id": commit_data["sha"],
                                "file_path": file_path,
                                "change_type": "added",
                                "timestamp": commit_data["commit"]["author"]["date"],
                                "prev_rule": None,
                                "new_rule": line.value,
                            }
                        )

                elif line.is_removed:
                    prev_removed = line

                else:
                    if prev_removed is not None:
                        changes.append(
                            {
                                "commit_id": commit_data["sha"],
                                "file_path": file_path,
                                "change_type": "removed",
                                "timestamp": commit_data["commit"]["author"]["date"],
                                "prev_rule": prev_removed.value,
                                "new_rule": None,
                            }
                        )

                    prev_removed = None

            if prev_removed is not None:
                changes.append(
                    {
                        "commit_id": commit_data["sha"],
                        "file_path": file_path,
                        "change_type": "removed",
                        "timestamp": commit_data["commit"]["author"]["date"],
                        "prev_rule": prev_removed.value,
                        "new_rule": None,
                    }
                )

    return changes


def scrape_commits(
    out_dir: Path, config: dict, force=False, pages_limit=None, date_limit=None
):

    cols = [
        "index",
        "commit_id",
        "prev_rule",
        "new_rule",
        "file_path",
        "change_type",
        "timestamp",
    ]

    out_csv = out_dir / "changes.csv"

    n_changes = 0

    with CSVExperimentLogger(out_csv, cols, mkdir=True, append=not force) as logger:

        page_start = len(logger.processed_ids) // config["params"]["per_page"] + 1

        n_changes += len(logger.processed_ids)

        index = 0

        for i, commit in tqdm(
            enumerate(
                scrape_commits_iter(
                    repo=config["repo"],
                    url_args=config.get("params"),
                    pages_limit=pages_limit,
                    date_limit=date_limit,
                    page_start=page_start,
                )
            )
        ):
            try:

                index = i + (page_start - 1) * config["params"]["per_page"]

                if logger.processed(str(index)):
                    continue

                for change in unpack_commit(config["repo"], commit):
                    logger.log({"index": n_changes, **change})
                    n_changes += 1

            except Exception as e:
                print(f"Error at index {index}: {e}")
                raise e