from common import *

Title("Reducing User Anonymity (Section 6.2)")


# GET THE GENERAL ANONYMITY STATISTICS

ISSUES_DIRS = {
    "adguard": (DATA_DIR / Path("./filterlists/adguard/fingerprint")).resolve(),
    "ublock": (DATA_DIR / Path("./filterlists/ublock/fingerprint")).resolve(),
}

ADBLOCKERS = ["adguard", "ublock"]
ATTACK_NAMES = [
    "baseline",
    "css-animation-attack",
    "stat-generic-cosmetic",
]

ATTACK_DATASETS = {
    dataset
    + " "
    + attack_name: pd.read_csv(
        issues_dir / f"{attack_name}/issues_confs_identified.csv"
    )
    for dataset, issues_dir in ISSUES_DIRS.items()
    for attack_name in ATTACK_NAMES
    if (issues_dir / f"{attack_name}/issues_confs_identified.csv").exists()
}
ATTACK_FILTERLIST_STATS = {
    dataset
    + " "
    + attack_name: pd.read_csv(issues_dir / f"{attack_name}/unique_counts.csv")
    for dataset, issues_dir in ISSUES_DIRS.items()
    for attack_name in ATTACK_NAMES
    if (issues_dir / f"{attack_name}/unique_counts.csv").exists()
}
ATTACK_RULES_DATASETS = {
    dataset
    + " "
    + attack_name: pd.read_csv(issues_dir / f"{attack_name}/user_rules.csv")
    for dataset, issues_dir in ISSUES_DIRS.items()
    for attack_name in ATTACK_NAMES
    if (issues_dir / f"{attack_name}/user_rules.csv").exists()
}

stats_df, *_ = stats.apply_to_datasets(
    lambda df: stats.issues_filterlists_statistics(
        df, variable_column="identifiable_unique_lists"
    ),
    ATTACK_DATASETS,
)
stats_df = stats_df.reset_index()

stats_df[["adblocker", "attack"]] = stats_df["index"].str.split(expand=True)
stats_df.drop(columns=["index"], inplace=True)

attack_renames = {
    "baseline": "Baseline attack",
    "css-animation-attack": "CSS animation attack (+ others)",
    "stat-generic-cosmetic": "Generic cosmetic rules only",
}

stats_df["attack"] = stats_df["attack"].apply(lambda x: attack_renames[x])
stats_df.drop(columns=["support", "mode", "mean", "std", "min", "max"], inplace=True)
stats_df = stats_df.rename(
    columns={
        "normalized_shannon_entropy": "Entropy",
        "unique_filterlists": "Unique Users",
    }
)

stats_df = stats_df[["adblocker", "attack", "Entropy", "Unique Users"]]
stats_df = stats_df.sort_values(by=["adblocker", "attack"])

stats_df[
    [
        "Targeted Unique Users",
        "Targeted m_max",
        "General Entropy",
        "General Unique Users",
        "General m",
    ]
] = ["-", "-", "-", "-", "-"]

# GET TARGETED and GENERIC FINGERPRINTING STATISTICS

for adblocker in ADBLOCKERS:
    for attack in ATTACK_NAMES:

        # Targeted fingerprinting stats
        attack_dir = DATA_DIR / Path(
            f"./fingerprinting/{adblocker}/{attack}/filterlist/targeted"
        )

        if not (attack_dir / "fingerprints.csv").exists():
            continue

        targeted_stats, *_ = stats.targeted_anon_set_stats(attack_dir, 10)

        stats_df.loc[
            (stats_df.adblocker == adblocker)
            & (stats_df.attack == attack_renames[attack]),
            "Targeted Unique Users",
        ] = targeted_stats["unique"]

        stats_df.loc[
            (stats_df.adblocker == adblocker)
            & (stats_df.attack == attack_renames[attack]),
            "Targeted m_max",
        ] = targeted_stats["max_size"]["max"]

        # General fingerprinting stats
        attack_dir = DATA_DIR / Path(
            f"./fingerprinting/{adblocker}/{attack}/filterlist/general"
        )
        general_stats = stats.general_fingerprinting_stats(
            attack_dir, unique_upper_bound=1
        )

        stats_df.loc[
            (stats_df.adblocker == adblocker)
            & (stats_df.attack == attack_renames[attack]),
            "General Entropy",
        ] = general_stats["max_entropy"]

        stats_df.loc[
            (stats_df.adblocker == adblocker)
            & (stats_df.attack == attack_renames[attack]),
            "General Unique Users",
        ] = general_stats["max_unique"]

        stats_df.loc[
            (stats_df.adblocker == adblocker)
            & (stats_df.attack == attack_renames[attack]),
            "General m",
        ] = general_stats["k"]

Header("Table 4: Statistics of attacks on collected datasets")
print(tabulate(stats_df, headers="keys", tablefmt="pretty"))
stats_df.to_csv(PAPER_FIGURES_DIR / Path("attack_stats.csv")) 

Header("Figure 2: Anon set size vs distance from default")

fig, ax = stats.anon_set_size_vs_rules_count(
    DATA_DIR
    / Path(f"./fingerprinting/adguard/css-animation-attack/filterlist/targeted"),
    DATA_DIR / Path(f"./filterlists/adguard/fingerprint/css-animation-attack"),
    yaml.safe_load(open(CONF_DIR / "filterlists/adguard.yaml")),
)

fig.savefig(
    PAPER_FIGURES_DIR / Path("anon_set_size_vs_rules_count.pdf"), bbox_inches="tight"
)

Link(
    "Figure 2 saved to: "
    + str(PAPER_FIGURES_DIR / Path("anon_set_size_vs_rules_count.pdf"))
)
