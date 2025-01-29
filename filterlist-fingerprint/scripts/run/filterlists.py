"""Script to download and parse filterlists"""

import json
import logging
import os
from pathlib import Path

import hydra
import pandas as pd
from hydra.utils import to_absolute_path
from omegaconf import DictConfig
from parallelbar import progress_starmap
from tqdm import tqdm

from filterlist_parser.filterlist_subscriptions import (
    encode_rules,
    filter_identifiable_rules_direclty,
    filter_unique_identifiable_filterlist_set_subscriptions,
    identifiable_rules_generator,
)
from filterlist_parser.raw import download_lists
from filterlist_parser.rules import (
    unique_sets_of_filterlists,
    get_identifiable_list_rules,
    parse_rules_from_filterlist_fp,
    unique_rules,
)
from filterlist_parser.utils import slug

logger = logging.getLogger(__name__)


def generate_filterlists_rules_file(allowed_rules_per_list: dict, n_rules: int):
    """Generate a csv file with the rules for each filterlist"""

    with open("filterlists_rules.csv", "w", encoding="utf-8") as f:
        f.write("list,rules\n")
        for fl_name, rules in allowed_rules_per_list.items():
            rules_encoded = encode_rules(rules, n_rules)
            f.write(f"{fl_name},{rules_encoded.hex()}\n")


def write_user_rules_file(
    user_index: int,
    row: pd.Series,
    allowed_rules_per_list: dict,
    name_resolutions: dict,
    n_rules: int,
):
    """Write the rules for a user subscription to a file"""

    rules = identifiable_rules_generator(
        row.filters, allowed_rules_per_list, name_resolutions, n_rules
    )

    if rules:
        with open(f"user-rules/{user_index}", "wb") as f:
            f.write(rules)


def generate_user_rules_file(
    user_subscriptions: pd.DataFrame,
    allowed_rules_per_list: dict,
    name_resolutions: dict,
    n_rules: int,
):
    """Generate a csv file with the rules for each user subscription"""

    # write them to temporary files
    os.makedirs("user-rules", exist_ok=True)

    progress_starmap(
        write_user_rules_file,
        [
            (i, row, allowed_rules_per_list, name_resolutions, n_rules)
            for i, row in user_subscriptions.iterrows()
        ],
        n_cpu=8,
    )

    # combine to csv
    with open("user_rules.csv", "w") as f:
        f.write("index,rules\n")
        for i in tqdm(range(len(user_subscriptions))):
            if os.path.exists(f"user-rules/{i}"):
                with open(f"user-rules/{i}", "rb") as f2:
                    f.write(f"{i},{f2.read().hex()}\n")

    # remove temporary files
    os.system("rm -r user-rules")


def parse_filterlist(cfg, name):
    """Parse a filterlist"""

    try:
        list_fp = Path(to_absolute_path(cfg.parse.download_fp)) / (slug(name) + ".txt")
        out_fp = Path(f"{slug(name)}.csv")

        if not cfg.parse.overwrite and out_fp.exists():
            return

        parse_rules_from_filterlist_fp(list_fp).to_csv(out_fp, index=False)
        tqdm.write(f"Filterlist {name} parsed")
    except Exception as e:
        tqdm.write(f"Error parsing {name}: {e}")


@hydra.main(config_path="../../conf", config_name="filterlists.conf", version_base=None)
def main(cfg: DictConfig) -> None:

    if cfg.action == "download":

        download_lists(
            filterlists=cfg.filterlists.list,
            out_dir=Path(os.getcwd()),
        )

    elif cfg.action == "parse":

        names_to_parse = (
            cfg.parse.which
            if cfg.parse.which
            else [a["name"] for a in cfg.filterlists.list]
        )

        progress_starmap(
            parse_filterlist,
            [(cfg, name) for name in names_to_parse],
            n_cpu=8,
        )

    elif cfg.action == "fingerprint":
        names_to_fingerprint = (
            cfg.fingerprint.which
            if cfg.fingerprint.which
            else [a["name"] for a in cfg.filterlists.list]
        )

        logger.info("Fingerprinting %i filter lists", len(names_to_fingerprint))

        if cfg.fingerprint.exclude:
            names_to_fingerprint = [
                a for a in names_to_fingerprint if a not in cfg.fingerprint.exclude
            ]

        filterlists_parsed = [
            pd.read_csv(
                Path(to_absolute_path(cfg.fingerprint.parse_fp)) / f"{slug(name)}.csv"
            )
            for name in names_to_fingerprint
        ]

        allowed_rules = get_identifiable_list_rules(
            filterlists_parsed, cfg.attack.patterns
        )

        # statistics about counts per filterlist
        _unique_rules = unique_rules(*allowed_rules)
        counts = []
        for i, _list in enumerate(_unique_rules):
            counts.append(
                {
                    "name": names_to_fingerprint[i],
                    "count_unique": len(_list),
                    "count_allowed": len(allowed_rules[i]),
                    "count_total": len(filterlists_parsed[i]),
                }
            )

        pd.DataFrame(counts).to_csv("unique_counts.csv", index=False)

        # identify the user subscriptions
        user_subscriptions = pd.read_csv(
            Path(to_absolute_path(cfg.fingerprint.issues_fp)) / "issues_confs.csv"
        )
        user_subscriptions = user_subscriptions[user_subscriptions.valid]

        rule_id_map, allowed_rules_per_list, name_resolutions = (
            filter_identifiable_rules_direclty(allowed_rules, cfg.filterlists.list)
        )

        generate_user_rules_file(
            user_subscriptions,
            allowed_rules_per_list,
            name_resolutions,
            len(rule_id_map),
        )

        json.dump(rule_id_map, open("rule_id.json", "w"))

        generate_filterlists_rules_file(allowed_rules_per_list, len(rule_id_map))

        # third method

        unique_list_sets = unique_sets_of_filterlists(allowed_rules)

        if len(unique_list_sets) == 0:
            logger.error("No unique filterlist sets found")
            return
        list_sets, rule_sets = zip(*unique_list_sets)

        unique_filterlists_output = {
            "list_names": names_to_fingerprint,
            "equivalent_rules": [list(rule) for rule in rule_sets],
            "equiprobable_list_sets": [list(li) for li in list_sets],
        }

        with open("unique_filterlist_sets.json", "w") as f:
            json.dump(unique_filterlists_output, f)

        identifiable_unique_lists, bad_names = (
            filter_unique_identifiable_filterlist_set_subscriptions(
                user_subscriptions, unique_filterlists_output, cfg.filterlists.list
            )
        )

        user_subscriptions["identifiable_unique_lists"] = (
            identifiable_unique_lists.apply(json.dumps)
        )
        json.dump(list(bad_names), open("bad_names_unique.json", "w"))

        user_subscriptions.to_csv("issues_confs_identified.csv", index=False)

    elif cfg.action == "query":

        names_to_fingerprint = (
            cfg.fingerprint.which
            if cfg.fingerprint.which
            else [a["name"] for a in cfg.filterlists.list]
        )

        filterlists_parsed = [
            pd.read_csv(
                Path(os.getcwd()) / f"../../{cfg.fingerprint.parse_fp}/{slug(name)}.csv"
            )
            for name in names_to_fingerprint
        ]

        if "rule" in cfg.query:

            # print lists that have this rule
            rule = cfg.query.rule
            lists = []
            for i, _list in enumerate(filterlists_parsed):
                if any(rule in r for r in _list.rule):
                    lists.append(names_to_fingerprint[i])
                    print(names_to_fingerprint[i])

        if "lists" in cfg.query:
            # print rules that are similar in both lists
            list1, list2 = cfg.query.lists

            rules1 = filterlists_parsed[names_to_fingerprint.index(list1)].rule
            rules2 = filterlists_parsed[names_to_fingerprint.index(list2)].rule

            similar_rules = set(rules1).intersection(rules2)
            for r in similar_rules:
                print(r)

        else:
            raise ValueError(f"Unknown query: {cfg.query}. Valid queries are: rule")

    else:
        raise ValueError(f"Unknown action: {cfg.action}. Valid actions are: download")

    # print the output path
    print(os.getcwd())


if __name__ == "__main__":
    main()
