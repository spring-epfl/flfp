"""
Script to run stability analysis on filter lists
"""

import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import hydra
import pandas as pd
from hydra.utils import to_absolute_path
from filterlist_parser.rules import parse_rules
from omegaconf import DictConfig
from tqdm import tqdm

from gh_scraper import scrape_commits

logger = logging.getLogger(__name__)

tqdm.pandas()


def parse_commit_lists(commits_fp: Path):

    # expand prev_rule to all features of prev_rule
    # expand next_rule to all features of next_rule

    commits_df = pd.read_csv(commits_fp)

    # remove rows where the file_path does not end with .txt
    commits_df = commits_df[commits_df["file_path"].str.endswith(".txt")]

    non_empty_prev_commits, non_empty_prev_commits_i = [], []
    non_empty_new_commits, non_empty_new_commits_i = [], []

    for i, row in tqdm(commits_df.iterrows(), total=len(commits_df)):

        index = row["index"]
        prev_rule = row["prev_rule"]
        new_rule = row["new_rule"]

        if isinstance(prev_rule, str) and len(prev_rule) > 0:
            non_empty_prev_commits.append(prev_rule)
            non_empty_prev_commits_i.append(index)

        if isinstance(new_rule, str) and len(new_rule) > 0:
            non_empty_new_commits.append(new_rule)
            non_empty_new_commits_i.append(index)

    # parse_by_rule because sending long list of rules overflows npm
    non_empty_prev_commits = parse_rules(
        non_empty_prev_commits, parse_by_rule=True, parallel=True
    ).drop(columns=["rule", "rule_regex"])
    non_empty_new_commits = parse_rules(
        non_empty_new_commits, parse_by_rule=True, parallel=True
    ).drop(columns=["rule", "rule_regex"])

    # add the index back
    non_empty_prev_commits["index"] = non_empty_prev_commits_i
    non_empty_new_commits["index"] = non_empty_new_commits_i

    # merge the two dataframes back to the original
    merged_commits_df = pd.merge(
        commits_df,
        non_empty_prev_commits,
        on="index",
        how="left",
        suffixes=("", "_prev"),
    )
    merged_commits_df = pd.merge(
        merged_commits_df,
        non_empty_new_commits,
        on="index",
        how="left",
        suffixes=("", "_new"),
    )

    # transform all NaNs to None
    merged_commits_df = merged_commits_df.where(pd.notnull(merged_commits_df), None)

    # json encode the rules because they cause issues when writing them
    merged_commits_df["prev_rule"] = merged_commits_df["prev_rule"].apply(
        lambda x: x if x is None else json.dumps(x)
    )
    merged_commits_df["new_rule"] = merged_commits_df["new_rule"].apply(
        lambda x: x if x is None else json.dumps(x)
    )

    return merged_commits_df


def get_important_rules_from_all_attacks(
    attacks_dir: Path, attack_type: Optional[str] = None
) -> pd.DataFrame:
    """Collects the important rules from all attacks

    Args:
        attacks_dir (Path): Path to the directory containing the attack summaries
        attack_type (str, optional): Type of attack to consider

    Returns:
        pd.DataFrame: DataFrame containing the important rules. The Dataframe is also saved to a file `important_rules.csv` in the current directory.
        The DataFrame has two columns: rule, filterlists. The filterlists column contains a list of filterlists that the rule is present in.
    """

    # if the file already exists, just read it
    if os.path.exists("important_rules.csv"):
        return pd.read_csv(
            "important_rules.csv", converters={"filterlists": json.loads}
        )

    # pattern to match the important rules file depending on the attack type
    important_rule_pattern = "**/summary/important_rules.csv"
    if attack_type == "general":
        important_rule_pattern = "**/summary/general_important_rules.csv"
    elif attack_type == "targeted":
        important_rule_pattern = "**/summary/targeted_important_rules.csv"

    def _process_rule_df(rule_df):
        """
        Transform the rule_df to a single row DataFrame with the filterlists column
        as a list of unique filterlists in JSON format.
        """

        filterlists = rule_df.filterlists.values
        filterlists = list(set(sum(filterlists, [])))

        return pd.Series({"filterlists": json.dumps(filterlists)})

    important_rules = []

    # get the important rules from all attacks folders
    for attack_rules_fp in tqdm(attacks_dir.glob(important_rule_pattern)):
        important_rules.append(
            pd.read_csv(
                attack_rules_fp,
                converters={
                    "filterlists": lambda s: s.strip("[]").replace("'", "").split(", ")
                },
            )
        )

    important_rules = (
        pd.concat(important_rules).groupby("rule").progress_apply(_process_rule_df)
    )

    important_rules.reset_index(inplace=True)
    important_rules.to_csv("important_rules.csv", index=False)
    return important_rules


@hydra.main(config_path="../../conf", config_name="commits.conf", version_base=None)
def main(cfg: DictConfig = None) -> None:

    if cfg.action == "scrape":
        scrape_commits.scrape_commits(
            out_dir=Path(os.getcwd()),
            config=cfg.forum,
            force=cfg.overwrite,
            pages_limit=cfg.pages_limit,
            date_limit=(
                datetime.strptime(cfg.date_limit, "%Y-%m-%dT%H:%M:%SZ")
                if cfg.date_limit
                else None
            ),
        )

    elif cfg.action == "parse":
        commits = parse_commit_lists(
            Path(to_absolute_path(cfg.parse.scrape_fp)) / "changes.csv"
        )
        commits.to_csv("changes.csv", index=False)

    elif cfg.action == "history":

        # get the filter rules to watch from attack summaries
        important_rules = get_important_rules_from_all_attacks(
            Path(to_absolute_path(cfg.history.attacks_parent_dir)),
            attack_type=cfg.history.attack_type,
        )

        # in the conf we get date deltas in days
        timedeltas = [timedelta(days=0)]

        for delta_days in cfg.history.deltas:
            timedeltas.append(timedeltas[-1] + timedelta(days=delta_days))

        rules_last_seen = scrape_commits.track_rules_history(
            cfg.filterlists.list,
            timedeltas,
            Path(to_absolute_path(cfg.history.downloads_dir)),
            important_rules,
            logger=logger,
        )

        rules_last_seen.to_csv("rules_last_seen.csv", index=False)

    else:
        raise ValueError(f"Unknown action: {cfg.action}")


if __name__ == "__main__":
    main()
