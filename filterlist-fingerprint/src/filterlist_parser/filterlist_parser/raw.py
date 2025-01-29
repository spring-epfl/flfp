"""Functions for downloading and parsing adguard's filterlists"""

from datetime import datetime
from pathlib import Path
from typing import Iterable

import requests

from filterlist_parser.utils import slug
import tqdm
import yaml


def get_adguard_lists() -> list[dict]:
    """
    Get a list of available filterlists from adguard's filterlist registry

    Returns:
        filters: list of filterlists with name and url
    """

    resp = requests.get(
        "https://raw.githubusercontent.com/AdguardTeam/FiltersRegistry/master/report.txt"
    )
    resp.raise_for_status()

    filters = []

    for _filter in resp.text.split("---------------------------"):

        if "Filter ID: " not in _filter:
            continue

        filter_name = _filter.split("Filter name: ")[1].split("\n")[0].strip()

        if "(Obsolete)" in filter_name:
            continue

        filters.append(
            {
                "name": filter_name,
                "url": _filter.split("URL: ")[1].split("\n")[0].strip(),
            }
        )

    filters_yaml = yaml.dump(filters)

    print(filters_yaml)

    return filters


def download_list(url: str, out: Path) -> None:
    """
    Download a filterlist to a file

    Args:
        url: url of the filterlist
        out: path to the output file
    """

    resp = requests.get(url)
    resp.raise_for_status()

    with open(out, "w") as f:
        f.write("! CONFIG\n")
        f.write("! url = " + url + "\n")
        f.write("! timestamp = " + datetime.now().isoformat() + "\n")
        f.write("\n")

        f.write(resp.text)


def download_lists(filterlists: list[dict], out_dir: Path) -> None:
    """
    Download a list of filterlists to a directory

    Args:
        filterlists: list of filterlists with name and url
        out_dir: directory to save the filterlists
    """

    for filterlist in tqdm.tqdm(filterlists):
        out = out_dir / f"{slug(filterlist["name"])}.txt"

        if out.exists():
            continue

        download_list(filterlist["url"], out)


def load_rules_str(name: str, filterlist_dir: Path) -> str:
    """
    Load the rules from a filterlist file to a string

    Args:
        name: name of the filterlist
        filterlist_dir: directory of the filterlists

    Returns:
        out: string of the rules
    """

    out = ""

    for line in load_rules_iter(name, filterlist_dir):
        out += line

    return out


def load_rules_iter(name: str, filterlist_dir: Path) -> Iterable[str]:
    """
    Load the rules from a filterlist file as an iterator

    Args:
        name: name of the filterlist
        filterlist_dir: directory of the filterlists

    Returns:
        out: iterator of the rules
    """

    with open(filterlist_dir / (slug(name) + ".txt")) as f:
        while True:

            line = f.readline()
            if not line:
                break

            # if a comment
            if (
                line.startswith("!")
                or line.startswith("# ")
                or line.startswith("[Adblock")
            ):
                continue

            # if an empty / line
            if len(line) < 2:
                continue

            yield line
