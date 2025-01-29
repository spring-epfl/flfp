from datetime import datetime, timezone
import os
import yaml
import pandas as pd
from pathlib import Path
import sys
import json
from tabulate import tabulate
from colorama import Fore, just_fix_windows_console

just_fix_windows_console()

__dir__ = Path(os.path.abspath(os.path.dirname(__file__)))
sys.path.append(str(__dir__.parent))

CURR_DIR = __dir__

import stats
import utils
from matplotlib import pyplot as plt
import numpy as np


def Title(text):
    print(Fore.RED + text + Fore.RESET)

    HSpace()


def Header(text, mt=2):

    HSpace(mt)

    print(Fore.BLUE + text + Fore.RESET)
    print("=" * len(text))


def HSpace(n=1):
    for _ in range(n):
        print()


def Link(text):
    print(Fore.GREEN + text + Fore.RESET)


CONF_DIR = (__dir__ / Path("../../conf/")).resolve()
PAPER_FIGURES_DIR = (__dir__ / Path("./figures/")).resolve()
DATA_DIR = (__dir__ / Path("../../data/")).resolve()
ISSUES_DIR = (__dir__ / Path("../../data/issues/")).resolve()
PAPER_FIGURES_DIR.mkdir(parents=True, exist_ok=True)


#######################
#### CONFIGURABLE PATHS
#######################

# Forum Issues Paths
UBLOCK_CONFS_DIR = ISSUES_DIR / "ublock/2024-06-11/issues_confs.csv"
UBLOCK_DEDUP_CONFS_DIR = ISSUES_DIR / "ublock/2024-06-14:dedup/issues_confs.csv"
ADGUARD_CONFS_DIR = ISSUES_DIR / "adguard/2024-04-24/issues_confs.csv"

# Stability Commits Paths
ADGUARD_COMMITS_FP = DATA_DIR / "commits/adguard/parse/2024-04-27/changes.csv"
UBLOCK_COMMITS_FP = DATA_DIR / "commits/ublock/parse/2024-04-29/changes.csv"

ADGUARD_RULE_LAST_SEEN_DOWNLOAD_TIMESTAMP = datetime(2024, 3, 29, tzinfo=timezone.utc)
ADGUARD_RULE_LAST_SEEN_FP = (
    DATA_DIR / "commits/adguard/history/2024-03-29/rules_last_seen.csv"
)

UBLOCK_RULE_LAST_SEEN_DOWNLOAD_TIMESTAMP = datetime(2024, 4, 24, tzinfo=timezone.utc)
UBLOCK_RULE_LAST_SEEN_FP = (
    DATA_DIR / "commits/ublock/history/2024-04-24/rules_last_seen.csv"
)