from datetime import datetime
from functools import reduce
import json
import math
import os
from pathlib import Path
import hydra
from omegaconf import DictConfig
import pandas as pd
from hydra.utils import to_absolute_path
from tqdm import tqdm

tqdm.pandas()


@hydra.main(
    config_path="../../conf",
    config_name="summarize_attack_rules.conf",
    version_base=None,
)
def main(cfg: DictConfig = None) -> None:

    # get important equivalence sets for general and targeted fingerprinting
    important_equivalence_sets = set()

    #### Targeted
    targeted_fingerprints = pd.read_csv(
        Path(to_absolute_path(cfg.targeted_fingerprint_dir)) / "fingerprints.csv"
    )

    # remove the minus sign from best masks
    targeted_equivalence_sets = targeted_fingerprints.best_mask.apply(
        lambda x: set(json.loads(x.replace("-", "").replace("0.01", "0")))
    ).values
    targeted_equivalence_sets = reduce(
        lambda x, y: x.union(y), targeted_equivalence_sets
    )
    important_equivalence_sets |= targeted_equivalence_sets

    #### General
    general_equivalence_sets = set()

    for fp in Path(to_absolute_path(cfg.general_fingerprint_dir)).glob(
        "**/max_size:*/fingerprint.json"
    ):
        fingerprint = json.load(fp.open())
        equivalence_sets = fingerprint["best_mask"]
        general_equivalence_sets |= set(
            abs(x) if abs(x) != 0.01 else 0 for x in equivalence_sets
        )

    important_equivalence_sets |= general_equivalence_sets

    # get the rules for the equivalent sets
    equivalent_sets_definition = json.loads(
        open(
            Path(to_absolute_path(cfg.attack_fingerprint_dir))
            / "unique_filterlist_sets.json"
        ).read()
    )

    ordered_filterlist_names = equivalent_sets_definition["list_names"]
    ordered_equivalent_filterlists = equivalent_sets_definition[
        "equiprobable_list_sets"
    ]
    ordered_equivalent_rules = equivalent_sets_definition["equivalent_rules"]

    # save the output as a CSV such that
    # rule, equivalent_set_id, filterlists

    def output_rules_for_equivalence_sets(equivalent_sets):
        output_rules = []

        for equivalent_set_id in equivalent_sets:

            _rules = ordered_equivalent_rules[equivalent_set_id]
            _filterlist_ids = ordered_equivalent_filterlists[equivalent_set_id]
            _filterlist_names = [ordered_filterlist_names[x] for x in _filterlist_ids]

            for rule in _rules:
                output_rules.append(
                    {
                        "rule": rule,
                        "equivalent_set_id": equivalent_set_id,
                        "filterlists": _filterlist_names,
                    }
                )

        return pd.DataFrame(output_rules)

    output_rules_for_equivalence_sets(important_equivalence_sets).to_csv(
        "important_rules.csv", index=False
    )
    output_rules_for_equivalence_sets(general_equivalence_sets).to_csv(
        "general_important_rules.csv", index=False
    )
    output_rules_for_equivalence_sets(targeted_equivalence_sets).to_csv(
        "targeted_important_rules.csv", index=False
    )


if __name__ == "__main__":
    main()
