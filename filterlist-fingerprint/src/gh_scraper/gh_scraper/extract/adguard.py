from datetime import datetime
import json
import os
from typing import Optional, override
from pathlib import Path
from gh_scraper.extract.common import OS_PREFIXES, BaseExtractor
import pandas as pd

# Bot issues are considered unique

COLS = [
    "submitted_by_bot",
    "adguard_product",
    "system_version",
    "system_os",
    "browser",
    "stealth_mode",
]


class AdguardExtractor(BaseExtractor):

    @staticmethod
    def get_os(system_version: str) -> str:
        
        if system_version is None:
            return None

        for prefix in OS_PREFIXES:
            if system_version.lower().startswith(prefix):
                return OS_PREFIXES[prefix]

        return None

    @override
    def is_valid_issue_body(self, body: str) -> bool:
        return "### System configuration" in body and "Filters" in body

    @override
    def parse_conf_dict(self, body: str) -> dict:
        """

        example body:

        bla bla

        ### System configuration

        Information | Value
        --- | ---
        AdGuard product: | AdGuard Browser Extension v4.3.13
        System version: | Android 13
        Browser: | Chrome
        Stealth mode options: | Strip URLs from tracking parameters, <br>Hide your search queries, <br>Send Do-Not-Track header, <br>Remove X-Client-Data header from HTTP requests, <br>Self-destructing third-party cookies (2880), <br>Block trackers
        Stealth mode: | Strip URLs from tracking parameters, <br>Hide your search queries, <br>Send Do-Not-Track header, <br>Remove X-Client-Data header from HTTP requests, <br>Self-destructing third-party cookies (2880), <br>Block trackers
        Filters: | <b>Ad Blocking:</b><br/>AdGuard Base, <br/>AdGuard Mobile Ads<br/><br/><b>Privacy:</b><br/>AdGuard Tracking Protection, <br/>AdGuard URL Tracking, <br/>Legitimate URL Shortener<br/><br/><b>Annoyances:</b><br/>AdGuard Cookie Notices, <br/>AdGuard Popups, <br/>AdGuard Mobile App Banners, <br/>AdGuard Other Annoyances, <br/>AdGuard Widgets<br/><br/><b>Language-specific:</b><br/>Official Polish filters for AdBlock, uBlock Origin & AdGuard, <br/>Polish Anti Adblock Filters
        """

        conf = {}

        lines = body.split("\n")

        # get all keys from table
        table_started = False
        for line in lines:

            if "Information" in line and ("Value" in line or "value" in line):
                table_started = True
                continue

            if table_started:
                if line.strip() == "":
                    continue
                args = line.split("|")
                if len(args) != 2:
                    continue

                if args[0].strip() == "---":
                    continue

                key = args[0].strip()[:-1]  # [-1] to remove the ":"
                value = args[1].strip()

                conf[key] = value

        return True, conf

    @override
    def parse_filterlists(self, body: str, conf: dict):

        filters = []
        for line in conf["Filters"].split("<br/>"):

            if "<b>" in line or line.strip() == "":
                continue

            _filter = line.strip()

            # remove the last comma
            if _filter[-1] == ",":
                _filter = _filter[:-1]

            # replacing creeping html tags due to bad formatting
            _filter.replace("</details>", "")

            filters.append(_filter)

        return True, filters

    @override
    def format_output(self, index: int, issue_data: dict) -> dict:

        issue_out = super().format_output(index, issue_data)

        issue_out |= {col: None for col in COLS}

        if issue_out["valid"]:
            
            conf_dict = json.loads(issue_out["conf_dict"])

            issue_out["adguard_product"] = conf_dict.get(
                "AdGuard product", None
            )
            issue_out["system_version"] = conf_dict.get(
                "System version", None
            )
            issue_out["system_os"] = AdguardExtractor.get_os(
                issue_out["system_version"]
            )
            issue_out["browser"] = conf_dict.get("Browser", None)
            issue_out["stealth_mode"] = conf_dict.get("Stealth mode", None)

        return issue_out

def scrape_confs(
    out_dir: Path,
    config: dict,
    pages_limit: Optional[int] = None,
    date_limit: Optional[datetime] = None,
    overwrite: bool = False,
):
    out_csv = out_dir / "issues_confs.csv"
    if overwrite and out_csv.exists():
        os.remove(out_csv)

    extractor = AdguardExtractor(
        out_dir=out_dir,
        config=config,
        cols=COLS,
        pages_limit=pages_limit,
        date_limit=date_limit,
    )

    extractor.scrape_confs()


def remove_duplicates_submitted_by_bot(adguard_confs: pd.DataFrame) -> pd.DataFrame:
    """
    Remove duplicates issues submitted by bot
    """
    consecutive_duplicates = []

    for i in range(1, len(adguard_confs)):

        if (
            adguard_confs.iloc[i - 1]["browser"] == adguard_confs.iloc[i]["browser"]
            and adguard_confs.iloc[i - 1]["system_version"]
            == adguard_confs.iloc[i]["system_version"]
            and adguard_confs.iloc[i - 1]["stealth_mode"]
            == adguard_confs.iloc[i]["stealth_mode"]
            and adguard_confs.iloc[i - 1]["filters"] == adguard_confs.iloc[i]["filters"]
        ):

            consecutive_duplicates.append(i)

    return adguard_confs.drop(consecutive_duplicates)
