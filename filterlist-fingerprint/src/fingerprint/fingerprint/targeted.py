# Reference: https://github.com/gaborgulyas/constrainted_fingerprinting/blob/master/03_individual_fingerprints_faster.py

from typing import Optional
import pandas as pd
from parallelbar import progress_map
from dotenv import load_dotenv
import os

from fingerprint.common import prepare

load_dotenv()

N_CPU = int(os.getenv("N_CPU", "4"))


class GreedyTargetedFingerprinting:
    """Wrapper for the Targeted fingerprinting algorithm based on the equivalence set setup"""

    users: dict
    attrs: dict

    def __init__(self, users, attrs):
        self.users = users
        self.attrs = attrs

    def _greedy_individual_fingerprint(self, uid):
        user_set = set(self.users.keys())
        users = {}
        for a in self.attrs.keys():
            if len(self.attrs[a]) == 0:
                continue

            if a in self.users[uid]:
                users[a] = self.attrs[a]
            else:
                users[a] = user_set - self.attrs[a]

        mask = []
        anon_set = set(self.users.keys())

        history = []

        while len(anon_set) > 1:
            avail_attrs = set(users.keys()) - set(mask)

            min_a = None
            for a in avail_attrs:
                if min_a == None:
                    min_a = a
                    continue

                if len(users[a] & anon_set) < len(users[min_a] & anon_set):
                    min_a = a

            if min_a is None or len(users[min_a] & anon_set) == len(anon_set):
                break

            if min_a in self.users[uid]:
                mask.append(min_a)
            else:
                if min_a == 0:
                    mask.append(
                        -0.01
                    )  # otherwise sign of 0 could not be distinguished (remained due to "historical" reasons :) )
                else:
                    mask.append(-min_a)

            anon_set = anon_set & users[min_a]

            history.append({"len_anon_set": len(anon_set), "len_mask": len(mask)})

        return mask, history

    def best_mask(self, uid):
        return self._greedy_individual_fingerprint(uid)


class FastTargetedFingerprinting:

    users: list
    attrs: list

    def __init__(self, users, attrs):
        self.users = users
        self.attrs = attrs

    def _get_minmax_attrs(self, _uid, _mask):

        pos_mask = {int(x) for x in _mask if x >= 0.0}
        neg_mask = {int(abs(x)) for x in _mask if x < 0.0}
        mask = neg_mask | pos_mask

        users_tmp = {}
        attrs_tmp = {}
        if _mask == []:
            users_tmp = {ix: user for ix, user in self.users.items()}
            attrs_tmp = {ix: attr for ix, attr in self.attrs.items()}
        else:
            for ix, user in self.users.items():
                if (
                    ix != _uid
                    and pos_mask.issubset(set(user))
                    and (neg_mask & set(user))
                ):
                    users_tmp[ix] = user
                    for f in users_tmp[ix]:
                        if f not in attrs_tmp:
                            attrs_tmp[f] = [ix]
                        else:
                            attrs_tmp[f].append(ix)

        min_f = None
        max_f = None
        for f in attrs_tmp.keys():
            if f not in mask:
                if f in self.users[_uid]:
                    if min_f == None or len(attrs_tmp[f]) < len(attrs_tmp[min_f]):
                        min_f = f

                if f not in self.users[_uid]:
                    if max_f == None or len(attrs_tmp[f]) > len(attrs_tmp[max_f]):
                        max_f = f

        min_p = 1.0
        if min_f in attrs_tmp.keys():
            min_p = float(len(attrs_tmp[min_f])) / float(len(users_tmp))
        max_p = 1.0
        if max_f in attrs_tmp.keys():
            max_p = 1.0 - float(len(attrs_tmp[max_f])) / float(len(users_tmp))

        return min_f, min_p, max_f, max_p

    def _cut_it(self, _uid, _mask):
        (min_f, min_p, max_f, max_p) = self._get_minmax_attrs(_uid, _mask)

        if min_f is None or max_f is None:
            return _mask

        if min_p <= max_p:
            if min_f == 0:
                _mask.append(0.01)
            else:
                _mask.append(min_f)
            return self._cut_it(_uid, _mask)
        else:
            if max_f == 0:
                _mask.append(-0.01)
            else:
                _mask.append(-1 * max_f)
            return self._cut_it(_uid, _mask)

    def best_mask(self, _uid):
        """Find the best fingerprinting template for a user"""
        return self._cut_it(_uid, []), []


def targeted_fingerprinting(
    user_subscriptions: pd.DataFrame,
    algorithm="greedy",
    n_users: Optional[int] = None,
    i_process: Optional[list] = None,
    col="identifiable_lists",
):
    """Targeted fingerprinting algorithm"""

    if n_users:
        user_subscriptions = user_subscriptions.head(n_users)

    users, attrs, listname_from_index = prepare(user_subscriptions, col)

    _algorithm = None
    if algorithm == "greedy":
        _algorithm = GreedyTargetedFingerprinting(users, attrs)
    elif algorithm == "fast":
        _algorithm = FastTargetedFingerprinting(users, attrs)
    else:
        raise ValueError("Unknown algorithm")

    users_to_process = users.keys() if i_process is None else i_process
    results = progress_map(_algorithm.best_mask, users_to_process, n_cpu=N_CPU)

    return results, listname_from_index
