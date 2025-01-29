from datetime import datetime, timezone
from common import *

Title("Stability of Filterlists (Section 6.3)")

Header("Commit Frequency (Unit in Minutes)")

# TODO: add the commit parse back
COMMITS_DATASETS = {
    "adguard": pd.read_csv(ADGUARD_COMMITS_FP),
    "ublock": pd.read_csv(UBLOCK_COMMITS_FP),
}

commit_freq_df, *_ = stats.apply_to_datasets(
    lambda df: stats.intercommit_time_and_n_changes_stats(df, lambda row: True),
    COMMITS_DATASETS,
    is_notebook=False,
)

commit_freq_df.drop(columns=["count"], inplace=True)
commit_freq_df[["mean", "std", "min", "25%", "50%", "75%", "max"]] = (
    commit_freq_df[["mean", "std", "min", "25%", "50%", "75%", "max"]] * 60
)


print(tabulate(commit_freq_df, headers="keys", tablefmt="pretty"))
commit_freq_df.to_csv(PAPER_FIGURES_DIR / "commit_frequency.csv")


Header("Rule Stability")
colors = ["r", "b"]

ATTACK_NAMES = [
    "css-animation-attack",
]

RENAMES = {"css-animation-attack": "CSS animation attack"}

RULE_LAST_SEEN_DATASETS = {
    "adguard": (
        ADGUARD_RULE_LAST_SEEN_DOWNLOAD_TIMESTAMP,
        pd.read_csv(ADGUARD_RULE_LAST_SEEN_FP),
    ),
    "ublock": (
        UBLOCK_RULE_LAST_SEEN_DOWNLOAD_TIMESTAMP,
        pd.read_csv(UBLOCK_RULE_LAST_SEEN_FP),
    ),
}

stability_general_df, extra_data = stats.apply_to_datasets(
    lambda x: stats.rule_last_seen_statistics(*x, figsize=(10, 2)),
    RULE_LAST_SEEN_DATASETS,
)

ATTACK_IMPORTANT_RULES = {
    adblocker
    + ": "
    + attack_name: pd.read_csv(
        DATA_DIR
        / f"fingerprinting/{adblocker}/{attack_name}/filterlist/summary/general_important_rules.csv"
    )
    for adblocker in ["adguard", "ublock"]
    for attack_name in ATTACK_NAMES
    if Path(
        DATA_DIR
        / f"fingerprinting/{adblocker}/{attack_name}/filterlist/summary/general_important_rules.csv"
    ).exists()
}

RULE_LAST_SEEN_ATTACK_BREAKDOWN = {}

for adblocker_attack_name, important_rules in ATTACK_IMPORTANT_RULES.items():
    adblocker, attack_name = adblocker_attack_name.split(": ")
    download_timestamp, rules_last_seen = RULE_LAST_SEEN_DATASETS[adblocker]
    rules_last_seen = rules_last_seen[
        rules_last_seen["rule"].isin(important_rules["rule"])
    ]
    RULE_LAST_SEEN_ATTACK_BREAKDOWN[adblocker_attack_name] = (
        download_timestamp,
        rules_last_seen,
    )

stability_attack_df, extra_breakdown = stats.apply_to_datasets(
    lambda x: stats.rule_last_seen_statistics(*x, figsize=(10, 2)),
    RULE_LAST_SEEN_ATTACK_BREAKDOWN,
)

stability_general_df = stability_general_df.reset_index()
stability_general_df["adblocker"] = stability_general_df["index"]
stability_general_df["attack"] = "All rules"
stability_general_df.drop(columns=["index"], inplace=True)

stability_attack_df = stability_attack_df.reset_index()
stability_attack_df["adblocker"] = stability_attack_df["index"].apply(
    lambda x: x.split(": ")[0]
)
stability_attack_df["attack"] = stability_attack_df["index"].apply(
    lambda x: x.split(": ")[1]
)
stability_attack_df.drop(columns=["index"], inplace=True)

stability_df = pd.concat([stability_general_df, stability_attack_df])
stability_df.sort_values(by=["adblocker", "attack"], inplace=True)
stability_df = stability_df[
    ["adblocker", "attack", *stability_df.columns.difference(["adblocker", "attack"])]
]

stability_df["attack"] = stability_df["attack"].apply(lambda x: RENAMES.get(x, x))

print(tabulate(stability_df, headers="keys", tablefmt="pretty"))
stability_df.to_csv(PAPER_FIGURES_DIR / "rule_stability.csv")

# only for css-animation-attack
css_animation_indeces = []
for i, name in enumerate(RULE_LAST_SEEN_ATTACK_BREAKDOWN.keys()):
    if "css-animation-attack" in name:
        css_animation_indeces.append(i)


_extra_breakdowns = [extra_breakdown[i] for i in css_animation_indeces]


fig, axes = plt.subplots(2, 1, figsize=(10, 4), sharex=True)

ax = axes[0]
ax2 = axes[1]

ax.set_title("CDF of rules older than a given period")


def plot(ax, extra_data):
    for i, (adblocker, (heights, x_labels)) in enumerate(
        zip(RULE_LAST_SEEN_DATASETS.keys(), extra_data)
    ):

        ax.plot(
            x_labels, heights, label=adblocker.upper(), color=colors[i], linewidth=2
        )

    ax.set_xticks(ax.get_xticks())
    ax.set_xticklabels([int(i) for i in np.absolute(ax.get_xticks())])


plot(ax, extra_data)
plot(ax2, _extra_breakdowns)

ax.legend(loc="upper left")
ax2.set_xlabel("Number of days since download")


plt.savefig(PAPER_FIGURES_DIR / "rule_stability.pdf", bbox_inches="tight")


Link("Figure 3 saved to " + str(PAPER_FIGURES_DIR / "rule_stability.pdf"))


Header("Equivalence Set Stability")

ATTACK_EQUIVALENT_SET_AND_RULES = {}

for adblocker_and_attack_name, important_rules in ATTACK_IMPORTANT_RULES.items():
    adblocker, attack_name = adblocker_and_attack_name.split(": ")
    equivalent_set_rules = ATTACK_IMPORTANT_RULES[adblocker_and_attack_name]
    download_timestamp, rule_last_seen = RULE_LAST_SEEN_DATASETS[adblocker]

    ATTACK_EQUIVALENT_SET_AND_RULES[adblocker_and_attack_name] = (
        download_timestamp,
        equivalent_set_rules,
        rule_last_seen,
    )

equiv_stability_df, _ = stats.apply_to_datasets(
    lambda x: stats.equivalent_set_max_last_seen_statistics(*x, figsize=(10, 2)),
    ATTACK_EQUIVALENT_SET_AND_RULES,
    is_notebook=False,
)

equiv_stability_df = equiv_stability_df.reset_index()
equiv_stability_df["adblocker"] = equiv_stability_df["index"].apply(
    lambda x: x.split(": ")[0]
)
equiv_stability_df["attack"] = equiv_stability_df["index"].apply(
    lambda x: x.split(": ")[1]
)
equiv_stability_df.drop(columns=["index"], inplace=True)

equiv_stability_df = equiv_stability_df[
    [
        "adblocker",
        "attack",
        *equiv_stability_df.columns.difference(["adblocker", "attack"]),
    ]
]

equiv_stability_df["attack"] = equiv_stability_df["attack"].apply(
    lambda x: RENAMES.get(x, x)
)
print(tabulate(equiv_stability_df, headers="keys", tablefmt="pretty"))
equiv_stability_df.to_csv(PAPER_FIGURES_DIR / "equiv_stability.csv")