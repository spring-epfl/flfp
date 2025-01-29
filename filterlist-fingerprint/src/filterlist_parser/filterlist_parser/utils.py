"""Utility functions for the filterlist parser"""

from __future__ import absolute_import

import json
from typing import Iterable, List

import numpy as np
import pandas as pd


class FilterlistDoesNotExist(KeyError):
    """Raised when a filterlist does not exist"""


def get_filterlist_name_resolutions(filterlists: Iterable[dict]) -> dict:
    """
    Get a dictionary to resolve aliases to the default name

    Returns a dictionary with an alias as key and the default name as value
    """

    name_resolutions = {}

    for filterlist in filterlists:
        name_resolutions[filterlist["name"]] = filterlist["name"]

        if "aliases" in filterlist:
            for alias in filterlist["aliases"]:
                name_resolutions[alias] = filterlist["name"]

    return name_resolutions


def slug(name: str) -> str:
    """Convert a name to a slug"""
    return (
        name.lower()
        .replace(" ", "-")
        .replace("/", "-")
        .replace(".", "-")
        .replace(",", "-")
    )


def filterlist_to_tuple(filterlist_json: str):
    """Convert a filterlist configuration JSON to a tuple"""
    ls = list(json.loads(filterlist_json))
    ls = sorted(ls)
    return tuple(ls)


def split_data(iterable, pred):
    """
    Split data from ``iterable`` into two lists.
    Each element is passed to function ``pred``; elements
    for which ``pred`` returns True are put into ``yes`` list,
    other elements are put into ``no`` list.

    >>> split_data(["foo", "Bar", "Spam", "egg"], lambda t: t.istitle())
    (['Bar', 'Spam'], ['foo', 'egg'])
    """
    yes, no = [], []
    for d in iterable:
        if pred(d):
            yes.append(d)
        else:
            no.append(d)
    return yes, no
