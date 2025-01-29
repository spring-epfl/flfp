"""Module for parsing and analyzing filter rules"""

import json
from typing import Dict, Iterable, List, Optional

import pandas as pd
from tqdm import tqdm
from pathlib import Path

from filterlist_parser.aglintparser import AdblockRule, AGLintBinding


def _make_rule_row(rule: AdblockRule) -> dict:
    """Create a dataframe row (dict) for a rule"""

    if not rule.is_well_formed:
        return {
            "rule": rule.raw_rule_text,
            "cosmetic": False,
            "network": False,
            "html": False,
            "script": False,
            "exception": False,
            "extended_css": False,
            "generic": False,
            "options": None,
            "cosmetic_how": None,
            "network_how": None,
            "resource": None,
            "rule_regex": None,
        }

    return {
        "rule": rule.raw_rule_text,
        "cosmetic": rule.is_cosmetic_rule,
        "network": rule.is_network_rule,
        "html": rule.is_html_rule,
        "script": rule.is_js_rule,
        "exception": rule.is_exception,
        "extended_css": rule.is_extended_css,
        "generic": rule.is_generic_rule,
        "options": json.dumps(rule.options),
        "cosmetic_how": rule.cosmetic_how,
        "network_how": rule.network_how,
        "resource": rule.resource_type,
        "rule_regex": rule.regex,
    }


def parse_rules(
    rules: Iterable[str], parse_by_rule=False, parallel=False
) -> pd.DataFrame:
    """
    Creates a dataframe with metadata for each rule in a list of rules

    Args:
        rules (Iterable[str]): List of rules
        parse_by_rule (bool, optional): If false, pass all rules to the AGLint parser at once. Defaults to False.
        parallel (bool, optional): Parallelize the parsing. Defaults to False.

    Returns:
        pd.DataFrame: DataFrame with metadata for each rule
    """

    # could throw an error if the list is long

    rules_metadata = []

    def _parse_by_rule_iterator(rules):

        def _parse_rule(rule):
            try:
                return AGLintBinding.parse_filter_rule(rule)
            except AGLintBinding.ParsingError:
                return None

        if not parallel:
            for rule in tqdm(rules):
                yield _parse_rule(rule)

        else:
            from joblib import Parallel, delayed

            rules = list(rules)
            results = Parallel(n_jobs=-1)(
                delayed(_parse_rule)(rule) for rule in tqdm(rules)
            )

            for rule, result in zip(rules, results):
                if result is None:
                    yield None
                else:
                    yield result

    iterator = (
        _parse_by_rule_iterator
        if parse_by_rule
        else lambda rules: tqdm(
            AGLintBinding.parse_filter_rules(rules), total=len(rules)
        )
    )

    for rule in iterator(rules):

        # only if parsing error happened
        if rule is None:
            rules_metadata.append(
                {
                    "rule": None,
                    "cosmetic": False,
                    "network": False,
                    "html": False,
                    "script": False,
                    "exception": False,
                    "extended_css": False,
                    "generic": False,
                    "options": None,
                    "cosmetic_how": None,
                    "network_how": None,
                    "resource": None,
                    "parsing_error": True,
                    "rule_regex": None,
                }
            )
            continue

        rules_metadata.append(
            _make_rule_row(rule)
            | {"well_formed": rule.is_well_formed, "parsing_error": False}
        )

    return pd.DataFrame(rules_metadata)


def parse_rules_from_filterlist_fp(
    filterlist_fp: Path,
) -> pd.DataFrame:
    """
    Parse rules from a filterlist file path

    Args:
        filterlist_fp (Path): Path to the filterlist file

    Returns:
        pd.DataFrame: DataFrame with metadata for each rule
    """

    rules_metadata = []

    for rule in AGLintBinding.parse_filter_list(filterlist_fp):

        if not rule.is_well_formed:
            continue

        rules_metadata.append(_make_rule_row(rule))

    return pd.DataFrame(rules_metadata)


def _rules_mask_for_pattern(rules: pd.DataFrame, pattern):
    """Create a mask for a pattern to filter rules"""

    mask = pd.Series([True] * len(rules))

    if pattern.get("type") is not None:
        mask &= rules[pattern.type]

    if pattern.get("generic") is not None:
        mask &= rules["generic"] == pattern["generic"]

    if pattern.get("cosmetic_how") is not None:
        mask &= rules["cosmetic_how"] == pattern.cosmetic_how

    if pattern.get("network_how") is not None:
        mask &= rules["network_how"] == pattern.network_how

    if pattern.get("exclude_resource_types") is not None:
        mask &= ~(rules["resource"].isin(pattern.exclude_resource_types))

    return mask


def _allowed_filter_rules(rules: pd.DataFrame, patterns: list):

    mask = pd.Series([False] * len(rules))

    for pattern in patterns:
        mask |= _rules_mask_for_pattern(rules, pattern)

    return rules[mask]


def _rule_provenance_dict(*lists: List[str]):

    rules = {}

    # tqdm.write("Finding unique rules")
    for i, l in enumerate(lists):
        for rule in l:
            rules[rule] = rules.get(rule, [])
            rules[rule].append(i)

    return rules


def unique_rules(*lists: List[str]):
    """Find unique rules in each list"""

    rules = _rule_provenance_dict(*lists)

    unique_rules = {}

    for rule, rule_lists in rules.items():
        if len(rule_lists) == 1:
            unique_rules[rule_lists[0]] = unique_rules.get(rule_lists[0], [])
            unique_rules[rule_lists[0]].append(rule)

    return [unique_rules.get(i, []) for i in range(len(lists))]


def get_identifiable_list_rules(
    lists: List[pd.DataFrame],
    patterns: Optional[List[Dict]] = None,
    return_as_string: bool = True,
):
    """Filter rules of lists that match provided patterns.
    You can find the pattern format in the config directory. It mostly describes rule types and scopes allowed.

    Args:
        lists (List[pd.DataFrame]): List of filter rules
        patterns (Optional[List[Dict]], optional): List of patterns to match. Defaults to None.
        return_as_string (bool, optional): Return as string. Defaults to True.

    Returns:
        List: List of filter rules
    """
    rules = []

    if patterns is not None:
        rules = [_allowed_filter_rules(l, patterns) for l in tqdm(lists)]
    else:
        rules = lists

    if return_as_string:
        return [l.rule.values.tolist() for l in lists]
    else:
        return rules


def unique_sets_of_filterlists(list_rules: List[List[str]]):
    """
    Get all sets of lists that share at least one rule

    Args:
        list_rules (List[List[str]]): List of filter lists (i.e. list of rules)

    Returns:
        List[Tuple[frozenset, List[List[str]]]]: List of tuples ({list set}, {rule set}) equivalences
    """

    rule_provenances = _rule_provenance_dict(*list_rules)

    keyed_by_list_sets = {}

    for rule, provenance in rule_provenances.items():

        key = frozenset(provenance)

        if key not in keyed_by_list_sets:
            keyed_by_list_sets[key] = []

        keyed_by_list_sets[key].append(rule)

    return list(keyed_by_list_sets.items())
