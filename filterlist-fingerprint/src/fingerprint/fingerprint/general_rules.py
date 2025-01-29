#!/usr/bin/python

import numpy as np
import pandas as pd
from tqdm import tqdm

from fingerprint.common import prepare_rules


class GeneralFingerprinting:
    """Wrapper for the General fingerprinting algorithm based on the flattened rule construct"""
    
    k: int
    users_attrs: list

    def __init__(self, k, users_attrs: np.array):
        self.users_attrs = users_attrs
        self.attrs_users = users_attrs.T

        self.k = min(k, self.attrs_users.shape[0])

    def greedy_group_fingerprinting(self):

        user_num = self.users_attrs.shape[0]

        scores = -abs(user_num / 2 - np.sum(self.attrs_users, axis=1))

        best_item = np.argmax(scores)

        class1 = self.attrs_users[best_item].copy()

        e_classes = [class1, ~class1]

        # signature set of possible items
        sig_set = np.zeros(self.attrs_users.shape[0], dtype=bool)

        sig_set[best_item] = True

        with tqdm(total=len(e_classes)) as pbar:
            while sig_set.sum() < self.k and len(e_classes) < user_num:
                # separation metric: number of pairs that the item separates
                sep_metrics = np.zeros(self.attrs_users.shape[0], dtype=int)

                # for class in e_classes that contain more than one user
                # TODO: loop parallelizable in threads
                for i, e_class in enumerate(e_classes):

                    # items for any user in class that are not in signature
                    items_occurances = (~sig_set) * self.attrs_users[:, e_class].sum(
                        axis=1
                    )

                    sep_metrics += items_occurances * (e_class.sum() - items_occurances)

                    pbar.update(1)

                best_metric = np.max(sep_metrics)
                best_item = np.argmax(sep_metrics)

                if best_metric == 0:
                    tqdm.write("No more useful separators found")
                    break

                new_classes = []

                user_set = self.attrs_users[best_item]

                # Division into subpartitions
                for e_class in e_classes:

                    new_set1 = e_class & ~user_set
                    new_set2 = e_class & ~new_set1

                    if new_set1.any() and new_set2.any():
                        new_classes.extend([new_set1, new_set2])
                    else:
                        new_classes.append(e_class)

                e_classes = new_classes
                sig_set[best_item] = True

                # finish the progress bar
                pbar.update(pbar.total - pbar.n)

        # transform to lists
        e_classes = [np.where(e_class)[0].tolist() for e_class in e_classes]
        signature = np.where(sig_set)[0].tolist()

        return signature, e_classes, int(best_metric)


def general_fingerprinting(user_rules: pd.DataFrame, rule_map, k):
    """General fingerprinting algorithm using rule mode"""

    user_attrs = prepare_rules(user_rules, len(rule_map))

    fingerprinter = GeneralFingerprinting(k, user_attrs)

    return fingerprinter.greedy_group_fingerprinting()
