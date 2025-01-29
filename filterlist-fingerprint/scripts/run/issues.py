import os
from datetime import datetime
from pathlib import Path

import hydra
import pandas as pd
from hydra.utils import to_absolute_path
from omegaconf import DictConfig

from gh_scraper.extract import adguard as extract_adguard
from gh_scraper.extract import ublock as extract_ublock


@hydra.main(config_path="../../conf", config_name="issues.conf", version_base=None)
def main(cfg: DictConfig = None) -> None:

    if cfg.forum.name == "adguard":
        extract_adguard.scrape_confs(
            out_dir=Path(os.getcwd()),
            config=cfg.forum,
            pages_limit=cfg.pages_limit,
            date_limit=datetime.strptime(cfg.date_limit, "%Y-%m-%dT%H:%M:%SZ") if cfg.date_limit else None,
            overwrite=cfg.overwrite,
        )

        issues = pd.read_csv("issues_confs.csv")
        issues_no_bot_dups = extract_adguard.remove_duplicates_submitted_by_bot(issues)

        issues.to_csv("issues_confs_raw.csv", index=False)
        issues_no_bot_dups.to_csv("issues_confs.csv", index=False)

    elif cfg.forum.name == "ublock":

        if not cfg.forum.get("dedup_from", None):

            extract_ublock.scrape_confs(
                out_dir=Path(os.getcwd()),
                config=cfg.forum,
                pages_limit=cfg.pages_limit,
                date_limit=(
                    datetime.strptime(cfg.date_limit, "%Y-%m-%d")
                    if cfg.date_limit
                    else None
                ),
                prev_out_dir=cfg.get("prev_out_dir", None),
            )

        else:

            prev_issues = pd.read_csv(
                Path(to_absolute_path(cfg.forum.dedup_from)) / "issues_confs.csv"
            )
            prev_issues = prev_issues[prev_issues.valid]

            new_issues = prev_issues.groupby("author").apply(
                lambda x: x.sort_values("created_at", ascending=False).iloc[0]
            )

            new_issues.to_csv("issues_confs.csv", index=False)

    else:
        raise ValueError(f"Unknown forum name: {cfg.forum.name}")
    
    print("Issues extraction completed.")


if __name__ == "__main__":
    main()
