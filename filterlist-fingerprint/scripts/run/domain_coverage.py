"""
Get the domain coverage over lists for all the related attacks
"""

import functools
import json
import logging
import os
import traceback
from collections import defaultdict
from pathlib import Path
from typing import Dict, List

import hydra
import pandas as pd
from hydra.utils import to_absolute_path
from omegaconf import DictConfig
from parallelbar import progress_starmap
from tqdm import tqdm

from filterlist_parser.aglintparser import AGLintBinding
from filterlist_parser.rules import get_identifiable_list_rules
from filterlist_parser.utils import slug

tqdm.pandas()

logger = logging.getLogger(__name__)
timestamp = pd.Timestamp.now().strftime("%Y-%m-%d_%H-%M-%S")


class DomainNode:
    """A node in the domain tree representing a prefix or suffix domain"""

    domain: str
    leaf: bool = False
    subdomains: Dict[str, "DomainNode"]

    def __init__(self, domain):
        self.domain = domain
        self.subdomains = {}

    def _clear_caches(self):
        self.__contains__.cache_clear()
        self.suffixes_for.cache_clear()
        self.has_suffix.cache_clear()
        self.leafs.cache_clear()

    def register(self, parts: List[str]) -> "DomainNode":
        """Register a domain in the tree

        Args:
            parts (List[str]): List of parts of the domain. ex: ["example", "com"]

        Returns:
            DomainNode: The node where the domain is registered
        """

        if len(parts) == 0:
            self.leaf = True
            return self

        if parts[-1] not in self.subdomains:
            self.subdomains[parts[-1]] = DomainNode(f"{parts[-1]}.{self.domain}")

        # clear caches
        self._clear_caches()

        return self.subdomains[parts[-1]].register(parts[:-1])

    def __str__(self):
        return f"DomainNode({self.domain} -> {list(self.subdomains.keys())}, leaf={self.leaf})"

    def __repr__(self) -> str:
        return self.__str__()

    def __len__(self):
        return sum([len(v) for v in self.subdomains.values()])

    def __getitem__(self, domain):
        parts = domain.split(".")

        if len(parts) == 1:
            return self.subdomains[parts[0]]

        return self.subdomains[parts[-1]][parts[:-1]]

    @functools.lru_cache(maxsize=1024)
    def __contains__(self, domain):
        parts = domain.split(".")

        if len(parts) == 1:
            return parts[0] in self.subdomains

        return parts[-1] in self.subdomains and parts[:-1] in self.subdomains[parts[-1]]

    @functools.lru_cache(maxsize=1024)
    def suffixes_for(self, parts: tuple) -> list:
        """Get all the prefixes for a given suffix

        Args:
            parts (tuple): The parts of the suffix. ex: ("example", "com")

        Returns:
            list: List of suffixes
        """

        prefixes = []

        if len(parts) == 0:
            if self.leaf:
                prefixes.append(self.domain)

        else:
            if parts[-1] in self.subdomains:
                if self.subdomains[parts[-1]].leaf:
                    prefixes.append(self.subdomains[parts[-1]].domain)
                prefixes.extend(self.subdomains[parts[-1]].suffixes_for(parts[:-1]))

        if "*" in self.subdomains:
            if self.subdomains["*"].leaf:
                prefixes.append(self.subdomains["*"].domain)
            prefixes.extend(self.subdomains["*"].suffixes_for(parts[:-1]))

        # remove duplicates
        prefixes = list(set(prefixes))

        return prefixes

    @functools.lru_cache(maxsize=1024)
    def has_suffix(self, parts: tuple):
        """Check if this domain matches the suffix

        Args:
            parts (tuple): The parts of the domain to check for the suffix. ex: ("example", "com")

        Returns:
            bool: True if the domain has the suffix
        """

        if len(parts) == 0:
            if self.leaf:
                return True
            else:
                parts = ["*"]

        if parts[-1] in self.subdomains:
            return self.subdomains[parts[-1]].leaf or self.subdomains[
                parts[-1]
            ].has_suffix(parts[:-1])

        if "*" in self.subdomains:
            return self.subdomains["*"].leaf or self.subdomains["*"].has_suffix(
                parts[:-1]
            )

        return False

    def __iter__(self):
        return iter(self.subdomains.values())

    def __next__(self):
        return next(self.subdomains.values())

    @functools.lru_cache(maxsize=1024)
    def leafs(self) -> "List[DomainNode]":
        """Get all the leaf nodes in the tree

        Returns:
            List[DomainNode]: List of leaf nodes
        """

        leafs = []

        if len(self.subdomains) == 0:
            return [self] if self.leaf else []

        for subdomain in self.subdomains.values():
            if subdomain.leaf:
                leafs.append(subdomain)

            leafs.extend(subdomain.leafs())

        return leafs

    def to_dict(self):
        """Convert the node to a dictionary"""

        return {
            "domain": self.domain,
            "leaf": self.leaf,
            "subdomains": {k: v.to_dict() for k, v in self.subdomains.items()},
        }

    @staticmethod
    def from_dict(node_dict: dict) -> "DomainNode":
        """Create a DomainNode from a dictionary"""

        node = DomainNode(node_dict["domain"])
        node.leaf = node_dict["leaf"]
        node.subdomains = {
            k: DomainNode.from_dict(v) for k, v in node_dict["subdomains"].items()
        }

        return node

    def __add__(self, other):

        new_node = DomainNode(self.domain)
        new_node.leaf = self.leaf or other.leaf

        self_subdomains = set(self.subdomains.keys())
        other_subdomains = set(other.subdomains.keys())

        for subdomain in self_subdomains.difference(other_subdomains):
            new_node.subdomains[subdomain] = self.subdomains[subdomain]

        for subdomain in other_subdomains.difference(self_subdomains):
            new_node.subdomains[subdomain] = other.subdomains[subdomain]

        for subdomain in self_subdomains.intersection(other_subdomains):
            new_node.subdomains[subdomain] = (
                self.subdomains[subdomain] + other.subdomains[subdomain]
            )

        return new_node


class DomainTree:
    """A tree representing a set of domains in prefix chains or suffix chains"""

    TLDs: Dict[str, DomainNode]
    reverse: bool = False

    def __init__(self, domains=None, reverse=False):
        """Create a new DomainTree

        Args:
            domains (List[str], optional): Optional list of domains to fill the tree with.
            reverse (bool, optional): If True, the tree will be a prefix tree, otherwise a suffix tree.
        """
        self.TLDs = {}
        self.reverse = reverse

        if domains is not None:
            for domain in domains:
                self.register(domain)

    def _clear_caches(self):
        self.__contains__.cache_clear()
        self.subsets_for.cache_clear()
        self.has_subset.cache_clear()
        self.leafs.cache_clear()

    def register(self, domain: str):
        """Register a domain in the tree

        Args:
            domain (str)

        Returns:
            DomainNode: The node where the domain is registered
        """

        parts = domain.split(".")

        if len(parts) > 5:
            logger.warning("Domain %s is too long", domain)

        if self.reverse:
            parts = parts[::-1]

        if parts[-1] not in self.TLDs:
            self.TLDs[parts[-1]] = DomainNode(parts[-1])

        # clear caches
        self._clear_caches()

        return self.TLDs[parts[-1]].register(parts[:-1])

    def __str__(self):
        return f"DomainTree({list(self.TLDs.keys())}, reverse={self.reverse})"

    def __repr__(self) -> str:
        return self.__str__()

    def __len__(self):
        return sum([len(v) for v in self.TLDs.values()])

    def __getitem__(self, domain):
        parts = domain.split(".")

        if self.reverse:
            parts = parts[::-1]

        if len(parts) == 1:
            return self.TLDs[parts[0]]

        return self.TLDs[parts[-1]][parts[:-1]]

    @functools.lru_cache(maxsize=1024)
    def __contains__(self, domain):
        parts = domain.split(".")

        if self.reverse:
            parts = parts[::-1]

        if len(parts) == 1:
            return parts[0] in self.TLDs

        return parts[-1] in self.TLDs and ".".join(parts[:-1]) in self.TLDs[parts[-1]]

    def __iter__(self):
        return iter(self.TLDs.values())

    def __next__(self):
        return next(self.TLDs.values())

    def append(self, domain):
        self.register(domain)

    def extend(self, domains):
        for domain in domains:
            self.append(domain)

    @functools.lru_cache(maxsize=1024)
    def subsets_for(self, domain, proper=False):
        """Get all the subdomains registered in the tree for a given domain

        Args:
            domain (str): The domain to get the subdomains for
            proper (bool, optional): If True, only return subdomains, not the domain itself

        Returns:
            List[str]: List of subdomains
        """

        if not isinstance(domain, str):
            logger.warning(
                f"Domain {domain} is not a string. Converting to string (this is experimental)"
            )
            domain = str(domain)

        parts = tuple(domain.split("."))

        if self.reverse:
            parts = parts[::-1]

        if parts[-1] in self.TLDs:
            subsets = self.TLDs[parts[-1]].suffixes_for(parts[:-1])

            if self.reverse:
                subsets = [DomainTree._reverse_domain(s) for s in subsets]

            if proper:
                return [s for s in subsets if s != domain]

            return subsets

        return []

    @staticmethod
    def _reverse_domain(domain):
        return ".".join(domain.split(".")[::-1])

    @functools.lru_cache(maxsize=1024)
    def has_subset(self, domain: str):
        """Check if the tree has domains with the following prefix or suffix depending on the tree type.

        Args:
            domain (str): The domain to check for

        Returns:
            bool: True if the tree has the domain as a prefix
        """

        parts = tuple(domain.split("."))

        if self.reverse:
            parts = parts[::-1]

        if parts[-1] in self.TLDs:
            return self.TLDs[parts[-1]].has_suffix(parts[:-1])

        return False

    def to_dict(self):
        """Convert the tree to a dictionary"""

        return {
            "reverse": self.reverse,
            "tlds": {k: v.to_dict() for k, v in self.TLDs.items()},
        }

    @staticmethod
    def from_dict(tree_dict: dict):
        """Create a DomainTree from a dictionary"""

        tree = DomainTree(reverse=tree_dict["reverse"])

        for tld, node in tree_dict["tlds"].items():
            tree.TLDs[tld] = DomainNode(node["domain"])
            tree.TLDs[tld].subdomains = {
                k: DomainNode.from_dict(v) for k, v in node["subdomains"].items()
            }

        return tree

    @functools.lru_cache(maxsize=1024)
    def leafs(self) -> "List[DomainNode]":
        """Get all the leaf nodes in the tree"""

        leafs = []

        for tld in self.TLDs.values():
            leafs.extend(tld.leafs())

        return leafs

    def __add__(self, other):

        if self.reverse != other.reverse:
            raise ValueError("Cannot merge trees with different reverse values")

        new_tree = DomainTree(reverse=self.reverse)

        self_tlds = set(self.TLDs.keys())
        other_tlds = set(other.TLDs.keys())

        for tld in self_tlds.difference(other_tlds):
            new_tree.TLDs[tld] = self.TLDs[tld]

        for tld in other_tlds.difference(self_tlds):
            new_tree.TLDs[tld] = other.TLDs[tld]

        for tld in self_tlds.intersection(other_tlds):
            new_tld = self.TLDs[tld] + other.TLDs[tld]

            new_tree.TLDs[tld] = new_tld

        return new_tree


def get_rule_applicable_domains(list_name, list_rules):
    """Get all domains that would activate the following filter rules
    The output is saved in a csv file with the following columns:
    - domain: The domain that activates the rule
    - count_rules: The number of rules that the domain activates
    - count_cosmetic_rules: The number of cosmetic rules that the domain activates
    - count_network_rules: The number of network rules that the domain activates

    Args:
        list_name (str): Name of the filter list
        list_rules (pd.DataFrame): DataFrame containing the filter rules
    """

    try:

        # if the file already exist`s, and the csv contains more than 200 rows, skip
        # if os.path.exists(f"{slug(list_name)}/rule_counts_per_domain.csv"):
        #     if pd.read_csv(f"{slug(list_name)}/rule_counts_per_domain.csv").shape[0] > 200:
        #         logger.info(f"Skipping {list_name}")
        #         return

        suffix_domain_tree = DomainTree()
        prefix_domain_tree = DomainTree(reverse=True)

        rules = AGLintBinding.parse_filter_rules(
            [
                json.loads(f'"{list_rule.rule}"').strip("\r")
                for _, list_rule in list_rules.iterrows()
            ]
        )

        rule_counts_per_domain = defaultdict(
            lambda: {"count": 0, "count_cosmetic": 0, "count_network": 0}
        )

        for rule in rules:
            rule_domains = rule.activating_domains
            suffix_domain_tree.extend(rule_domains)
            prefix_domain_tree.extend(rule_domains)

            for domain in rule_domains:
                rule_counts_per_domain[domain]["count"] += 1
                rule_counts_per_domain[domain][
                    "count_cosmetic"
                ] += rule.is_cosmetic_rule
                rule_counts_per_domain[domain]["count_network"] += rule.is_network_rule

        rule_counts_per_domain = pd.DataFrame(rule_counts_per_domain).T
        rule_counts_per_domain["domain"] = rule_counts_per_domain.index

        rule_counts_per_domain.rename(
            columns={
                "count": "count_rules",
                "count_cosmetic": "count_cosmetic_rules",
                "count_network": "count_network_rules",
            },
            inplace=True,
        )

        os.makedirs(slug(list_name), exist_ok=True)

        rule_counts_per_domain.to_csv(
            f"{slug(list_name)}/rule_counts_per_domain.csv", index=False
        )
        json.dump(
            suffix_domain_tree.to_dict(),
            open(f"{slug(list_name)}/suffix_tree.json", "w", encoding="utf-8"),
        )
        json.dump(
            prefix_domain_tree.to_dict(),
            open(f"{slug(list_name)}/prefix_tree.json", "w", encoding="utf-8"),
        )
        json.dump(
            {"timestamp": timestamp},
            open(f"{slug(list_name)}/meta.json", "w", encoding="utf-8"),
        )

        logger.info(f"Done for {list_name},` {len(suffix_domain_tree.leafs())} domains")

    except Exception as e:
        logger.error(f"Error for {list_name}: {e}")
        traceback.print_exc()
        return


def analyze_coverage(exp_dir: Path, list_names):
    """
    Creates a table containing the count of rules activated by each domain in the filter lists

           | list1 | list2 | list3 | ... | total_lists | total_rules
    domain1|   5   |   0   |   10  | ... |      15     |     20
    ...
    ...
    """

    out_dir = exp_dir / ".analysis"

    out_dir.mkdir(exist_ok=True)

    # keyed by domain
    domain_coverages: Dict[str, pd.DataFrame] = {
        "count_rules": None,
        "count_network_rules": None,
        "count_cosmetic_rules": None,
    }

    suffix_tree = DomainTree()
    prefix_tree = DomainTree(reverse=True)

    participating_list_names = []

    for list_name in tqdm(list_names, desc="Merging Counts"):

        if not os.path.exists(exp_dir / f"{slug(list_name)}/meta.json"):
            continue

        rule_counts_per_domain = pd.read_csv(
            exp_dir / f"{slug(list_name)}/rule_counts_per_domain.csv"
        )
        suffix_tree += DomainTree.from_dict(
            json.load(
                open(exp_dir / f"{slug(list_name)}/suffix_tree.json", encoding="utf-8")
            )
        )
        prefix_tree += DomainTree.from_dict(
            json.load(
                open(exp_dir / f"{slug(list_name)}/prefix_tree.json", encoding="utf-8")
            )
        )

        if len(rule_counts_per_domain) == 0:
            logger.info(f"Skipping {list_name}")
            continue

        for rule_type_col, old_coverage in domain_coverages.items():
            _coverage = rule_counts_per_domain[["domain", rule_type_col]].rename(
                columns={rule_type_col: list_name}
            )

            # remove rows where the count is 0
            _coverage = (
                _coverage[(_coverage[list_name] > 0)].copy().astype({"domain": str})
            )

            if old_coverage is None:
                domain_coverages[rule_type_col] = _coverage
            else:
                domain_coverages[rule_type_col] = old_coverage.merge(
                    _coverage, on="domain", how="outer"
                )

        participating_list_names.append(list_name)

    json.dump(
        suffix_tree.to_dict(), open(out_dir / "suffix_tree.json", "w", encoding="utf-8")
    )
    json.dump(
        prefix_tree.to_dict(), open(out_dir / "prefix_tree.json", "w", encoding="utf-8")
    )

    # sort by the number of parts in the domain to ensure that the suffixes and prefixes are added correctly
    for rule_type_col in domain_coverages.keys():
        domain_coverages[rule_type_col] = domain_coverages[rule_type_col].fillna(0)
        domain_coverages[rule_type_col].loc[:, participating_list_names] = (
            domain_coverages[rule_type_col][participating_list_names].astype(int)
        )
        domain_coverages[rule_type_col] = domain_coverages[rule_type_col].sort_values(
            by="domain", key=lambda x: x.str.count(".")
        )

    # for each domain, add the counts from all available suffixes
    for rule_type_col, coverage in domain_coverages.items():
        for _, row in tqdm(
            coverage.iterrows(),
            desc=f"Adding Suffixes for {rule_type_col}",
            total=len(coverage),
        ):
            suffixes = suffix_tree.subsets_for(row["domain"], proper=True)

            # if adversary controls suffix domain, they have access to all subdomain rules
            for suffix in suffixes:
                domain_coverages[rule_type_col].loc[
                    coverage["domain"] == suffix,
                    participating_list_names,
                ] += row[participating_list_names].astype(int)

            # if adversary controls subdomain, they have access to all suffix domain rules
            if len(suffixes):
                suffix_counts = domain_coverages[rule_type_col][
                    domain_coverages[rule_type_col]["domain"].isin(suffixes)
                ].sum()
                domain_coverages[rule_type_col].loc[
                    domain_coverages[rule_type_col]["domain"] == row["domain"],
                    participating_list_names,
                ] += suffix_counts[participating_list_names].astype(int)

    # for each domain, add the counts from all available prefixes
    for rule_type_col in domain_coverages.keys():
        for _, row in tqdm(
            domain_coverages[rule_type_col].iterrows(),
            desc=f"Adding Prefixes for {rule_type_col}",
            total=len(domain_coverages[rule_type_col]),
        ):
            prefixes = prefix_tree.subsets_for(row["domain"], proper=True)

            # if adversary controls prefix domain, they have access to all subdomain rules
            for prefix in prefixes:
                domain_coverages[rule_type_col].loc[
                    domain_coverages[rule_type_col]["domain"] == prefix,
                    participating_list_names,
                ] += row[participating_list_names].astype(int)

            # if adversary controls subdomain, they have access to all prefix domain rules
            if len(prefixes):
                print(row["domain"], prefixes)
                prefix_counts = domain_coverages[rule_type_col][
                    domain_coverages[rule_type_col]["domain"].isin(prefixes)
                ].sum()
                domain_coverages[rule_type_col].loc[
                    domain_coverages[rule_type_col]["domain"] == row["domain"],
                    participating_list_names,
                ] += prefix_counts[participating_list_names].astype(int)

    for rule_type_col in domain_coverages.keys():

        domain_coverages[rule_type_col]["total_rules"] = domain_coverages[
            rule_type_col
        ][participating_list_names].sum(axis=1)
        domain_coverages[rule_type_col]["total_lists"] = domain_coverages[
            rule_type_col
        ][participating_list_names].apply(lambda x: (x > 0).sum(), axis=1)

        domain_coverages[rule_type_col].to_csv(
            out_dir / f"coverage_{rule_type_col}.csv", index=False
        )


@hydra.main(
    config_path="../../conf",
    config_name="domain_coverage.conf",
    version_base=None,
)
def main(cfg: DictConfig = None) -> None:

    names_to_fingerprint = [a["name"] for a in cfg.filterlists.list]

    if cfg.action == "build":

        filterlists_parsed = [
            pd.read_csv(Path(to_absolute_path(cfg.parse_fp)) / f"{slug(name)}.csv")
            for name in names_to_fingerprint
        ]

        allowed_rules = get_identifiable_list_rules(
            filterlists_parsed, cfg.patterns, return_as_string=False
        )

        # parallelized
        progress_starmap(
            get_rule_applicable_domains,
            [(name, rules) for name, rules in zip(names_to_fingerprint, allowed_rules)],
            n_cpu=16,
        )

        json.dump({"timestamp": timestamp}, open("build-meta.json", "w", encoding="utf-8"))

    elif cfg.action == "analyze":

        analyze_coverage(Path("."), names_to_fingerprint)


if __name__ == "__main__":
    main()
