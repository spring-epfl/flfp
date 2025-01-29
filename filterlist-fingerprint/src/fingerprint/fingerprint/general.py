#!/usr/bin/python

from collections import Counter
from functools import reduce
from tqdm import tqdm
import pandas as pd

from fingerprint.common import prepare

class GeneralFingerprinting:
    """Wrapper for the General fingerprinting algorithm based on the equivalence set setup"""
    
    k: int
    users_attrs: list
    attrs_users: list

    def __init__(self, k, users_attrs, attrs_users):
        self.users_attrs = [set(users_attrs[key]) for key in sorted(users_attrs.keys())]
        self.attrs_users = [set(attrs_users[key]) for key in sorted(attrs_users.keys())]
        self.k = min(k, len(self.attrs_users))

    def greedy_group_fingerprinting(self):

        user_num = len(self.users_attrs)

        best_item = None
        max_score = None

        for i, users in enumerate(self.attrs_users):

            score = -abs(user_num / 2 - len(users))

            if max_score is None or score > max_score:
                max_score = score
                best_item = i

        class1 = set(self.attrs_users[best_item])

        e_classes = [class1, set(range(user_num)) - class1]

        signature = [best_item]
        sig_set = set(signature)

        with tqdm(total=len(e_classes)) as pbar:
            while len(signature) < self.k and len(e_classes) < user_num:
                # separation metric: number of pairs that the item separates
                sep_metric = Counter()

                for i, e_class in enumerate(e_classes):
                    if len(e_class) == 1:
                        continue

                    items = set()
                    for user in e_class:
                        items |= self.users_attrs[user]

                    for item in items:
                        if item in sig_set:
                            continue

                        occurence = reduce(
                            lambda x, y: x + (item in self.users_attrs[y]), e_class, 0
                        )

                        sep_metric[item] += occurence * (len(e_class) - occurence)

                    pbar.update(1)

                (best_item, best_metric) = sep_metric.most_common(1)[0]

                if best_metric == 0:
                    tqdm.write("No more useful separators found")
                    break

                new_classes = []

                # Division into subpartitions
                for e_class in e_classes:
                    user_set = set(self.attrs_users[best_item])

                    new_set1 = e_class - user_set
                    new_set2 = e_class - new_set1

                    if len(new_set1) > 0 and len(new_set2) > 0:
                        new_classes.extend([new_set1, new_set2])
                    else:
                        new_classes.append(e_class)

                e_classes = new_classes
                signature.append(best_item)
                sig_set.add(best_item)

                # finish the progress bar
                pbar.update(pbar.total - pbar.n)

        # transform to lists
        e_classes = [list(e_class) for e_class in e_classes]

        return signature, e_classes, best_metric


def general_fingerprinting(
    user_subscriptions: pd.DataFrame, k, col="identifiable_lists"
) -> tuple:
    """General fingerprinting algorithm using list mode"""

    users, attrs, listname_from_index = prepare(user_subscriptions, col=col)

    fingerprinter = GeneralFingerprinting(k, users, attrs)

    return fingerprinter.greedy_group_fingerprinting(), listname_from_index
