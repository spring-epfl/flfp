"""Module to generate the identifiable rules for each user subscription"""

import json
from typing import List
import zlib

import numpy as np
import pandas as pd
from tqdm import tqdm

from filterlist_parser.utils import get_filterlist_name_resolutions

tqdm.pandas()


def encode_rules(rules: List[int], n_rules: int):
    """
    Encode a list of rules into a bitstring

    Args:
        rules: list of ad-blocker rule indeces
        n_rules: number of rules in the filterlist

    Returns:
        rules_bytes: compressed bitstring of the rules
    """
    rule_vector = [False] * n_rules

    for rule_index in rules:
        rule_vector[rule_index] = True

    # turn into bitstring
    # each 8 bits represent a byte
    rules_bytes = bytes(
        [
            sum([b << i for i, b in enumerate(rule_vector[j : j + 8])])
            for j in range(0, n_rules, 8)
        ]
    )

    # compress the bitstring
    rules_bytes = zlib.compress(rules_bytes)
    return rules_bytes


def decode_rules(rules_bytes: bytes, n_rules: int, mode="indeces"):
    """
    Decode a bitstring into a list of rule indeces.

    Args:
        rules: compressed bitstring of the rules
        n_rules: number of rules in the filterlist
        mode: "indeces" to return the rule indeces, "bytes" to return the compressed bitstring, "bool" to return a boolean vector

    Returns:
        rules: list of ad-blocker rule indeces. Formatting depends on the mode.
    """

    rules_bytes = zlib.decompress(rules_bytes)

    if mode == "bytes":
        return rules_bytes

    if mode == "bool":
        return np.array(
            [
                bool(byte & (1 << i))
                for bi, byte in enumerate(rules_bytes)
                for i in range(8)
                if bi * 8 + i < n_rules
            ]
        )

    # else mode is "indeces" and we return the rule indeces
    rule_vector = []

    for byte in rules_bytes:
        rule_vector += [(byte >> i) & 1 for i in range(8)]

    return [i for i, b in enumerate(rule_vector) if b]


def identifiable_rules_generator(
    filterlists, allowed_rules_per_list, name_resolutions, n_rules
):
    """
    Generate the rules for a user subscription
    """

    _filterlists = []

    if pd.isna(filterlists):
        return []

    else:

        # make sure all lists are the original name not an alias
        for name in json.loads(filterlists):

            if name not in name_resolutions:
                continue

            _filterlists.append(name_resolutions[name])

        return encode_rules(
            [
                rule
                for filterlist in _filterlists
                for rule in allowed_rules_per_list[filterlist]
            ],
            n_rules,
        )


def filter_identifiable_rules_direclty(allowed_rules: list, filterlists_defs: list):
    """
    Filter the rules that are allowed for each filterlist without the filter-list intermediate

    Args:
        allowed_rules: list of lists of allowed rules for each filterlist
        filterlists_defs: list of filterlist definitions

    Returns:
        Tuple of:
            * allowed_rule_map: map of rule to rule id
            * allowed_rules_per_list: map of filterlist name to allowed rule ids
            * name_resolutions: map of alias to default name
    """

    # build name resolution to change aliases to default names
    name_resolutions = get_filterlist_name_resolutions(filterlists_defs)

    allowed_rule_map = {}
    allowed_rules_ids = []

    for rules in allowed_rules:

        # assign a unique id to each rule, if it is not already assigned
        for rule in rules:
            if rule not in allowed_rule_map:
                allowed_rule_map[rule] = len(allowed_rule_map)

        # map the rules to their ids
        allowed_rules_ids.append([allowed_rule_map[rule] for rule in rules])

    allowed_rules_per_list = {
        fl["name"]: allowed_rules_ids[i] for i, fl in enumerate(filterlists_defs)
    }

    return allowed_rule_map, allowed_rules_per_list, name_resolutions


def filter_unique_identifiable_filterlist_set_subscriptions(
    issue_confs: pd.DataFrame, filterlists_data: dict, filterlists_defs: list
):
    """
    Return the equivalence sets for each user subscription

    Args:
        issue_confs: user subscription data
        filterlists_data: dictionary of filterlist data from fingeprinting attack
        filterlists_defs: list of filterlist definitions

    Returns:
        Tuple of:
            * identifiable_filterlists: list of equivalence sets for each user subscription
            * bad_names: set of filterlist names that are not in the filterlist definitions
    """

    list_names, equiprobable_list_sets = (
        filterlists_data["list_names"],
        filterlists_data["equiprobable_list_sets"],
    )

    # build name resolution to change aliases to default names
    name_resolutions = get_filterlist_name_resolutions(filterlists_defs)
    filterlist_index = {name: i for i, name in enumerate(list_names)}

    bad_names = set()

    def _filter_identifiable_subscriptions_for_conf(
        filterlists: str,
    ):
        if pd.isna(filterlists):
            return []

        _filterlists = []

        for name in json.loads(filterlists):

            if name not in name_resolutions:
                bad_names.add(name)
                continue

            _filterlists.append(filterlist_index[name_resolutions[name]])

        user_list_sets = []

        for i, equiprobable_list_set in enumerate(equiprobable_list_sets):
            # check if at least one of the equiprobable list sets is in the user's list
            # -> the equivalent rule should test to true
            if len(set(equiprobable_list_set).intersection(_filterlists)) > 0:
                user_list_sets.append(i)

        return list(set(user_list_sets))

    identifiable_filterlists = issue_confs.filters.progress_apply(
        _filter_identifiable_subscriptions_for_conf
    )

    return identifiable_filterlists, bad_names
