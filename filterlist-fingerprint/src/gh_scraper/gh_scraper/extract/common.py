from abc import abstractmethod
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
import traceback
from typing import Optional, Tuple

from gh_scraper.logging import CSVExperimentLogger
from gh_scraper.scrape_issues import scrape_issues_iter
import pandas as pd
from tqdm import tqdm

DEFAULT_COLS = [
    "i",
    "issue",
    "title",
    "author",
    "labels",
    "created_at",
    "is_closed",
    "body",
    "conf_dict",
    "valid",
    "filters",
]

BROWSERS = {
    "[ff": "firefox",
    "ff ": "firefox",
    "firefox": "firefox",
    "chrome": "chrome",
    "edge": "edge",
    "safari": "safari",
    "opera": "opera",
    "brave": "brave",
    "vivaldi": "vivaldi",
    "ie": "ie",
    "chromium": "chromium",
    "yandex": "yandex",
    "uc": "uc",
    "samsung": "samsung",
    "maxthon": "maxthon",
    "librewolf": "librewolf",
    "firefox mobile": "firefox mobile",
    "chrome mobile": "chrome mobile",
    "edge mobile": "edge mobile",
    "safari mobile": "safari mobile",
    "opera mobile": "opera mobile",
    "brave mobile": "brave mobile",
    "vivaldi mobile": "vivaldi mobile",
    "ie mobile": "ie mobile",
    "chromium mobile": "chromium mobile",
    "yandex mobile": "yandex mobile",
    "uc mobile": "uc mobile",
    "samsung mobile": "samsung mobile",
    "maxthon mobile": "maxthon mobile",
}

OS_PREFIXES = {
    "win": "Windows",
    "mac": "MacOS",
    "ios": "iOS",
    "chromeos": "ChromeOS",
    "chrome os": "ChromeOS",
    "andr": "Android",
    "linux": "Linux",
    "ubuntu": "Ubuntu",
    "fedora": "Fedora",
    "debian": "Debian",
    "centos": "CentOS",
    "redhat": "RedHat",
    "suse": "SUSE",
    "gentoo": "Gentoo",
    "arch": "Arch",
    "slackware": "Slackware",
    "freebsd": "FreeBSD",
    "openbsd": "OpenBSD",
    "netbsd": "NetBSD",
    "dragonfly": "DragonFly",
    "solaris": "Solaris",
    "illumos": "Illumos",
    "openindiana": "OpenIndiana",
    "smartos": "SmartOS",
    "aix": "AIX",
    "hp-ux": "HP-UX",
    "irix": "IRIX",
    "osf1": "OSF1",
    "tru64": "Tru64",
    "unix": "Unix",
    "other": "Other",
    "windows10": "Windows",
    "chromium": "Chromium",
    
}


class BaseExtractor:

    def __init__(
        self,
        out_dir: Path,
        config: dict,
        cols: list,
        pages_limit: Optional[int] = None,
        date_limit: Optional[datetime] = None,
        exit_on_error: bool = False,
        prev_out_dir: Optional[Path] = None,
    ):

        self.out_dir = out_dir
        self.config = config
        self.pages_limit = pages_limit
        self.date_limit = date_limit
        self.cols = DEFAULT_COLS + (list(set(cols) - set(DEFAULT_COLS)) if cols else [])

        self.exit_on_error = exit_on_error
        self.prev_out_dir = prev_out_dir

    @abstractmethod
    def is_valid_issue_body(self, body: str) -> bool:
        raise NotImplementedError(
            "You must implement the is_valid_issue_body method in your subclass"
        )

    @abstractmethod
    def parse_conf_dict(self, body: str) -> Tuple[bool, Optional[dict]]:
        raise NotImplementedError(
            "You must implement the parse_conf_dict method in your subclass"
        )

    @abstractmethod
    def parse_filterlists(
        self, body: str, conf: Optional[dict] = None
    ) -> Tuple[bool, Optional[dict]]:
        raise NotImplementedError(
            "You must implement the parse_filterlists method in your subclass"
        )

    def format_output(self, index: int, issue_data: dict):
        issue_out = {
            "i": index,
            "issue": issue_data["number"],
            "title": issue_data["title"],
            "author": sha256(issue_data["user"]["login"].encode()).hexdigest(),
            "labels": json.dumps([label["name"] for label in issue_data["labels"]]),
            "created_at": issue_data["created_at"],
            "is_closed": issue_data["state"] == "closed",
            "body": issue_data["body"],
            "conf_dict": None,
            "filters": None,
            "valid": False,
        }

        if issue_data["body"] and self.is_valid_issue_body(issue_data["body"]):
            is_valid, conf = self.parse_conf_dict(issue_data["body"])

            if is_valid:
                issue_out["conf_dict"] = json.dumps(conf)
                is_valid, _filterlists = self.parse_filterlists(
                    issue_data["body"], conf
                )

                if is_valid:
                    issue_out["valid"] = True
                    issue_out["filters"] = json.dumps(_filterlists)

        return issue_out

    @abstractmethod
    def update_output(self, issue_row: pd.Series) -> pd.Series:
        return issue_row

    def scrape_confs(self):

        out_csv = self.out_dir / "issues_confs.csv"

        force = self.config.get("force", False)

        with CSVExperimentLogger(
            out_csv, self.cols, mkdir=True, append=not force
        ) as logger:

            page_start = (
                len(logger.processed_ids) // self.config["params"]["per_page"] + 1
            )

            index = 0

            for i, issue in tqdm(
                enumerate(
                    scrape_issues_iter(
                        repo=self.config["repo"],
                        url_args=self.config.get("params"),
                        pages_limit=self.pages_limit,
                        date_limit=self.date_limit,
                        page_start=page_start,
                    )
                )
            ):
                try:

                    index = i + (page_start - 1) * self.config["params"]["per_page"]

                    if logger.processed(str(index)):
                        continue

                    issue_out = self.format_output(index, issue)
    
                    logger.log(issue_out)

                except Exception as e:
                    print(f"Error at index {index}: {e}")
                    traceback.print_exc()
                    if self.exit_on_error:
                        raise e

    def update_confs(self):

        prev_csv = pd.read_csv(self.prev_out_dir / "issues_confs.csv")

        out_csv = self.out_dir / "issues_confs.csv"

        with CSVExperimentLogger(
            out_csv, self.cols, mkdir=True, append=False
        ) as logger:

            index = 0
            try:
                for i, issue in tqdm(prev_csv.iterrows()):
                    index = issue.i
                    issue_out = self.update_output(issue)
                    logger.log(issue_out.to_dict())

            except Exception as e:
                print(f"Error at index {index}: {e}")
                if self.exit_on_error:
                    raise e
