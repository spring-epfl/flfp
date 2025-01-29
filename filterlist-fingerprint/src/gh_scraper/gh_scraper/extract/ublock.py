from datetime import datetime
import json
import math
import re
from typing import Optional, override
from pathlib import Path
from csv import writer, reader, DictWriter
from gh_scraper.extract.common import DEFAULT_COLS, BaseExtractor, BROWSERS, OS_PREFIXES
from gh_scraper.logging import CSVExperimentLogger
import numpy as np
import pandas as pd

from tqdm import tqdm
from ..scrape_issues import scrape_issues_iter, IssueListError

import yaml


COLS = [
    # No columns to add
    "browser",
    "browser_origin",
    "system_os",
]

# Got this from trying to post an issue with default settings
# limitations is trying to make sure it is historically similar to back then
DEFAULT_CONF = """
listset (total-discarded, last-updated):
 default:
  user-filters: 0-0, never
  easylist: 82657-16, now
  easyprivacy: 50369-8, now
  plowe-0: 3772-1184, now
  ublock-badware: 7848-147, now
  ublock-filters: 37535-357, now
  ublock-privacy: 763-6, now
  ublock-quick-fixes: 203-28, now
  ublock-unbreak: 2250-33, now
  urlhaus-1: 7770-0, now
"""


def _clean_yaml(yaml_str: str) -> str:

    # if a key is [key]: value, remove the brackets
    yaml_str = re.sub(r"\[([\w\s]+)\]:", r"\1:", yaml_str)

    # if the value starts with * or ?, wrap it in quotes
    yaml_str = re.sub(r"(\w+): ([\*\?][\w \*]*)", r"\1: '\2'", yaml_str)

    # if the value contains { or } or < or >, wrap it in quotes
    yaml_str = re.sub(r"(\w+): ([\w\s]*[\{<][\S\s]*)", r"\1: '\2'", yaml_str)

    return yaml_str


class UblockExtractor(BaseExtractor):

    def get_os(self, issue: dict) -> str:

        if not isinstance(issue["body"], str):
            return None

        lines_lower = [
            line.lower()
            for line in issue["body"].split("\n")
            if line.strip() not in ["", "\n", "\r"]
        ]

        for os in OS_PREFIXES.values():

            os = os.lower()

            if os in ["chromium", "other"]:
                continue

            os_keywords = rf"([^\S]|[:])+{os}|^{os}"
            if any(re.search(os_keywords, line) for line in lines_lower):
                return os

        return None

    def get_browser(self, issue: dict) -> str:

        # where can the browser exist

        if not isinstance(issue["conf_dict"], str) and not isinstance(
            issue["conf_dict"], dict
        ):
            return None, None

        conf_dict = (
            issue["conf_dict"]
            if isinstance(issue["conf_dict"], dict)
            else json.loads(issue["conf_dict"])
        )

        conf_keys_lower = [key.lower() for key in conf_dict.keys()]

        lines_lower = [
            line.lower()
            for line in issue["body"].split("\n")
            if line.strip() not in ["", "\n", "\r"]
        ]

        for browser, browser_val in BROWSERS.items():

            # 1. in the yaml conf dict
            if browser in conf_keys_lower:
                return browser_val, "conf_dict"

        for browser, browser_val in BROWSERS.items():

            # 2. after headers
            #  - "Browser/version"
            #  - "### Browser name and version"

            escaped_browser = re.escape(browser)
            browser_keywords = rf"{escaped_browser}:|{escaped_browser}\n|{escaped_browser} version|version: {escaped_browser}| {escaped_browser}[\s]*|{escaped_browser} "

            if any(re.search(browser_keywords, line) for line in lines_lower):
                return browser_val, "body"

        return None, None

    @override
    def is_valid_issue_body(self, body: str) -> bool:

        patterns = [
            # pattern that matches <summary>Details</summary> ... ```yaml ...``` and could be multiline
            r"<summary>Details</summary>[\s\S]+?```yaml[\s\S]+?```",
            # <details> ```yaml ...``` </details>
            r"<details>[\s\S]*?```yaml[\s\S]+?```[\s\S]*?</details>",
            # ### Settings ... ```yaml ...``` and could be multiline
            r"### Settings[\s\S]+?```yaml[\s\S]+?```",
            # Settings Default
            r"Settings[\s\n\r]*Default",
        ]

        if any(re.search(pattern, body) for pattern in patterns):
            return True

        return False

    @override
    def parse_conf_dict(self, body: str) -> dict:

        # handle the edge case for older issues that simply mention Settings Default
        pattern = r"Settings[\s\n\r]*Default"

        if re.search(pattern, body):
            return True, yaml.safe_load(_clean_yaml(DEFAULT_CONF))

        # must come after <summary>Details</summary>
        details_index = (
            body.index("<details>")
            if "<details>" in body
            else body.index("### Settings")
        )

        # get the yaml part
        yaml_part = body[details_index:]
        yaml_part = yaml_part.split("```yaml")[1].split("```")[0]

        if len(yaml_part.strip(" \n\r")) == 0:
            return False, None

        if "listset" not in yaml_part.lower():
            return False, None

        try:
            conf: dict = yaml.safe_load(_clean_yaml(yaml_part))
        except Exception as e:
            return False, None

        if len(conf) == 0:
            return False, None

        return True, conf

    @override
    def parse_filterlists(self, body: str, conf: dict) -> list:

        # handle the edge case for older issues that simply mention Settings Default

        keys = conf.keys()
        filterlist_key = [key for key in keys if "listset" in key.lower()]

        if len(filterlist_key) == 0:
            return False, None

        filterlist_key = filterlist_key[0]

        if not isinstance(conf[filterlist_key], dict):
            return False, None

        # get the keys for each sub-dict
        lists = []

        for key in conf[filterlist_key]:

            # if the key is 'removed' it is not active so don't include it
            if key == "removed":
                continue

            if isinstance(conf[filterlist_key][key], dict):
                lists.extend(conf[filterlist_key][key].keys())

        # remove the user-filters key because it's redacted
        if "user-filters" in lists:
            lists.remove("user-filters")

        # TODO: normalize the list names like adguard
        return True, lists

    @override
    def format_output(self, index: int, issue_data: dict) -> dict:
        issue_out = super().format_output(index, issue_data)

        issue_out |= {col: None for col in COLS}

        if issue_out["valid"]:
            issue_out["browser"], issue_out["browser_origin"] = self.get_browser(
                issue_out
            )

        return issue_out

    @override
    def update_output(self, issue_row: pd.Series) -> pd.Series:

        # if "browser" not in issue_row or issue_row["browser"] is None:
        issue_row["browser"], issue_row["browser_origin"] = self.get_browser(issue_row)

        if "system_os" not in issue_row or issue_row["system_os"] is None:
            issue_row["system_os"] = self.get_os(issue_row)

        return issue_row


def scrape_confs(
    out_dir: Path,
    config: dict,
    pages_limit: Optional[int] = None,
    date_limit: Optional[datetime] = None,
    prev_out_dir: Optional[str] = None,
):

    if prev_out_dir is not None:
        prev_out_dir = Path(prev_out_dir)

    extractor = UblockExtractor(
        out_dir,
        config,
        COLS,
        pages_limit,
        date_limit,
        exit_on_error=True,
        prev_out_dir=prev_out_dir,
    )

    if prev_out_dir is not None:
        return extractor.update_confs()

    else:
        return extractor.scrape_confs()
