# Reference: https://github.com/gaborgulyas/constrainted_fingerprinting/blob/master/common.py

import json
from multiprocessing.managers import SharedMemoryManager
from typing import List
import numpy as np
import pandas as pd
from filterlist_parser.filterlist_subscriptions import decode_rules, encode_rules
from tools.timer import Timer
from tqdm import tqdm
from parallelbar import progress_starmap
from dotenv import load_dotenv
import os
from scipy.sparse import csr_matrix

load_dotenv()
N_CPU_SMALL_MEM = int(os.getenv("N_CPU_SMALL_MEM", 4))
tqdm.pandas()


def prepare(user_subscriptions: pd.DataFrame, col="identifiable_lists"):
    """Prepare the user subscriptions for the fingerprinting algorithm using filter-list mode

    Args:
        user_subscriptions (pd.DataFrame): A dataframe with the user subscriptions
        col (str, optional): The user subscriptions column. Defaults to "identifiable_lists".

    Returns (tuple): A tuple with the following elements:
        - users (dict): A dictionary with the users as keys and the lists they are subscribed to as values
        - attrs (dict): A dictionary with the lists as keys and the users that have the list as values
        - listname_from_index (dict): A dictionary that maps the list index to the list name
    """

    list_indeces = {}
    listname_from_index = {}

    users = {}
    attrs = {}

    for i, user_row in user_subscriptions.iterrows():
        user_subscriptions = set(json.loads(user_row[col]))

        for list_name in user_subscriptions:
            # assign an index to each list
            if list_name not in list_indeces:
                list_indeces[list_name] = len(list_indeces)
                listname_from_index[list_indeces[list_name]] = list_name

            # add the user to the list of users that have this list
            if list_indeces[list_name] not in attrs:
                attrs[list_indeces[list_name]] = {i}
            else:
                attrs[list_indeces[list_name]].add(i)

        # store the user's subscriptions as a list of list indeces
        users[i] = [list_indeces[list_name] for list_name in user_subscriptions]

    return users, attrs, listname_from_index


def decode_rules_to_loc(buffer, uid, n_users, n_rules, rules_compressed_hex):
    """Decode the rules of a user and store them in a shared memory buffer"""

    rules = decode_rules(bytes.fromhex(rules_compressed_hex), n_rules, "bool")

    decoded_rules = np.ndarray((n_users, n_rules), dtype=bool, buffer=buffer.buf)
    decoded_rules[uid, :] = rules


def prepare_rules(user_rules: pd.DataFrame, n_rules):
    """Prepare the rules for the fingerprinting algorithm using rule mode

    Args:
        user_rules (pd.DataFrame): A dataframe with the user rules in hex format
        n_rules (int): The number of rules

    Returns:
        np.ndarray: The decoded rules
    """

    with SharedMemoryManager() as smm:
        # shared memory for decoded rules
        decoded_rules_buff = smm.SharedMemory(n_rules * user_rules.shape[0] * 8)
        decoded_rules = np.ndarray(
            (user_rules.shape[0], n_rules), dtype=bool, buffer=decoded_rules_buff.buf
        )

        # the rules are stored as a compressed binary list of true/false values
        progress_starmap(
            decode_rules_to_loc,
            (
                (decoded_rules_buff, i, user_rules.shape[0], n_rules, x)
                for i, x in enumerate(user_rules.rules)
            ),
            total=user_rules.shape[0],
            n_cpu=N_CPU_SMALL_MEM,
        )

        decoded_rules = decoded_rules.copy()

    return decoded_rules


# FILTERLIST MATRIX OPERATIONS

def viable_candidates_positive(
    filterlists_matrix, rule_index, available_candidates=None
):

    certain_rules = np.sum(
        filterlists_matrix * filterlists_matrix[:, [rule_index]], axis=0
    ) == np.sum(filterlists_matrix[:, [rule_index]])

    if available_candidates is None:
        return ~certain_rules

    return (
        available_candidates.reshape(
            -1,
        )
        & ~certain_rules
    )


def viable_candidates_negative(
    filterlists_matrix, rule_index, available_candidates=None
):

    target_rules = (
        np.sum(filterlists_matrix * ~filterlists_matrix[:, [rule_index]], axis=0) > 0
    )

    if available_candidates is None:
        return target_rules
    else:

        return target_rules & available_candidates.reshape(
            -1,
        )
