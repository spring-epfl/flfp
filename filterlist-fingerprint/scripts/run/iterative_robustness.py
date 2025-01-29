import json
import logging
import os
from typing import Optional

import hydra
import numpy as np
import pandas as pd
from hydra.utils import to_absolute_path
from omegaconf import DictConfig
from scipy.stats import entropy

import fingerprint.general as filterlist_general

log = logging.getLogger(__name__)


def update_user_subscriptions(
    user_subscriptions: pd.DataFrame, marker_to_fl_map: dict, fingerprint_results: dict
):
    """Update the identifiable lists after the defender enforces the previous mask rules on all users
    this effectively makes equivalence sets from the previous iteration no longer identifiable
    """

    ids_to_remove = set()

    is_key_str = isinstance(list(marker_to_fl_map.keys())[0], str)

    for marker in fingerprint_results["best_mask"]:
        fl = marker_to_fl_map[str(marker) if is_key_str else marker]
        ids_to_remove.add(fl)

    print(ids_to_remove)

    def remove_ids(x):
        return json.dumps(list(set(json.loads(x)) - ids_to_remove))

    new_subscriptions = user_subscriptions.copy()
    new_subscriptions["identifiable_unique_lists"] = new_subscriptions[
        "identifiable_unique_lists"
    ].apply(remove_ids)

    return new_subscriptions


def report_iteration(
    iteration: int,
    marker_to_fl_map: dict,
    fingerprint_results: dict,
    equivalence_sets: dict,
    used_rules: Optional[set] = None,
):
    """Report the results of an iteration of the iterative robustness process into output files"""

    if not used_rules:
        used_rules = set()

    os.makedirs(f"iter_{iteration}", exist_ok=True)

    with open(f"iter_{iteration}/fingerprint.json", "w") as f:
        json.dump(fingerprint_results, f)

    with open(f"iter_{iteration}/filterlist_names.json", "w") as f:
        json.dump(marker_to_fl_map, f)

    participating_filterlists = set()

    list_names = equivalence_sets["list_names"]

    is_key_str = isinstance(list(marker_to_fl_map.keys())[0], str)

    _used_rules = set()

    for marker in fingerprint_results["best_mask"]:
        fl = marker_to_fl_map[str(marker) if is_key_str else marker]
        _used_rules |= set(equivalence_sets["equivalent_rules"][fl])
        participating_filterlists |= set(
            [list_names[i] for i in equivalence_sets["equiprobable_list_sets"][fl]]
        )

    _used_rules = _used_rules - used_rules

    summary: dict = {
        "iteration": iteration,
        **fingerprint_results["stats"],
        "n_unique_users": sum(
            [len(s) for s in fingerprint_results["anon_sets"] if len(s) == 1]
        ),
        "n_usable_rules": len(_used_rules),
        "n_participating_filterlists": len(participating_filterlists),
        "participating_filterlists": list(participating_filterlists),
    }

    log.info(f"Iteration {iteration} summary:")
    for k, v in summary.items():
        if k == "participating_filterlists":
            continue
        log.info(f"  {k}: {v}")

    with open(f"iter_{iteration}/summary.json", "w") as f:
        json.dump(summary, f)

    return summary, _used_rules | used_rules


def load_iteration(iteration: int):
    """Load the results of an iteration of the iterative robustness process from output files"""

    with open(f"iter_{iteration}/fingerprint.json") as f:
        fingerprint_results: dict = json.load(f)

    with open(f"iter_{iteration}/filterlist_names.json") as f:
        marker_to_fl_map: dict = json.load(f)

    with open(f"iter_{iteration}/summary.json") as f:
        summary: dict = json.load(f)

    return marker_to_fl_map, fingerprint_results, summary


@hydra.main(
    config_path="../../conf", config_name="iterative_robustness.conf", version_base=None
)
def main(cfg: DictConfig = None) -> None:

    if cfg.encoding != "filterlist":
        raise NotImplementedError(
            "Only filterlist encoding is supported for general fingerprinting"
        )

    if cfg.method != "general":
        raise NotImplementedError(
            "Only general fingerprinting is supported for general fingerprinting"
        )

    ####### 1. Getting initial data
    # 1.1 User dataset
    user_subscriptions = pd.read_csv(
        to_absolute_path(os.path.join(cfg.source_dir, "issues_confs_identified.csv"))
    )

    # 1.2 Equivalence set definitions
    with open(
        to_absolute_path(
            os.path.join(cfg.filterlist_dir, "unique_filterlist_sets.json")
        )
    ) as f:
        equivalence_sets = json.load(f)

    # 1.3 Intial fingerprinting
    with open(
        to_absolute_path(os.path.join(cfg.fingerprint_dir, "filterlist_names.json"))
    ) as f:
        marker_to_fl_map = json.load(f)

    with open(
        to_absolute_path(os.path.join(cfg.fingerprint_dir, "fingerprint.json"))
    ) as f:
        fingerprint_results = json.load(f)

    iteration = 0

    iteration_summary, used_rules = report_iteration(
        iteration,
        marker_to_fl_map,
        fingerprint_results,
        equivalence_sets,
    )

    while not "max_iter" in cfg.thresholds or iteration < cfg.thresholds.max_iter:

        if (
            "uniqueness" in cfg.thresholds
            and iteration_summary["n_unique_users"] / len(user_subscriptions)
            <= cfg.thresholds.uniqueness
        ):
            log.info(f"Uniqueness threshold reached. Stopping at iteration {iteration}")
            break

        if (
            "entropy" in cfg.thresholds
            and iteration_summary["anon_set_entropy"] <= cfg.thresholds.entropy
        ):
            log.info(f"Entropy threshold reached. Stopping at iteration {iteration}")
            break

        iteration += 1

        if os.path.exists(f"iter_{iteration}"):
            log.info(f"Loading iteration {iteration}")
            marker_to_fl_map, fingerprint_results, iteration_summary = load_iteration(
                iteration
            )

        else:

            # 2.1 Update user subscriptions
            user_subscriptions = update_user_subscriptions(
                user_subscriptions, marker_to_fl_map, fingerprint_results
            )

            # 2.2 Fingerprinting
            (best_mask, anon_sets, best_metric), marker_to_fl_map = (
                filterlist_general.general_fingerprinting(
                    user_subscriptions,
                    iteration_summary["best_mask_size"],
                    col="identifiable_unique_lists",
                )
            )

            anon_set_sizes = np.array([len(s) for s in anon_sets])

            fingerprint_results = {
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

            # 2.3 Report iteration
            iteration_summary, used_rules = report_iteration(
                iteration,
                marker_to_fl_map,
                fingerprint_results,
                equivalence_sets,
                used_rules,
            )

    if "entropy" in cfg.thresholds and iteration >= cfg.thresholds.max_iter:
        log.info(f"Max iterations reached. Stopping at iteration {iteration}")


if __name__ == "__main__":
    main()
