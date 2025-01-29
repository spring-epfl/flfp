from tqdm import tqdm
from common import *

# make logger silent
import logging
logging.getLogger().setLevel(logging.CRITICAL)

Title("Utility of Domain-Specific Filter Rules (Section 6.4)")

print("Might take a while to run...")

Header("Table 5: The impact of controlling specific domains on the filter-list coverage for AdGuard, broken down by rule type.")


def clean_domains(df):
    BAD_DOMAINS_PREFIX = [
        "*",
        "nan",
        "[$",
        ".", 
        "/]",
        "/^",
        "/",
        "\\\\/",
        "~",
    ]

    return df[(df['domain'].str.startswith(tuple(BAD_DOMAINS_PREFIX)) == False)].copy()

TOTAL_LISTS = {
    "adguard": 84,
    "ublock": 68
}

LIST_IDENTIFIABLE_RULE_COUNTS = {
    
    "adguard":{
        "all": pd.read_csv(DATA_DIR / 'filterlists/adguard/fingerprint/stat-generic/unique_counts.csv'),
        "cosmetic": pd.read_csv(DATA_DIR / 'filterlists/adguard/fingerprint/stat-generic-cosmetic/unique_counts.csv'),
        "network": pd.read_csv(DATA_DIR / 'filterlists/adguard/fingerprint/stat-generic-network/unique_counts.csv'),
    },
    
    "ublock":{
        "all": pd.read_csv(DATA_DIR / 'filterlists/ublock/fingerprint/stat-generic/unique_counts.csv'),
        "cosmetic": pd.read_csv(DATA_DIR / 'filterlists/ublock/fingerprint/stat-generic-cosmetic/unique_counts.csv'),
        "network": pd.read_csv(DATA_DIR / 'filterlists/ublock/fingerprint/stat-generic-network/unique_counts.csv'),
    }
}

DOMAIN_SPECIFIC_STATS = {
    "adguard": {
        "all": clean_domains(pd.read_csv(DATA_DIR / 'filterlists/adguard/domain_coverage/.analysis/coverage_count_rules.csv')),
        "cosmetic": clean_domains(pd.read_csv(DATA_DIR / 'filterlists/adguard/domain_coverage/.analysis/coverage_count_cosmetic_rules.csv')),
        "network": clean_domains(pd.read_csv(DATA_DIR / 'filterlists/adguard/domain_coverage/.analysis/coverage_count_network_rules.csv')),
    },
    "ublock": {
        "all": clean_domains(pd.read_csv(DATA_DIR / 'filterlists/ublock/domain_coverage/.analysis/coverage_count_rules.csv')),
        "cosmetic": clean_domains(pd.read_csv(DATA_DIR / 'filterlists/ublock/domain_coverage/.analysis/coverage_count_cosmetic_rules.csv')),
        "network": clean_domains(pd.read_csv(DATA_DIR / 'filterlists/ublock/domain_coverage/.analysis/coverage_count_network_rules.csv')),
    }
}

TOP_1K_DOMAINS = pd.read_csv(CONF_DIR / 'tranco_24P99.csv', header=None, names=['rank', 'domain'])


# All domains stats
print("All domains")

table = []

for adblocker in ["adguard", "ublock"]:
    for rule_type in ["all", "cosmetic", "network"]:
        domain_count = DOMAIN_SPECIFIC_STATS[adblocker][rule_type]
        table.append({"adblocker": adblocker, "rule_type": rule_type,**stats.domain_counts_stats(domain_count)})
        
        
stats_df = pd.DataFrame(table)
stats_df.rename(columns={
    "rule_type": "Rule Type",
    "adblocker": "Adblocker",
    "n_domains": "Unique Domains",
    "max_lists": "Max List Coverage",
    "median_lists": "Median List Coverage",
    "min_lists": "Min List Coverage",
    "max_rules": "Max Rule Coverage",
    "median_rules": "Median Rule Coverage",
    "min_rules": "Min Rule Coverage",
}, inplace=True)


stats_df[['Baseline Identifiable Lists', 'Max +L(1)', 'Max +L(inf)', 'Min. Domains for +L(inf)']] = ['-', '-', '-', '-']

for adblocker in ['adguard', 'ublock']:
    for list_type in tqdm(['all', 'cosmetic', 'network']):
        results, _ = stats.domain_coverage_stats(DOMAIN_SPECIFIC_STATS[adblocker][list_type], LIST_IDENTIFIABLE_RULE_COUNTS[adblocker][list_type], is_notebook=False)
        
        first_n_additional = results.iloc[0].n_additional_lists if len(results) else 0
        first_n_total = results.iloc[0].n_total_lists if len(results) else "N/A"
        last_n_total = results.iloc[-1].n_total_lists if len(results) else "N/A"
        min_domains = (results.n_additional_lists != 0).sum() if len(results) else "N/A"
        
        stats_df.loc[(stats_df['Adblocker'] == adblocker) & (stats_df['Rule Type'] == list_type), ['Baseline Identifiable Lists', 'Max +L(1)', 'Max +L(inf)', 'Min. Domains for +L(inf)']] = [f"{first_n_total - first_n_additional if len(results) else "N/A"} / {TOTAL_LISTS[adblocker]}", f"+{first_n_additional}", f"+{last_n_total - first_n_total + first_n_additional if len(results) else "N/A"}", min_domains]

print(tabulate(stats_df, headers="keys", tablefmt="pretty"))
stats_df.to_csv(PAPER_FIGURES_DIR / Path("domain_coverage_all.csv"), index=False)


# lower than 1K domains
print(" > 1K domains")

from run.domain_coverage import DomainTree

def filter_out_domains(df, domains):
    
    suffix_tree = DomainTree(list(df.domain.values))
    prefix_tree = DomainTree(list(df.domain.values), reverse=True)
    
    domains_to_remove = []
    
    for domain in domains:
        
        prefixes = prefix_tree.subsets_for(domain)
        suffixes = suffix_tree.subsets_for(domain)
        
        domains_to_remove.extend(prefixes)
        domains_to_remove.extend(suffixes)
        
    return df[df['domain'].isin(domains_to_remove) == False].copy()


table = []

for adblocker in ["adguard", "ublock"]:
    for rule_type in ["all", "cosmetic", "network"]:
        domain_count = DOMAIN_SPECIFIC_STATS[adblocker][rule_type]
        table.append({"adblocker": adblocker, "rule_type": rule_type,**stats.domain_counts_stats(filter_out_domains(domain_count, TOP_1K_DOMAINS.domain.values))})
        
        
stats_df = pd.DataFrame(table)
stats_df.rename(columns={
    "rule_type": "Rule Type",
    "adblocker": "Adblocker",
    "n_domains": "Unique Domains",
    "max_lists": "Max List Coverage",
    "median_lists": "Median List Coverage",
    "min_lists": "Min List Coverage",
    "max_rules": "Max Rule Coverage",
    "median_rules": "Median Rule Coverage",
    "min_rules": "Min Rule Coverage",
}, inplace=True)

stats_df[['Baseline Identifiable Lists', 'Max +L(1)', 'Max +L(inf)', 'Min. Domains for +L(inf)']] = ['-', '-', '-', '-']

for adblocker in ['adguard', 'ublock']:
    for list_type in tqdm(['all', 'cosmetic', 'network']):
        
        domain_count = DOMAIN_SPECIFIC_STATS[adblocker][rule_type]
        domain_count = filter_out_domains(domain_count, TOP_1K_DOMAINS.domain.values)
        results, _ = stats.domain_coverage_stats(domain_count, LIST_IDENTIFIABLE_RULE_COUNTS[adblocker][list_type], is_notebook=False)
        
        first_n_additional = results.iloc[0].n_additional_lists if len(results) else 0
        first_n_total = results.iloc[0].n_total_lists if len(results) else "N/A"
        last_n_total = results.iloc[-1].n_total_lists if len(results) else "N/A"
        min_domains = (results.n_additional_lists != 0).sum() if len(results) else "N/A"
        
        stats_df.loc[(stats_df['Adblocker'] == adblocker) & (stats_df['Rule Type'] == list_type), ['Baseline Identifiable Lists', 'Max +L(1)', 'Max +L(inf)', 'Min. Domains for +L(inf)']] = [f"{first_n_total - first_n_additional if len(results) else "N/A"} / {TOTAL_LISTS[adblocker]}", f"+{first_n_additional}", f"+{last_n_total - first_n_total + first_n_additional if len(results) else "N/A"}", min_domains]

print(tabulate(stats_df, headers="keys", tablefmt="pretty"))
stats_df.to_csv(PAPER_FIGURES_DIR / Path("domain_coverage.csv"), index=False)

