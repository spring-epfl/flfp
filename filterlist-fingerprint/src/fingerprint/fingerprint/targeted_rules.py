# Reference: https://github.com/gaborgulyas/constrainted_fingerprinting/blob/master/03_individual_fingerprints_faster.py

import json
from multiprocessing.managers import SharedMemoryManager
import traceback
from typing import Optional
import numpy as np
import pandas as pd

from fingerprint.common import (
    prepare_rules,
    viable_candidates_negative,
    viable_candidates_positive,
)
from parallelbar import progress_starmap
from dotenv import load_dotenv
import os

from tools.timer import Timer

load_dotenv()

N_CPU = int(os.getenv("N_CPU", 4))


# TODO: Update GreedyTargetedFingerprinting to work with sparse edge matrix
def prepare_readonly_filterlist_data(
    filterlist_rules: np.ndarray, smm: Optional[SharedMemoryManager] = None
):

    if smm:
        _filterlist_rules_buff = smm.SharedMemory(filterlist_rules.nbytes)
        filterlist_rules_shared = np.ndarray(
            filterlist_rules.shape, dtype=bool, buffer=_filterlist_rules_buff.buf
        )
        filterlist_rules_shared[:] = filterlist_rules

        return [(_filterlist_rules_buff, filterlist_rules.shape)]

    return filterlist_rules


def prepare_readonly_user_data(
    user_attrs: np.ndarray, smm: Optional[SharedMemoryManager] = None
):

    if smm:
        _user_attrs_buff = smm.SharedMemory(user_attrs.nbytes)
        _attr_users_buff = smm.SharedMemory(user_attrs.nbytes)
        _non_empty_attrs_buff = smm.SharedMemory(user_attrs.shape[1] * 8)

        user_attrs_shared = np.ndarray(
            user_attrs.shape, dtype=bool, buffer=_user_attrs_buff.buf
        )
        user_attrs_shared[:] = user_attrs

        attr_users_shared = np.ndarray(
            (user_attrs.shape[1], user_attrs.shape[0]),
            dtype=bool,
            buffer=_attr_users_buff.buf,
        )
        attr_users_shared[:] = user_attrs.T

        non_empty_attrs_shared = np.ndarray(
            (user_attrs.shape[1], 1), dtype=bool, buffer=_non_empty_attrs_buff.buf
        )
        non_empty_attrs_shared[:] = (np.sum(user_attrs, axis=0) > 0).reshape(-1, 1)

        return [
            (_user_attrs_buff, user_attrs.shape),
            (_attr_users_buff, user_attrs.T.shape),
            (_non_empty_attrs_buff, non_empty_attrs_shared.shape),
        ]

    attr_users = user_attrs.T
    attrs_user_count = np.sum(user_attrs, axis=0)
    non_empty_attrs = attrs_user_count > 0
    non_empty_attrs = non_empty_attrs.reshape(-1, 1)

    return user_attrs, attr_users, attrs_user_count, non_empty_attrs


def _greedy_individual_fingerprint(shared_data, uid):

    # timer = Timer(log_func=lambda x: print(f"[TASK {uid}]: {x}"))
    timer = Timer()

    (
        (_user_attrs_buff, user_attrs_shape),
        (_attr_users_buff, attr_users_shape),
        (_non_empty_attrs_buff, non_empty_attrs_shape),
    ) = shared_data

    user_attrs = np.ndarray(user_attrs_shape, dtype=bool, buffer=_user_attrs_buff.buf)
    attr_users = np.ndarray(attr_users_shape, dtype=bool, buffer=_attr_users_buff.buf)
    non_empty_attrs = np.ndarray(
        non_empty_attrs_shape, dtype=bool, buffer=_non_empty_attrs_buff.buf
    )

    # """

    # 		r1 r2 r3
    # 	u1   0  1  1
    # 	u2   1  0  1
    # 	u3   1  1  0

    # """

    with timer("target_users"):
        target_users = (user_attrs[uid].reshape(-1, 1) & attr_users) | (
            ~user_attrs[uid].reshape(-1, 1) & ~attr_users
        )

    # 	else:
    # 		users[a] = user_set - self.attrs[a]
    with timer("mask"):
        mask = np.zeros((user_attrs.shape[1], 1))

    with timer("anon_set"):
        anon_set = np.ones((1, user_attrs.shape[0]), dtype=bool)

    history = []

    targeted_anon_set_sizes = (target_users).sum(axis=1)

    # return mask, history, timer.measurements

    # i = 0
    with timer("loop"):
        while anon_set.sum() > 1:

            # i+= 1

            # if i > 10:
            # 	raise Exception("Infinite loop")

            # avail_attrs = set(users.keys()) - set(mask)
            with timer("avail_attrs"):
                avail_attrs = non_empty_attrs & (mask < 1)

            # print("avail_attrs", np.where(avail_attrs)[0])

            with timer("targeted_anon_set"):
                targeted_anon_set = target_users & anon_set

            with timer("a_vals sum"):
                # https://github.com/numpy/numpy/issues/16158
                # matmul is faster than sum
                a_vals_sum = targeted_anon_set_sizes.reshape(-1, 1)

            with timer("a_vals reshape"):
                a_vals = a_vals_sum.reshape(-1, 1)

            with timer("a_vals"):
                a_vals = a_vals - avail_attrs * user_attrs.shape[0]

            with timer("min_a"):
                min_a = np.argmin(a_vals)

            if a_vals_sum[min_a] == anon_set.sum():
                break

            if user_attrs[uid, min_a]:
                mask[min_a] = 1
            else:
                mask[min_a] = -1

            with timer("update_anon_set"):
                prev_users = anon_set
                anon_set = anon_set & target_users[min_a]
                rem_users = prev_users & ~anon_set

                rem_lists = targeted_anon_set[:, rem_users.reshape(-1)].sum(axis=1)

                targeted_anon_set_sizes -= rem_lists

            history.append(
                {
                    "len_anon_set": int(anon_set.sum()),
                    "len_mask": int(mask.__abs__().sum()),
                }
            )

    return mask, history, timer.measurements


def _greedy_individual_fingerprint_filterlist_aware(shared_data, uid):

    timer = Timer(log_func=lambda x: print(f"[TASK {uid}]: {x}"))

    (
        (_user_attrs_buff, user_attrs_shape),
        (_attr_users_buff, attr_users_shape),
        (_non_empty_attrs_buff, non_empty_attrs_shape),
        (_filterlist_rules_buff, filterlist_rules_shape),
    ) = shared_data

    user_attrs = np.ndarray(user_attrs_shape, dtype=bool, buffer=_user_attrs_buff.buf)
    attr_users = np.ndarray(attr_users_shape, dtype=bool, buffer=_attr_users_buff.buf)
    non_empty_attrs = np.ndarray(
        non_empty_attrs_shape, dtype=bool, buffer=_non_empty_attrs_buff.buf
    )
    filterlist_rules = np.ndarray(
        filterlist_rules_shape, dtype=bool, buffer=_filterlist_rules_buff.buf
    )

    # """

    # 		r1 r2 r3
    # 	u1   0  1  1
    # 	u2   1  0  1
    # 	u3   1  1  0

    # """

    with timer("target_users"):
        target_users = (user_attrs[uid].reshape(-1, 1) & attr_users) | (
            ~user_attrs[uid].reshape(-1, 1) & ~attr_users
        )

    with timer("mask"):
        mask = np.zeros((user_attrs.shape[1], 1))

    with timer("anon_set"):
        anon_set = np.ones((1, user_attrs.shape[0]), dtype=bool)

    history = []

    targeted_anon_set_sizes = (target_users).sum(axis=1)

    # return mask, history, timer.measurements

    # i = 0
    with timer("loop"):
        while anon_set.sum() > 1:

            with timer("avail_attrs"):
                avail_attrs = non_empty_attrs & (mask < 1)

            with timer("targeted_anon_set"):
                targeted_anon_set = target_users & anon_set

            with timer("a_vals sum"):
                a_vals_sum = targeted_anon_set_sizes.reshape(-1, 1)

            with timer("a_vals reshape"):
                a_vals = a_vals_sum.reshape(-1, 1)

            with timer("a_vals"):
                a_vals = a_vals - avail_attrs * user_attrs.shape[0]

            with timer("min_a"):
                min_a = np.argmin(a_vals)

            if a_vals_sum[min_a] == anon_set.sum():
                break

            if user_attrs[uid, min_a]:
                mask[min_a] = 1
                non_empty_attrs = viable_candidates_positive(
                    filterlist_rules, min_a, non_empty_attrs
                ).reshape(-1, 1)

            else:
                mask[min_a] = -1
                non_empty_attrs = viable_candidates_negative(
                    filterlist_rules, min_a, non_empty_attrs
                ).reshape(-1, 1)

            with timer("update_anon_set"):
                prev_users = anon_set
                anon_set = anon_set & target_users[min_a]
                rem_users = prev_users & ~anon_set

                rem_lists = targeted_anon_set[:, rem_users.reshape(-1)].sum(axis=1)

                targeted_anon_set_sizes -= rem_lists

            history.append(
                {
                    "len_anon_set": int(anon_set.sum()),
                    "len_mask": int(mask.__abs__().sum()),
                }
            )

    return mask, history, timer.measurements


def fingerprint_user(
    shared_data, uid, debug=False, wandb_run=None, filterlist_aware=False
):

    if filterlist_aware:
        fingerprint_method = _greedy_individual_fingerprint_filterlist_aware
    else:
        fingerprint_method = _greedy_individual_fingerprint

    try:

        timer = Timer(log_func=lambda x: print(f"[TASK {uid}]: {x}"))

        with timer("fingerprint"):
            mask, history, timer_measurements = fingerprint_method(shared_data, uid)

        mask = np.where(mask > 0)[0].tolist() + [
            -x if x != 0 else -0.01 for x in np.where(mask < 0)[0].tolist()
        ]

        # TODO: Temporary fix to save the results as it takes too long to run

        print(
            f"User {uid}: mask size: {len(mask)}, anon_set size: {history[-1]['len_anon_set']}"
        )

        if wandb_run:
            wandb_run.log(
                {
                    "mask_size": len(mask),
                    "anon_set_size": history[-1]["len_anon_set"],
                    "time": timer.measurements["fingerprint"][0],
                }
            )

        if not debug:
            os.makedirs("users", exist_ok=True)
            os.makedirs("stats/timer_measurements", exist_ok=True)

            out = {
                "best_mask": json.dumps(mask),
                "history": json.dumps(history),
                "max_size": len(mask),
                "min_anon_set": history[-1]["len_anon_set"],
                "unique": history[-1]["len_anon_set"] <= 1,
                "time": timer.measurements["fingerprint"][0],
            }

            json.dump(out, open(f"users/{uid}.json", "w"))
            json.dump(
                timer_measurements | {"total": [out["time"]]},
                open(f"stats/{uid}.json", "w"),
            )

    except Exception as e:
        print(f"Error in user {uid}: {e}")
        traceback.print_exc()
        mask = []
        history = []
        timer_measurements = {}

    return mask, history, timer_measurements | timer.measurements


def targeted_fingerprinting(
    user_rules: pd.DataFrame,
    rules_map,
    algorithm="greedy",
    n_users: Optional[int] = None,
    i_process: Optional[list] = None,
    debug=False,
    force=False,
    wandb_run=None,
    filterlist_rules: Optional[pd.DataFrame] = None,
):
    """

    If filterlist_rules is set, the fingerprinting is filterlist_aware

    """

    filterlist_aware = filterlist_rules is not None

    if n_users:
        user_rules = user_rules.head(n_users)

    user_attrs = prepare_rules(user_rules, len(rules_map))

    users_to_process = (
        list(range(user_attrs.shape[0])) if i_process is None else i_process
    )

    # if not forced, get existing results
    if not force and os.path.exists("users"):
        # all file names in the ./users directory
        existing_results = [
            int(f.split(".")[0]) for f in os.listdir("users") if f.endswith(".json")
        ]
        # remove existing results from the users_to_process list
        users_to_process = [u for u in users_to_process if u not in existing_results]

    with SharedMemoryManager() as smm:

        shared_data = prepare_readonly_user_data(user_attrs, smm)

        if filterlist_aware:
            filterlist_rules = prepare_rules(filterlist_rules, len(rules_map))
            shared_data += prepare_readonly_filterlist_data(filterlist_rules, smm)

        # parallelbar seems to hang indefinitely at waiter.acquire()
        results = progress_starmap(
            fingerprint_user,
            [
                (shared_data, i, debug, wandb_run, filterlist_aware)
                for i in users_to_process
            ],
            n_cpu=N_CPU,
        )

    return results
