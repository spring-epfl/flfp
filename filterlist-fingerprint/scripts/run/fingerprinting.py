"""
Fingerprinting script for the targeted and general attack methods.
"""

import json
import logging
import os

import hydra
import numpy as np
import pandas as pd
from hydra.utils import to_absolute_path
from omegaconf import DictConfig
from scipy.stats import entropy

import fingerprint.general as filterlist_general
import fingerprint.general_rules as rules_general
import fingerprint.targeted as filterlist_targeted
import fingerprint.targeted_rules as rules_targeted

log = logging.getLogger(__name__)


@hydra.main(config_path="../../conf", config_name="fingerprint.conf", version_base=None)
def main(cfg: DictConfig = None) -> None:

    user_subscriptions = pd.read_csv(
        to_absolute_path(os.path.join(cfg.source_dir, "issues_confs_identified.csv"))
    )

    if cfg.method == "targeted":

        if cfg.encoding == "filterlist":

            fingerprints, listnames = filterlist_targeted.targeted_fingerprinting(
                user_subscriptions, col="identifiable_unique_lists"
            )

            rows = []

            for best_mask, history in fingerprints:

                rows.append(
                    {
                        "best_mask": json.dumps(best_mask),
                        "history": json.dumps(history),
                        "max_size": len(best_mask),
                        "min_anon_set": history[-1]["len_anon_set"],
                        "unique": history[-1]["len_anon_set"] == 1,
                    }
                )

            pd.DataFrame(rows).to_csv("fingerprints.csv", index=False)
            json.dump(listnames, open("filterlist_names.json", "w"))

        elif cfg.encoding == "rule":

            user_rules = pd.read_csv(
                to_absolute_path(os.path.join(cfg.source_dir, "user_rules.csv"))
            )
            rules_map = json.load(
                open(to_absolute_path(os.path.join(cfg.source_dir, "rule_id.json")))
            )

            fingerprints = rules_targeted.targeted_fingerprinting(user_rules, rules_map)

            rows = []

            for best_mask, history, _ in fingerprints:

                # if the user failed to be fingerprinted, skip
                if len(history) == 0:
                    continue

                rows.append(
                    {
                        "best_mask": json.dumps(best_mask),
                        "history": json.dumps(history),
                        "max_size": len(best_mask),
                        "min_anon_set": history[-1]["len_anon_set"],
                        "unique": history[-1]["len_anon_set"] == 1,
                    }
                )

            pd.DataFrame(rows).to_csv("fingerprints.csv", index=False)

        else:
            raise ValueError(f"Unknown encoding: {cfg.encoding}")

    elif cfg.method == "general":

        if cfg.encoding == "filterlist":
            (best_mask, anon_sets, best_metric), listnames = (
                filterlist_general.general_fingerprinting(
                    user_subscriptions,
                    cfg.general.max_size,
                    col="identifiable_unique_lists",
                )
            )

            anon_set_sizes = np.array([len(s) for s in anon_sets])

            out = {
                "best_mask": best_mask,
                "best_metric": best_metric,
                "anon_sets": anon_sets,
                "stats": {
                    "best_mask_size": len(best_mask),
                    "n_anon_sets": len(anon_sets),
                    "max_anon_set_size": int(np.max(anon_set_sizes)),
                    "mean_anon_set_size": np.mean(anon_set_sizes),
                    "std_anon_set_size": np.std(anon_set_sizes),
                    "median_anon_set_size": int(np.median(anon_set_sizes)),
                    "anon_set_entropy": entropy(anon_set_sizes)
                    / np.log(len(user_subscriptions)),
                },
            }

            log.info(f"Stats:")
            for k, v in out["stats"].items():
                log.info(f"  {k}: {v}")

            json.dump(out, open("fingerprint.json", "w"))
            json.dump(listnames, open("filterlist_names.json", "w"))

        elif cfg.encoding == "rule":

            user_rules = pd.read_csv(
                to_absolute_path(os.path.join(cfg.source_dir, "user_rules.csv"))
            )
            rules_map = json.load(
                open(to_absolute_path(os.path.join(cfg.source_dir, "rule_id.json")))
            )

            (best_mask, anon_sets, best_metric) = rules_general.general_fingerprinting(
                user_rules, rules_map, cfg.general.max_size
            )

            anon_set_sizes = np.array([len(s) for s in anon_sets])

            out = {
                "best_mask": best_mask,
                "best_metric": best_metric,
                "anon_sets": anon_sets,
                "stats": {
                    "best_mask_size": len(best_mask),
                    "n_anon_sets": len(anon_sets),
                    "max_anon_set_size": int(np.max(anon_set_sizes)),
                    "mean_anon_set_size": np.mean(anon_set_sizes),
                    "std_anon_set_size": np.std(anon_set_sizes),
                    "median_anon_set_size": int(np.median(anon_set_sizes)),
                    "anon_set_entropy": entropy(anon_set_sizes)
                    / np.log(len(user_rules)),
                },
            }

            log.info(f"Stats:")
            for k, v in out["stats"].items():
                log.info(f"  {k}: {v}")

            json.dump(out, open("fingerprint.json", "w"))

    else:
        raise ValueError(f"Unknown attack method: {cfg.method}")


if __name__ == "__main__":
    main()
