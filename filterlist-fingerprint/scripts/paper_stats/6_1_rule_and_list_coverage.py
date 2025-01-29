from common import *

Title("Rule and List Coverage (Section 6.1)")

Header(
    "Table 3: The number of detectable lists, equivalence sets, and testable rules for each attack."
)

ATTACK_NAMES = [
    "default",
    "stat-generic",
    "stat-generic-network",
    "stat-generic-cosmetic",
    "baseline",
    "css-animation-attack",
]

ATTACK_DATASETS = {
    ADBLOCKER
    + " "
    + attack: (
        DATA_DIR / f"./filterlists/{ADBLOCKER}/fingerprint/{attack}/unique_counts.csv",
        # mapping
        DATA_DIR
        / f"./filterlists/{ADBLOCKER}/fingerprint/{attack}/unique_filterlist_sets.json",
        # targeted fingerprints
        DATA_DIR
        / f"./fingerprinting/{ADBLOCKER}/{attack}/filterlist/targeted/fingerprints.csv",
        # general fingerprint
        DATA_DIR
        / f"./fingerprinting/{ADBLOCKER}/{attack}/filterlist/general/max_size:90/fingerprint.json",
    )
    for ADBLOCKER in ["adguard", "ublock"]
    for attack in ATTACK_NAMES
}

stat_df, _ = stats.apply_to_datasets(
    lambda tup: stats.equivalent_list_set_stats(*tup), ATTACK_DATASETS
)

stat_df = stat_df.reset_index()
stat_df = stat_df[["index", "n_unique_lists", "n_list_sets", "n_allowed_rules"]]
stat_df[["adblocker", "attack"]] = stat_df["index"].str.split(expand=True)
stat_df.drop(columns=["index"], inplace=True)

attack_renames = {
    "default": "All rules",
    "stat-generic": "Generic rules",
    "stat-generic-network": "Generic network rules",
    "stat-generic-cosmetic": "Generic cosmetic rules",
    "baseline": "Baseline attack",
    "css-animation-attack": "CSS animation attack (+ others)",
}

stat_df["attack"] = stat_df["attack"].apply(lambda x: attack_renames[x])

adguard_stats = stat_df[stat_df.adblocker == "adguard"].copy()
ublock_stats = stat_df[stat_df.adblocker == "ublock"].copy()

for adblocker_stat in [adguard_stats, ublock_stats]:
    adblocker_stat.drop(columns=["adblocker"], inplace=True)
    adblocker_stat.set_index("attack", inplace=True)
    adblocker = "Adguard" if adblocker_stat is adguard_stats else "uBlock Origin"
    print(adblocker)
    print(tabulate(adblocker_stat, headers="keys", tablefmt="pretty"))
    adblocker_stat.to_csv(
        PAPER_FIGURES_DIR / Path(f"rule_list_coverage_{adblocker}_{adblocker_stat.index[0]}.csv")
    )
