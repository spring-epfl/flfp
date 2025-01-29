from functools import reduce
import json
import random
from fingerprint.common import prepare, prepare_rules
from fingerprint.general import general_fingerprinting
import numpy as np
import pandas as pd
import pytest
from fingerprint.targeted_rules import targeted_fingerprinting as rule_targeted_fingerprinting
from fingerprint.general_rules import general_fingerprinting as rule_general_fingerprinting
from fingerprint.targeted import targeted_fingerprinting
from filterlist_parser.filterlist_subscriptions import decode_rules, encode_rules

def create_rule_sets(n_sets=10, n_rules=100, seed=1):
    rules = list(range(n_rules))
    random.seed(seed)
    return [random.sample(rules, random.randint(0, n_rules)) for _ in range(n_sets)]

def subscribe_users_randomly(filterlists, n_users=10):
    
    users_subscriptions = []
    
    for _ in range(n_users):
        subscriptions = random.sample(filterlists, random.randint(0, len(filterlists)))
        
        subscriptions = reduce(lambda a, b: set(a) | set(b), subscriptions, set())
        
        users_subscriptions.append(list(subscriptions))
        
    return users_subscriptions

def test_rule_encoding():
    
    users_subscriptions = create_rule_sets()
    
    for rules in users_subscriptions:
        encoded = encode_rules(rules, 100)
        decoded = decode_rules(encoded, 100)
        
        assert set(rules) == set(decoded)


    # empty rules
    assert decode_rules(encode_rules([], 100), 100) == []
    
    # all rules
    assert decode_rules(encode_rules(list(range(100)), 100), 100) == list(range(100))
    
    
def test_user_matrix():
    n_rules = 100
    users_subscriptions = create_rule_sets(n_sets=10,n_rules=n_rules)
    user_subscriptions_df = pd.DataFrame([{"index": i, "identifiable_lists": json.dumps(subcriptions)} for i, subcriptions in enumerate(users_subscriptions)])
    
    users, attrs, id_from_index = prepare(user_subscriptions_df)
    
    index_from_id = {v: k for k, v in id_from_index.items()}

    user_subscriptions_rules_df = pd.DataFrame([{"index": i, "rules": encode_rules([index_from_id[s] for s in subcriptions], n_rules).hex()} for i, subcriptions in enumerate(users_subscriptions)])
    
    user_attrs = prepare_rules(user_subscriptions_rules_df, n_rules)
    
    
    for i in range(len(users)):
        assert set(users[i]) == set(np.where(user_attrs[i])[0])
    
    for j in range(n_rules):
        assert set(attrs[j]) == set(np.where(user_attrs[:,j])[0])


def test_targeted_fingerprint():
    
    n_rules = 100
    users_subscriptions = create_rule_sets(n_sets=10,n_rules=n_rules)
        
    # rules setup
    
    # encode to expected rules matrix format
    user_subscriptions_df = pd.DataFrame([{"index": i, "identifiable_lists": json.dumps(subcriptions)} for i, subcriptions in enumerate(users_subscriptions)])
    
    results, id_from_index  = targeted_fingerprinting(user_subscriptions_df) 
    
    # non-optimized version
    # this function re-indexes so need to apply that to the next one
    index_from_id = {v: k for k, v in id_from_index.items()}

    user_subscriptions_rules_df = pd.DataFrame([{"index": i, "rules": encode_rules([index_from_id[s] for s in subcriptions], n_rules).hex()} for i, subcriptions in enumerate(users_subscriptions)])
    
    # fingerprinting
    results_rules = rule_targeted_fingerprinting(user_subscriptions_rules_df, {i: i for i in range(n_rules)}, debug=True)

    for (mask_rule, history_rule, _), (mask, history) in zip(results_rules, results):
        
        assert set(mask_rule) == set(mask)
        
        
def test_filterlist_aware_targeted_fingerprint():
    
    n_rules = 500
    n_lists = 20
    
    filterlist_rules = create_rule_sets(n_sets=n_lists,n_rules=n_rules)
    users_subscriptions = subscribe_users_randomly(filterlist_rules, n_users=100)
    
    
    # rules setup
    # encode to expected rules matrix format
    user_subscriptions_df = pd.DataFrame([{"index": i, "identifiable_lists": json.dumps(subcriptions)} for i, subcriptions in enumerate(users_subscriptions)])
    
    results, id_from_index  = targeted_fingerprinting(user_subscriptions_df)
    
    # non-optimized version
    # this function re-indexes so need to apply that to the next one
    index_from_id = {v: k for k, v in id_from_index.items()}
    
    user_subscriptions_rules_df = pd.DataFrame([{"index": i, "rules": encode_rules([index_from_id[s] for s in subcriptions], n_rules).hex()} for i, subcriptions in enumerate(users_subscriptions)])
    filterlist_rules_df = pd.DataFrame([{"index": i, "rules": encode_rules(subcriptions, n_rules).hex()} for i, subcriptions in enumerate(filterlist_rules)])
    # fingerprinting
    results_rules_aware = rule_targeted_fingerprinting(user_subscriptions_rules_df, {i: i for i in range(n_rules)}, debug=True, filterlist_rules = filterlist_rules_df)
    results_rules = rule_targeted_fingerprinting(user_subscriptions_rules_df, {i: i for i in range(n_rules)}, debug=True)
    
    for (mask_rule_aware, history_rule_aware, _),(mask_rule, history_rule, _) , (mask, history) in zip(results_rules_aware, results_rules, results):
        assert set(mask_rule_aware) == set(mask) == set(mask_rule)
    
        
def test_general_fingerprint():
    
    n_rules = 100
    users_subscriptions = create_rule_sets(n_sets=10,n_rules=n_rules)
        
    # rules setup
    
    # encode to expected rules matrix format
    user_subscriptions_df = pd.DataFrame([{"index": i, "identifiable_lists": json.dumps(subcriptions)} for i, subcriptions in enumerate(users_subscriptions)])
    
    for k in range(2,10):
        results, id_from_index  = general_fingerprinting(user_subscriptions_df, k) 
        
        # non-optimized version
        # this function re-indexes so need to apply that to the next one
        index_from_id = {v: k for k, v in id_from_index.items()}

        user_subscriptions_rules_df = pd.DataFrame([{"index": i, "rules": encode_rules([index_from_id[s] for s in subcriptions], n_rules).hex()} for i, subcriptions in enumerate(users_subscriptions)])
    
        results_rules = rule_general_fingerprinting(user_subscriptions_rules_df, {i: i for i in range(n_rules)}, k )
        
        assert set(results[0]) == set(results_rules[0])
        assert results[1] == results_rules[1]
        assert results[2] == results_rules[2]
        