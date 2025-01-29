from common import *

CONF_DATASETS = {
    "adguard": pd.read_csv(ADGUARD_CONFS_DIR),
    "ublock": pd.read_csv(UBLOCK_CONFS_DIR),
    "ublock_dedup": pd.read_csv(UBLOCK_DEDUP_CONFS_DIR),
}

Title("Dataset Statistics (Section 5)")

Header("Post Counts")

filterlist_posts_stats, *_ = stats.apply_to_datasets(
    stats.issues_dataset_statistics, CONF_DATASETS
)
print(tabulate(filterlist_posts_stats, headers="keys", tablefmt="pretty"))

filterlist_posts_stats.to_csv(PAPER_FIGURES_DIR / Path("filterlist_posts_stats.csv"))


Header("Aguard Post Metadata and Advanced Privacy Features")


def get_stealth_mode(x):

    try:
        out = eval(x) if isinstance(x, str) else {}

        has_stealth_mode_options = (
            len(out.get("Stealth mode options", []))
            + len(out.get("Tracking protection options", []))
        ) > 0
        has_advanced_protection = (
            out.get("Advanced protection", "disabled") == "enabled"
        )
        stealth_mode_disabled = out.get("Stealth mode", "enabled") == "disabled"

        # if not has_stealth_mode_options and not stealth_mode_disabled and not has_advanced_protection:
        #     print(f"Stealth mode options not found in: {x}")

        return (
            has_stealth_mode_options,
            stealth_mode_disabled,
            has_advanced_protection,
            has_stealth_mode_options
            or not stealth_mode_disabled
            or has_advanced_protection,
        )

    except:
        raise ValueError(f"Error parsing: {x}")


df = CONF_DATASETS["adguard"].copy()
df[
    [
        "has_stealth_mode_options",
        "stealth_mode_disabled",
        "has_advanced_protection",
        "any_stealth_mode",
    ]
] = (
    df["conf_dict"].apply(get_stealth_mode).apply(pd.Series)
)

print(
    f"No. of issues with any stealth mode options: {len(df[df.any_stealth_mode])} ({len(df[df.any_stealth_mode]) / len(df) * 100:.2f}%)"
)
print(
    f"No. of issues with specific stealth mode options: {len(df[df.has_stealth_mode_options])} ({len(df[df.has_stealth_mode_options]) / len(df) * 100:.2f}%)"
)


Header(
    "Comparison Between Adguard Forum Popularity and Adguard-provided Filterlist Popularity"
)

ADGUARD_POPULARITY_FP = CURR_DIR / Path(
    "../statistics_from_adblockers/adguard_fl_popularity.csv"
)
ADGUARD_METADATA_FP = CURR_DIR / Path(
    "../statistics_from_adblockers/adguard_fl_metadata.json"
)
ADGUARD_PROJECT_METADATA_FP = CURR_DIR / Path("../../conf/filterlists/adguard.yaml")

# load data
adguard_popularity = pd.read_csv(ADGUARD_POPULARITY_FP)
adguard_metadata = json.load(open(ADGUARD_METADATA_FP))
adguard_project_metadata = yaml.safe_load(open(ADGUARD_PROJECT_METADATA_FP))["list"]
adguard_metadata_df = pd.DataFrame(adguard_metadata["filters"])
adguard_popularity = adguard_popularity.merge(
    adguard_metadata_df, left_on="list_id", right_on="filterId"
)

# remove the word filter if it occurs in the end of the name
adguard_popularity["name"] = adguard_popularity["name"].apply(
    lambda x: x[:-6] if x.endswith(" filter") else x
)


# for each name replace it with original if it is an alias
def normalize_name(name):
    for filter in adguard_project_metadata:
        if name.strip() == filter["name"]:
            return name
        if name.strip() in filter.get("aliases", []):
            return filter["name"]

    return name


adguard_popularity["name"] = adguard_popularity["name"].apply(normalize_name)

adguard_popularity = adguard_popularity[["list_id", "name", "count"]]

forum_users_choices = pd.read_csv(ADGUARD_CONFS_DIR)

_, _, forum_adguard_popularity = stats.filterlist_individual_statistics(
    forum_users_choices,
    top_k=30,
    figsize=(10, 2),
    list_info_metadata=adguard_project_metadata,
)
forum_adguard_popularity = forum_adguard_popularity.reset_index().rename(
    columns={"index": "name"}
)

# Jaccard similarity between indeces
global_lists_top_30 = set(
    adguard_popularity.sort_values(by="count", ascending=False).head(30)["name"]
)
forum_lists_top_30 = set(
    forum_adguard_popularity.sort_values(by="count", ascending=False).head(30)["name"]
)

jaccard = len(global_lists_top_30.intersection(forum_lists_top_30)) / len(
    global_lists_top_30.union(forum_lists_top_30)
)

print(f"Jaccard similarity between global and forum lists: {jaccard}")

print(f"Number of Global lists: {len(adguard_popularity)}")
print(f"Number of Forum lists: {len(forum_adguard_popularity)}")

# RBO similarity between indeces

import rbo


def rbo_similarity(list1, list2, p=0.9):

    return rbo.RankingSimilarity(list1, list2).rbo_ext()


rbo_res = rbo_similarity(
    adguard_popularity["name"].tolist(), forum_adguard_popularity["name"].tolist()
)
print(f"RBO similarity between global and forum lists: {rbo_res}")

# compute earth mover distance between the two distributions

frequencies_global = adguard_popularity.set_index("name")["count"]
frequencies_forum = forum_adguard_popularity.set_index("name")["count"]

# have the same index for both
frequencies_forum = frequencies_forum.reindex(frequencies_global.index, fill_value=0)
frequencies_global = frequencies_global.reindex(frequencies_forum.index, fill_value=0)


# normalize to become probabilities
frequencies_global = frequencies_global / frequencies_global.sum()
frequencies_forum = frequencies_forum / frequencies_forum.sum()

from scipy.stats import wasserstein_distance

emd = wasserstein_distance(frequencies_global, frequencies_forum)

print(f"Earth mover distance between global and forum lists: {emd}")

# Bar plot
import matplotlib.pyplot as plt

fig, ax = plt.subplots(figsize=(20, 5))

# drop Base filter

_frequencies_forum = frequencies_forum.drop("Base filter")
_frequencies_global = frequencies_global.drop("Base filter")

# frequencies_forum[:30].plot.bar(ax=ax, color='red', alpha=0.5, label='Forum')
# frequencies_global[:30].plot.bar(ax=ax, color='blue', alpha=0.5, label='Global')

_frequencies_forum.plot.bar(ax=ax, color="red", alpha=0.5, label="Forum")
_frequencies_global.plot.bar(ax=ax, color="blue", alpha=0.5, label="Global")

plt.legend()
plt.title("Global vs Forum filter list popularity")
plt.ylabel("Popularity")
plt.xlabel("Filter list")

out_fp = PAPER_FIGURES_DIR / Path("adguard_global_vs_forum_popularity.pdf")

plt.savefig(out_fp, bbox_inches="tight")

Link("Figure A2 saved to " + str(out_fp.absolute()))
