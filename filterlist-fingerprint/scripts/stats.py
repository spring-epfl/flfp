# UTILS
from datetime import datetime, timedelta
import json
import math
from pathlib import Path
from typing import Callable
from filterlist_parser.utils import filterlist_to_tuple, get_filterlist_name_resolutions
from matplotlib import pyplot as plt

import numpy as np
import pandas as pd

plt.style.use(
    {
        "axes.spines.left": True,
        "axes.spines.bottom": True,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "xtick.bottom": True,
        "ytick.left": True,
        "axes.grid": True,
        "grid.linestyle": ":",
        "grid.linewidth": 0.5,
        "grid.alpha": 0.5,
        "grid.color": "k",
        "axes.edgecolor": "k",
        "axes.linewidth": 0.5,
    }
)

# # use serif font
plt.rcParams["font.family"] = "serif"
plt.rcParams["font.serif"] = ["Times New Roman"] + plt.rcParams["font.serif"]

# # change text scaling
plt.rcParams.update({"font.size": 18})

# gray scale colors
plt.rcParams["axes.prop_cycle"] = plt.cycler(
    color=[
        "#000000",
        "#999999",
        "#666666",
        "#333333",
        "#666666",
        "#999999",
        "#000000",
    ]
)


from utils import logarithmic_bins, logarithmic_bins_base2


def num_and_percentage(x: int, total: int):
    return f"{x} ({x / total * 100:.2f}%)"


def hist_with_others(series, top_n=10, ommit_others=False, ax=None):
    hist = series.value_counts()
    hist = hist[:top_n]

    if not ommit_others:
        hist["others"] = len(series) - hist.sum()

    return hist.plot(kind="bar", ax=ax), hist


def normalized_shannon_entropy(frequencies: pd.Series):
    P = frequencies / frequencies.sum()
    N = len(frequencies)
    return -sum([p * math.log2(p) for p in P]) / math.log2(N)


def years_from_timestamps(time_values: pd.Series, ax=None):
    years = time_values.apply(lambda x: datetime.fromisoformat(x).year)
    return years


def plot_frequencies_over_time(df):

    # one plot different colors
    fig, ax = plt.subplots()

    df_plot = df[["valid", "created_at"]].copy()
    df_plot["created_at"] = years_from_timestamps(df_plot["created_at"])

    df_plot = df_plot.groupby(["created_at", "valid"]).size().unstack()

    df_plot.plot(kind="bar", stacked=True, ax=ax)
    ax.set_ylabel("Frequency")


def apply_to_datasets(func, datasets, is_notebook=False, **kwargs):

    _stats = []
    extras = []
    for name, df in datasets.items():
        data = func(df, **kwargs)

        if len(data) == 2:
            stats, plots = data
            extra = None
        elif len(data) == 3:
            stats, plots, extra = data

        _stats.append(stats)
        extras.append(extra)

        for fig, ax in plots.values():
            # add dataset name to the title
            ax.set_title(f"{name} - {ax.get_title()}")
            if is_notebook:
                plt.show(fig)

    df = pd.DataFrame(_stats, index=datasets)

    # if we are in a jupyter notebook display the table and the plots
    if is_notebook:
        display(df)

    return df, extras


def issues_dataset_statistics(df, only_valid=False, figsize=(15, 2)):

    fig, ax = plt.subplots(figsize=figsize)

    if only_valid:
        df = df[df.valid]
        
    # plot distribution of created_at
    created_ats = pd.to_datetime(df["created_at"])
    created_ats = created_ats.dt.tz_localize(None).dt.to_period("M")
    created_ats.value_counts().sort_index().plot(kind="bar", ax=ax)
    ax.set_title("Issues frequency over time")
    ax.set_ylabel("Frequency")
    ax.set_xlabel("Time")
    ax.invert_xaxis()
    return {
        "total": len(df),
        "valid": num_and_percentage(len(df[df["valid"]]), len(df)),
        "closed": num_and_percentage(len(df[df["is_closed"]]), len(df)),
        "earliest issue": df["created_at"].min().split("T")[0],
        "latest issue": df["created_at"].max().split("T")[0],
    }, {
        "issues_frequency_plot": (fig, ax),
    }


def issues_metadata_statistics(
    df, top_k_system_os=10, top_k_browsers=10, figsize=(5, 2)
):

    df_valid = df[df.valid]

    system_os_plot = plt.subplots(figsize=figsize)
    system_os_plot[1].set_title("OS")
    hist_with_others(
        df_valid.system_os[df_valid.system_os.notna()],
        top_n=top_k_system_os,
        ax=system_os_plot[1],
    )
    

    browser_plot = plt.subplots(figsize=figsize)
    browser_plot[1].set_title("Browsers")
    hist_with_others(
        df_valid.browser[df_valid.browser.notna()],
        top_n=top_k_browsers,
        ax=browser_plot[1],
    )
    
    # print the percentage of unique brwosers
    browser_freq = df_valid.browser[df_valid.browser.notna()].value_counts()
    browser_freq = browser_freq / browser_freq.sum() * 100
    
    return {
        "empty_system_os": num_and_percentage(
            len(df_valid[df_valid.system_os.isna()]), len(df_valid)
        ),
        "unique_system_os": num_and_percentage(
            len(df_valid.system_os.unique()), len(df_valid)
        ),
        "empty_browser": num_and_percentage(
            len(df_valid[df_valid.browser.isna()]), len(df_valid)
        ),
        "unique_browser": num_and_percentage(
            len(df_valid.browser.unique()), len(df_valid)
        ),
    }, {
        "system_os_frequency_plot": system_os_plot,
        "browser_frequency_plot": browser_plot,
    }


def attack_filterlists_statistics(df, figsize=(5, 2)):

    count_unique_sum = df.count_unique.sum()
    count_total_sum = df.count_total.sum()
    count_allowed_sum = df.count_allowed.sum()
    n_unique = (df.count_unique > 0).sum()

    return {
        "total": count_total_sum,
        "allowed": num_and_percentage(count_allowed_sum, count_total_sum),
        "unique": num_and_percentage(count_unique_sum, count_total_sum),
        "unique_filterlists": num_and_percentage(n_unique, len(df)),
    }, {}


def issues_filterlists_statistics(df, variable_column="filters", figsize=(5, 2)):

    df_valid = df[df.valid]

    filters = df_valid[variable_column].apply(filterlist_to_tuple)
    frequencies = filters.value_counts().values

    fig, ax = plt.subplots(figsize=figsize)
    ax.set_title("Filterlist combination frequency")
    hist_with_others(filters.apply(hash), ax=ax)

    return {
        "support": len(df_valid),
        "normalized_shannon_entropy": normalized_shannon_entropy(frequencies),
        "unique_filterlists": num_and_percentage(len(filters.unique()), len(df_valid)),
        "mode": num_and_percentage(frequencies[0], len(df_valid)),
        "mean": frequencies.mean(),
        "std": frequencies.std(),
        "min": frequencies.min(),
        "max": frequencies.max(),
    }, {"filterlist_combination_frequency_plot": (fig, ax)}


def issues_direct_rules_statistics(df, figsize=(5, 2)):

    fingerprints = df.rules
    frequencies = fingerprints.value_counts().values

    fig, ax = plt.subplots(figsize=figsize)
    ax.set_title("Direct rules frequency")
    hist_with_others(fingerprints.apply(hash), ax=ax)

    return {
        "unique_fingerprints": num_and_percentage(
            len(fingerprints.unique()), len(fingerprints)
        ),
        "normalized_shannon_entropy": normalized_shannon_entropy(frequencies),
        "mode": num_and_percentage(frequencies[0], len(fingerprints)),
        "mean": frequencies.mean(),
        "std": frequencies.std(),
        "min": frequencies.min(),
        "max": frequencies.max(),
    }, {"direct_rules_frequency_plot": (fig, ax)}


def filterlist_individual_statistics(df, top_k=30, figsize=(5, 2), list_info_metadata=None):

    df_valid = df[df.valid]

    frequencies = (
        df_valid.filters.apply(json.loads).apply(pd.Series).stack().value_counts()
    )
    
    # normalize the names if metadata is provided
    if list_info_metadata:
        def normalize_name(name):
            for filter in list_info_metadata:
                if name.strip()  == filter['name']:
                    return name
                if name.strip() in filter.get('aliases', []):
                    return filter['name']
                
            return name
        
        frequencies.index = frequencies.index.map(normalize_name)
        
        # combine the frequencies of the same filterlist
        frequencies = frequencies.groupby(frequencies.index).sum()
        # sort by frequency
        frequencies = frequencies.sort_values(ascending=False)

    fig, ax = plt.subplots(figsize=figsize)
    ax.set_title("Filterlist frequency")
    frequencies[:top_k].plot(kind="bar", ax=ax)

    return (
        {
            "unique_filterlists": len(frequencies.index),
            "mode": frequencies.idxmax(),
            "mode_frequency": num_and_percentage(frequencies.max(), len(df_valid)),
            # "normalized_shannon_entropy": normalized_shannon_entropy(frequencies),
        },
        {"filterlist_frequency_plot": (fig, ax)},
        frequencies,
    )


def compute_median_anon_set_size_over_individuals(anon_set_sizes: list):

    individuals = []

    for anon_set_size in anon_set_sizes:
        individuals.extend([anon_set_size] * anon_set_size)

    return np.median(individuals)


def general_fingerprinting_stats(exp_dir: Path, unique_upper_bound=3, is_notebook=False):
    
    anon_set_stats = []

    for f in exp_dir.iterdir():
        if f.is_dir() and f.name.startswith("max_size:"):
            stats = json.load((f / "fingerprint.json").open())
            n_unique = sum(
                [len(x) for x in stats["anon_sets"] if len(x) <= unique_upper_bound]
            )
            sizes_sum = sum([len(x) for x in stats["anon_sets"]])
            anon_set_stats.append(
                stats["stats"]
                | {
                    "n_unique": n_unique / sizes_sum * 100,
                    "support": sizes_sum,
                    "n_unique_raw": n_unique,
                    "median_anon_set_size_over_individuals": compute_median_anon_set_size_over_individuals(
                        [len(x) for x in stats["anon_sets"]]
                    ),
                }
            )

    anon_set_stats = pd.DataFrame(anon_set_stats).sort_values("best_mask_size")

    x = anon_set_stats["best_mask_size"]
    y_mean = anon_set_stats["mean_anon_set_size"]
    y_std = anon_set_stats["std_anon_set_size"]
    y_median = anon_set_stats["median_anon_set_size_over_individuals"]
    y_median_rel = y_median / anon_set_stats["support"]
    y_max = anon_set_stats["max_anon_set_size"]
    y_entropy = anon_set_stats["anon_set_entropy"]
    y_n_unique = anon_set_stats["n_unique"]
    y_n_unique_raw = anon_set_stats["n_unique_raw"]
    # plots

    if is_notebook:
        fig, ax = plt.subplots(
            3, 1, figsize=(5, 7.5), sharex=True, gridspec_kw={"hspace": 0.3}
        )

        ax[0].set_title("Anon set size over mask size")

        # plot mean and std as fill between

        ax[0].plot(x, y_mean, label="mean")
        ax[0].fill_between(x, y_mean - y_std, y_mean + y_std, alpha=0.5, label="std")
        ax[0].plot(x, y_max, label="max", linestyle="--")

        ax[0].set_xlabel("Mask size")
        ax[0].set_ylabel("Anon set size")
        ax[0].legend()

        # log scale
        ax[0].set_yscale("log")

        # plot entropy
        ax[1].plot(x, y_entropy)
        ax[1].set_xlabel("Mask size")
        ax[1].set_ylabel("Entropy")
        ax[1].set_title("Entropy over mask size")

        # plot n_unique
        ax[2].plot(x, y_n_unique)
        ax[2].set_xlabel("Mask size")
        ax[2].set_ylabel("Percentage of unique anon sets")
        ax[2].set_title("Percentage of unique anon sets over mask size")
        ax[2].set_yticklabels([f"{x:.0f}%" for x in ax[2].get_yticks()])

        print(
            f"Max Uniqueness: {y_n_unique_raw.max()} ({y_n_unique.max():.2f}%) for k={x.max()}"
        )

        print(f"Max Entropy: {y_entropy.max()} for k={x[y_entropy.idxmax()]}")
        print(f"Median Anon Set Size: {y_median.min()} for k={x[y_median.idxmin()]}")
        print(f"Median Anon Set Size (rel): {y_median_rel.min()} for k={x[y_median_rel.idxmin()]}")

        return fig, ax
    
    return {
        'max_unique': num_and_percentage(y_n_unique_raw.max(), anon_set_stats["support"][y_n_unique.idxmax()]),
        'max_entropy': y_entropy.max(),
        'max_median_anon_set_size': y_median.min(),
        'max_median_anon_set_size_rel': y_median_rel.min(),
        'k': x[y_entropy.idxmax()]
    }


def anon_set_size_scatter_plot(exp_subdir: Path, relative=False):

    stats = json.load((exp_subdir / "fingerprint.json").open())

    mask_size = stats["stats"]["best_mask_size"]
    anon_set_sizes = [len(x) for x in stats["anon_sets"]]
    sizes_sum = sum(anon_set_sizes)
    frequencies = pd.Series(anon_set_sizes).value_counts()

    if relative:
        frequencies.index = frequencies.index / sizes_sum * 100

    fig, ax = plt.subplots()
    # make the dots outlined
    ax.scatter(
        frequencies.index,
        frequencies.values,
        s=10,
        edgecolors="black",
        linewidth=0.5,
        color="white",
    )

    if relative:
        ax.set_xlabel("Anon set size portion (%)")
        ax.set_yticklabels([f"{x:.0f}%" for x in ax.get_yticks()])
    else:
        ax.set_xlabel("Anon set size (k)")

    ax.set_ylabel("Number of anon sets of size k")

    # log scale
    ax.set_yscale("log")
    ax.set_xscale("log")

    ax.set_title(f"Anon set size over index - mask size: {mask_size}")

    return fig, ax


def targeted_anon_set_stats(exp_dir: Path, unique_upper_bound=3, is_notebook=False):

    fingerprints = pd.read_csv(exp_dir / "fingerprints.csv")
    
    dict_out = {}
    
    dict_out["total"] = len(fingerprints)
    dict_out["unique"] = num_and_percentage(fingerprints["unique"].sum(), len(fingerprints))
    dict_out["almost_unique"] = (fingerprints["min_anon_set"] < unique_upper_bound).sum()
    dict_out["entropy"] = normalized_shannon_entropy(fingerprints.best_mask.value_counts())
    dict_out["max_size"] = fingerprints["max_size"].describe()

    
    if is_notebook:
        print("Total fingerprints:", len(fingerprints))
        print(
            f"Unique fingerprints: {fingerprints['unique'].sum()} ({fingerprints['unique'].sum() / len(fingerprints) * 100:.2f}%)"
        )

        almost_unique_counts = (fingerprints["min_anon_set"] < unique_upper_bound).sum()
        print(
            f"Almost unique fingerprints (k={unique_upper_bound}): {almost_unique_counts} ({almost_unique_counts / len(fingerprints) * 100:.2f}%)"
        )

        entropy = normalized_shannon_entropy(fingerprints.best_mask.value_counts())
        print(f"Entropy of mask sizes: {entropy:.2f}")

        # max_size stats
        print(fingerprints["max_size"].describe())

        # scatter anon set size over frequencies
        anon_set_sizes = fingerprints["min_anon_set"].value_counts()

        fig, ax = plt.subplots()
        ax.scatter(
            anon_set_sizes.index,
            anon_set_sizes.values,
            s=10,
            edgecolors="black",
            linewidth=0.5,
            color="white",
        )
        ax.set_yscale("log")
        ax.set_xscale("log")
        ax.set_xlabel("Anon set size")
        ax.set_ylabel("Frequency")
        ax.set_title("Anon set size over frequency")

        fig.show()

        # plot the distribution of fingerprint size
        fig2, ax2 = plt.subplots()
        ax2.hist(fingerprints["max_size"], bins=20)
        ax2.set_xlabel("Fingerprint size")
        ax2.set_ylabel("Frequency")
        ax2.set_title("Fingerprint size distribution")

        fig2.show()

        # plot the cumulative distribution of unique upper bounds
        fig3, ax3 = plt.subplots()

        max_anon_set_size = anon_set_sizes.values.max()
        anon_set_sizes = anon_set_sizes.reindex(
            range(1, max_anon_set_size + 1), fill_value=0
        )
        anon_set_sizes = anon_set_sizes.cumsum() / anon_set_sizes.sum()
        ax3.plot(anon_set_sizes)
        ax3.set_xlabel("Anon set size")
        ax3.set_ylabel("Cumulative frequency")
        ax3.set_title("Cumulative frequency of anon set sizes")
        ax3.set_yscale("log")
        ax3.set_xscale("log")

        fig3.show()
    
        return dict_out, {
            "anon_set_size_over_frequency": (fig, ax),
            "fingerprint_size_distribution": (fig2, ax2),
        }
        
    return dict_out, {}


def _get_distance_from_default(
    filterlists: list,
    adblocker_filterlists_conf: dict,
):

    filterlist_names = get_filterlist_name_resolutions(
        adblocker_filterlists_conf["list"]
    )

    default = set(adblocker_filterlists_conf["default"])
    filterlists = {
        filterlist_names.get(filterlist, filterlist) for filterlist in filterlists
    }

    # return len(default.intersection(filterlists)) / len(default.union(filterlists))
    return len(default.union(filterlists)) - len(default.intersection(filterlists))


def anon_set_size_vs_rules_count(
    exp_dir: Path, issues_dir: Path, adblocker_filterlists_conf: dict, is_notebook=False
):

    fingerprints = pd.read_csv(exp_dir / "fingerprints.csv")
    issues = pd.read_csv(issues_dir / "issues_confs_identified.csv")
    rule_counts = pd.read_csv(
        issues_dir / "unique_counts.csv"
    )  # TODO: check if we still generate this file

    def _get_n_rules(filterlists):
        return rule_counts[rule_counts.name.isin(filterlists)].count_total.sum()

    aggregate_df = pd.DataFrame(
        {
            "issue": issues.issue,
            "anon_set_size": fingerprints.min_anon_set,
            "filters": issues.filters,
        }
    )

    aggregate_df["n_filters"] = aggregate_df.filters.apply(lambda x: len(json.loads(x)))
    aggregate_df["n_rules"] = aggregate_df.filters.apply(
        lambda x: _get_n_rules(json.loads(x))
    )
    aggregate_df["distance_from_default"] = aggregate_df.filters.apply(
        lambda x: _get_distance_from_default(json.loads(x), adblocker_filterlists_conf)
    )

    if is_notebook:
        print(
            f"Number of people with distance < 13 and anon set > 128: {len(aggregate_df[(aggregate_df.distance_from_default < 13) & (aggregate_df.anon_set_size > 128)])} ({len(aggregate_df[(aggregate_df.distance_from_default < 13) & (aggregate_df.anon_set_size > 128)]) / len(aggregate_df) * 100:.2f}%)"
        )
        print(
            f"Number of people with distance > 11 and anon set < 128: {len(aggregate_df[(aggregate_df.distance_from_default > 11) & (aggregate_df.anon_set_size < 128)])} ({len(aggregate_df[(aggregate_df.distance_from_default > 11) & (aggregate_df.anon_set_size < 128)]) / len(aggregate_df) * 100:.2f}%)"
        )
        print(
            f"Number of people with distance < 13 and anon set < 128: {len(aggregate_df[(aggregate_df.distance_from_default < 13) & (aggregate_df.anon_set_size < 128)])} ({len(aggregate_df[(aggregate_df.distance_from_default < 13) & (aggregate_df.anon_set_size < 128)]) / len(aggregate_df) * 100:.2f}%)"
        )

        aggregate_df.distance_from_default.hist(bins=100, figsize=(20, 5))

        plt.show()

        # aggregate_df = aggregate_df[aggregate_df.distance_from_default < 10]

        plt.scatter(aggregate_df.distance_from_default, aggregate_df.anon_set_size)

        plt.show()

    fig, ax = plt.subplots(figsize=(10, 4))
    
    # heat map logarithmic xy

    x = aggregate_df.distance_from_default.values
    y = aggregate_df.anon_set_size.values

    n_bins = 50

    x_bins = np.linspace(x.min(), x.max(), n_bins)
    y_bins = logarithmic_bins_base2(y)

    counts, _, _ = np.histogram2d(x, y, bins=(x_bins, y_bins))

    counts = np.log10(counts + 1)

    cbar = plt.colorbar(
        ax.imshow(
            counts.T,
            origin="lower",
            extent=[
                x_bins.min(),
                x_bins.max(),
                min(np.log10(y_bins)),
                max(np.log10(y_bins)),
            ],
            aspect="auto",
            cmap="Greens",
        )
    )
    cbar.set_label("Count")
    cbar.set_ticks(cbar.get_ticks())
    cbar.set_ticklabels([f"{10**tick:.2f}" for tick in cbar.get_ticks()])

    ax.set_yticks(np.log10(y_bins))
    ax.set_yticklabels([f"{y:.0f}" for y in y_bins])
    # ax.set_xticks(x_bins)
    # ax.set_xticklabels([f"{x:.0f}" if i % 2 == 0 else "" for i, x in enumerate(x_bins)], rotation=90)
    ax.set_xlabel("Distance from default")
    ax.set_ylabel("Anon set size")
    ax.set_title("Anon set size vs distance from default")
    
    # remove the grid
    ax.grid(False)

    return fig, ax


def targeted_time_stats(exp_dir: Path):

    if not (exp_dir / "stats").exists():
        print("No stats directory found")
        return

    part_durations = {}
    n_iterations = []

    for stats_fp in (exp_dir / "stats").glob("*.json"):
        stats = json.load(stats_fp.open())
        for part, durations in stats.items():
            if part not in part_durations:
                part_durations[part] = []

            part_durations[part].append(sum(durations))

            if part == "avail_attrs":
                n_iterations.append(len(durations))

    part_durations = pd.DataFrame(part_durations)
    part_durations["total"] = (
        part_durations["mask"]
        + part_durations["target_users"]
        + part_durations.anon_set
        + part_durations.loop
    )

    # boxplot of the durations
    fig, ax = plt.subplots(1, 2, figsize=(10, 5))
    # add padding between the plots
    plt.subplots_adjust(wspace=0.5)

    ax[0].boxplot(part_durations)
    ax[0].set_ylabel("Duration (s)")
    ax[0].set_title("Duration of each part")
    ax[0].set_xticklabels(part_durations.columns, rotation=90)

    # plot distributions with different x axes for the number of iterations and total duration
    ax2 = ax[1]
    ax3 = ax2.twiny()

    ax2.hist(n_iterations, bins=20, color="blue", alpha=0.5)
    ax2.set_xlabel("Number of iterations")
    ax2.set_ylabel("Frequency")

    ax3.hist(part_durations["total"], bins=20, color="red", alpha=0.5)
    ax3.set_xlabel("Total duration (s)")

    ax2.set_title("Number of iterations and total duration distribution")

    return fig, ax


# -------------------------------------------------------
# STABILITY STATISTICS
# -------------------------------------------------------


def rule_last_seen_statistics(
    download_timestamp: datetime,
    rule_last_seen: pd.DataFrame,
    figsize=(5, 5),
):

    _rule_last_seen = rule_last_seen.copy()
    _rule_last_seen["last_seen"] = (
        -(
            pd.to_datetime(_rule_last_seen["last_seen"], utc=True) - download_timestamp
        ).dt.total_seconds()
        / 60
        / 60
        // 24
    )

    stats = {
        "non-removed count": num_and_percentage(
            len(_rule_last_seen[rule_last_seen["last_seen"].isna()]),
            len(_rule_last_seen),
        ),
        "mean": _rule_last_seen["last_seen"].mean(),
        "std": _rule_last_seen["last_seen"].std(),
        "min": _rule_last_seen["last_seen"].min(),
        "max": _rule_last_seen["last_seen"].max(),
        "median": (-_rule_last_seen["last_seen"]).median(),
        "25%": (-_rule_last_seen["last_seen"]).quantile(0.25),
        "75%": (-_rule_last_seen["last_seen"]).quantile(0.75),
        "90%": (-_rule_last_seen["last_seen"]).quantile(0.9),
        ">=88": num_and_percentage(
            len(
                _rule_last_seen[
                    (_rule_last_seen["last_seen"].isna())
                    | (_rule_last_seen["last_seen"] >= 88)
                ]
            ),
            len(_rule_last_seen),
        ),
        ">=365": num_and_percentage(
            len(_rule_last_seen[(_rule_last_seen["last_seen"] >= 365) | (_rule_last_seen["last_seen"].isna())]),
            len(_rule_last_seen),
        ),
        ">=357": num_and_percentage(
            len(_rule_last_seen[(_rule_last_seen["last_seen"] >= 357) | (_rule_last_seen["last_seen"].isna())]),
            len(_rule_last_seen),
        ),
    }
    
    _rule_last_seen["last_seen"] = _rule_last_seen["last_seen"].apply(lambda x: x if not math.isnan(x) else 1400)

    fig, ax = plt.subplots(figsize=figsize)
    
    # remove the nan values
    _rule_last_seen = _rule_last_seen.dropna()
    
    counts = _rule_last_seen["last_seen"].value_counts().sort_index(ascending=False)
    
    # cumulative distribution reversed
    ax.plot(-counts.index, counts.cumsum() / counts.sum())
    ax.set_xlabel("Days since last seen")
    ax.set_xticks(ax.get_xticks())
    ax.set_xticklabels( [int(i) for i in np.absolute(ax.get_xticks())])
    ax.set_ylabel("Cumulative frequency")
    ax.set_title("Cumulative distribution of days since last seen")
    

    return stats, {"rule_last_seen_histogram": (fig, ax)}, ((counts.cumsum() / counts.sum()).values, -counts.index)
# ,(heights, x_labels)


def equivalent_set_max_last_seen_statistics(
    download_timestamp: datetime,
    rule_equivalent_set: pd.DataFrame,
    rule_last_seen: pd.DataFrame,
    figsize=(5, 5),
):

    _rule_last_seen = rule_last_seen.copy()
    _rule_last_seen = _rule_last_seen.merge(rule_equivalent_set, on="rule", how="right")

    _rule_last_seen["last_seen"] = pd.to_datetime(
        _rule_last_seen["last_seen"], utc=True
    )

    # print(_rule_last_seen.columns)
    def get_max_or_none(df):
        return pd.Series(
            {"last_seen": df.last_seen.min() if not df.last_seen.isna().any() else None}
        )

    _equiv_set_last_seen = (
        _rule_last_seen[["equivalent_set_id", "last_seen"]]
        .groupby("equivalent_set_id")
        .apply(get_max_or_none)
        .reset_index()
    )

    _equiv_set_last_seen["last_seen"] = (
        - (
            pd.to_datetime(_equiv_set_last_seen["last_seen"], utc=True)
            - download_timestamp
        ).dt.total_seconds()
        / 60
        / 60
        // 24
    )

    stats = {
        "mean": _equiv_set_last_seen["last_seen"].mean(),
        "std": _equiv_set_last_seen["last_seen"].std(),
        "min": _equiv_set_last_seen["last_seen"].min(),
        "max": _equiv_set_last_seen["last_seen"].max(),
        "median": _equiv_set_last_seen["last_seen"].median(),
        "10%": _equiv_set_last_seen["last_seen"].quantile(0.1),
        "25%": _equiv_set_last_seen["last_seen"].quantile(0.25),
        "75%": _equiv_set_last_seen["last_seen"].quantile(0.75),
        "90%": _equiv_set_last_seen["last_seen"].quantile(0.9),
        "non-removed count": num_and_percentage(
            len(_equiv_set_last_seen[_equiv_set_last_seen["last_seen"].isna()]),
            len(_equiv_set_last_seen),
        ),
    }
    
    _equiv_set_last_seen["last_seen"] = _equiv_set_last_seen["last_seen"].apply(lambda x: x if not math.isnan(x) else np.infty)

    # plot the histogram of the last seen
    fig, ax = plt.subplots(figsize=figsize)
    
    # remove the nan values
    _equiv_set_last_seen['last_seen'] = _equiv_set_last_seen['last_seen'].apply(lambda x: x if not math.isinf(x) else 1400)
    
    
    
    counts = _equiv_set_last_seen["last_seen"].value_counts().sort_index(ascending=False)
    
    print(counts)
    
    # cumulative distribution reversed
    ax.plot(-counts.index, counts.cumsum() / counts.sum())
    ax.set_xlabel("Days since last seen")
    ax.set_xticklabels( [int(i) for i in np.absolute(ax.get_xticks())])
    ax.set_ylabel("Cumulative frequency")
    ax.set_title("Cumulative distribution of days since last seen")

    return stats, {"equivalent_set_last_seen_histogram": (fig, ax)}, ((counts.cumsum() / counts.sum()).values, -counts.index)


def intercommit_time_and_n_changes_stats(
    changes_df: pd.DataFrame,
    _filter: Callable[
        [
            pd.Series,
        ],
        bool,
    ],
):

    # multiple change rows for the same commit `commit_id`, we just need one of them to be true

    valid_changes = changes_df[changes_df.apply(_filter, axis=1)]

    def _commit_stats(group):
        return pd.Series(
            {
                "n_changes": len(group),
                "n_distinct_files": len(group.file_path.unique()),
                "timestamp": group.iloc[0].timestamp,
            }
        )

    commits_df = valid_changes.groupby("commit_id").apply(_commit_stats)

    commits_df = commits_df.reset_index()
    # sort by timestamp
    commits_df = commits_df.sort_values("timestamp")

    commits_df["timestamp"] = pd.to_datetime(commits_df["timestamp"])
    commits_df["intercommit_time"] = (
        commits_df["timestamp"].diff().dt.total_seconds() / 60 / 60
    )
    
    # remove outliers
    commits_df = commits_df[commits_df["intercommit_time"] < 1000] 

    stats = commits_df["intercommit_time"].describe()

    fig, ax = plt.subplots(1, 2, figsize=(10, 5))

    # log x distribution
    bins = 10 ** np.linspace(0, 2, 50)

    ax[0].hist(commits_df["intercommit_time"], bins=bins)
    ax[0].set_xscale("log")
    ax[0].set_yscale("log")
    ax[0].set_xlabel("Intercommit time (hours)")
    ax[0].set_ylabel("Frequency")
    ax[0].set_title("Intercommit time distribution")

    ax[1].hist(commits_df["n_changes"], bins=50)
    ax[1].set_xscale("log")
    ax[1].set_yscale("log")
    ax[1].set_xlabel("Number of changes")
    ax[1].set_ylabel("Frequency")
    ax[1].set_title("Number of changes distribution")

    return stats, {"fig_intercommit": (fig, ax[0]), "fig_changes_distr": (fig, ax[1])}


def change_frequency_per_file_path(
    changes_df: pd.DataFrame,
    _filter: Callable[
        [
            pd.Series,
        ],
        bool,
    ],
):

    valid_changes = changes_df[changes_df.apply(_filter, axis=1)].copy()
    valid_changes["timestamp"] = pd.to_datetime(valid_changes["timestamp"])
    valid_changes = valid_changes.sort_values("timestamp")

    def _stats(group):

        timestamps = group["timestamp"].drop_duplicates()

        # timestamps of distinct commits
        intercommit_time = timestamps.diff().dt.total_seconds() / 60 / 60

        return pd.Series(
            {
                "n_changes": len(group),
                "avg_intercommit_time": intercommit_time.mean(),
                "std_intercommit_time": intercommit_time.std(),
            }
        )

    file_changes = valid_changes.groupby("file_path").apply(_stats)

    # drop nans
    file_changes = file_changes.dropna()

    # bar plot of the average intercommit time by file path

    fig, ax = plt.subplots(figsize=(10, 5))

    file_changes.sort_values("avg_intercommit_time", ascending=False)[
        "avg_intercommit_time"
    ].plot(kind="bar", ax=ax)
    ax.set_yscale("log")
    ax.set_ylabel("Average intercommit time (hours)")
    ax.set_title("Average intercommit time by file path")

    ax.set_xticklabels(ax.get_xticklabels(), rotation=90)

    ax2 = ax.twinx()
    file_changes.sort_values("avg_intercommit_time", ascending=False)["n_changes"].plot(
        kind="line", ax=ax2, color="red"
    )
    ax2.set_ylabel("Number of changes")
    ax2.set_yscale("log")
    ax2.set_ylim(1, ax2.get_ylim()[1])

    return file_changes, fig, ax


# -------------------------------------------------------
# USER SUBSCRIPTIONS STATISTICS
# -------------------------------------------------------


def user_filters_changes(user_issues_df: pd.DataFrame):

    last_filterlist = None
    last_filterlist_date = None
    change_statistics = []
    unchanged_user = []

    for _, issue in user_issues_df.iterrows():

        to_set = set(json.loads(issue.filters))

        if last_filterlist is None:
            last_filterlist = to_set
            last_filterlist_date = pd.to_datetime(issue.created_at)
            continue

        if last_filterlist != to_set:

            from_set = last_filterlist

            added = to_set - from_set
            removed = from_set - to_set
            diff = to_set.symmetric_difference(from_set)

            change_statistics.append(
                {
                    "from": last_filterlist,
                    "to": issue.filters,
                    "n_added": len(added),
                    "n_removed": len(removed),
                    "n_changed": len(diff),
                    "from_date": issue.created_at,
                    "duration_hours": (
                        last_filterlist_date - pd.to_datetime(issue.created_at)
                    ).total_seconds()
                    / 60
                    / 60,
                }
            )

            last_filterlist = to_set
            last_filterlist_date = pd.to_datetime(issue.created_at)

    if len(change_statistics) == 0:
        # add an empty change
        unchanged_user.append(
            {
                "author": user_issues_df.author.iloc[0],
                "filters": user_issues_df.filters.iloc[0],
                "n_issues": len(user_issues_df),
                "min_date": user_issues_df.created_at.min(),
                "max_date": user_issues_df.created_at.max(),
            }
        )

    value_counts = user_issues_df.filters.value_counts()
    change_statistics = pd.DataFrame(change_statistics)
    change_statistics["author"] = user_issues_df.author.iloc[0]

    min_date = pd.to_datetime(user_issues_df.created_at.min())
    max_date = pd.to_datetime(user_issues_df.created_at.max())
    first_filterlist = json.loads(user_issues_df.filters.iloc[0])

    return (
        change_statistics,
        pd.DataFrame(unchanged_user),
        (
            value_counts,
            min_date,
            max_date,
            first_filterlist,
            len(user_issues_df),
        ),
    )


def get_users_changes_df_and_stats_df(users_issues_df: pd.DataFrame):

    change_statistics = []
    unchanged_users = []
    users_stats = []

    for _, user_issues_df in users_issues_df.groupby("author"):
        user_change_statistics, unchanged_user, user_values = user_filters_changes(
            user_issues_df
        )
        change_statistics.append(user_change_statistics)
        unchanged_users.append(unchanged_user)

        user_stats = user_subscriptions_statistics(user_change_statistics, *user_values)

        users_stats.append(user_stats)

    change_statistics = pd.concat(change_statistics)
    unchanged_users = pd.concat(unchanged_users)
    users_stats = pd.DataFrame(users_stats)

    return change_statistics, unchanged_users, users_stats


def user_subscriptions_statistics(
    change_statistics: pd.DataFrame,
    value_counts: pd.Series,
    min_date: pd.Timestamp,
    max_date: pd.Timestamp,
    first_filterlist: list,
    n_issues: int,
):

    stats = {
        "distribution": json.dumps(list(value_counts.values.astype(float) / n_issues)),
        "n_issues": n_issues,
        "n_changes": len(change_statistics),
        "average_change_rate": 0,
        "average_duration": 0,
        "average_size": 0,
        "average_added_n": 0,
        "average_removed_n": 0,
        "average_changed_n": 0,
        "median_duration": 0,
        "median_size": 0,
        "median_added_n": 0,
        "median_removed_n": 0,
        "median_changed_n": 0,
        "min_duration": np.infty,
        "max_duration": np.infty,
    }

    if len(change_statistics) > 0:

        stats["average_duration"] = change_statistics["duration_hours"].mean()
        stats["average_size"] = (
            change_statistics["n_added"].mean() + change_statistics["n_removed"].mean()
        )
        stats["average_added_n"] = change_statistics["n_added"].mean()
        stats["average_removed_n"] = change_statistics["n_removed"].mean()
        stats["average_changed_n"] = change_statistics["n_changed"].mean()

        stats["median_duration"] = change_statistics["duration_hours"].median()
        stats["median_size"] = (
            change_statistics["n_added"].median()
            + change_statistics["n_removed"].median()
        )
        stats["median_added_n"] = change_statistics["n_added"].median()
        stats["median_removed_n"] = change_statistics["n_removed"].median()
        stats["median_changed_n"] = change_statistics["n_changed"].median()

        stats["min_duration"] = change_statistics["duration_hours"].min()
        stats["max_duration"] = change_statistics["duration_hours"].max()

        stats["average_change_rate"] = (
            (max_date - min_date).total_seconds() / 60 / 60 / len(change_statistics)
        )

    else:
        stats["median_size"] = stats["average_size"] = len(first_filterlist)

    return pd.Series(stats)


def users_subscriptions_stats(
    user_changes_df: pd.DataFrame,
    unchanged_users: pd.DataFrame,
    issues_df: pd.DataFrame,
    user_change_stats_df: pd.DataFrame,
    timeplot_increment=timedelta(days=365),
):

    stats = user_change_stats_df

    users_with_no_change = stats[stats.n_changes == 0]

    print(
        "N users with no changes:",
        len(users_with_no_change),
        f"({len(users_with_no_change) / len(stats) * 100:.2f}%)",
    )
    print(
        "N issues with unique user/filters:",
        users_with_no_change.n_issues.sum(),
        f"({users_with_no_change.n_issues.sum() / stats.n_issues.sum() * 100:.2f}%)",
    )

    users_with_no_changes_and_mult_issues = stats[
        (stats.min_duration == np.infty) & (stats.n_issues > 1)
    ]

    print(
        "N users with multiple issues and same filters:",
        len(users_with_no_changes_and_mult_issues),
        f"({len(users_with_no_changes_and_mult_issues) / len(stats) * 100:.2f}%)",
    )
    print(
        "N issues with duplicate user/filters:",
        users_with_no_changes_and_mult_issues.n_issues.sum(),
        f"({users_with_no_changes_and_mult_issues.n_issues.sum() / stats.n_issues.sum() * 100:.2f}%)",
    )

    users_with_change_and_mult_issues = stats[(stats.min_duration != np.infty)]

    print(
        "N users with multiple issues and different filters:",
        len(users_with_change_and_mult_issues),
        f"({len(users_with_change_and_mult_issues) / len(stats) * 100:.2f}%)",
    )
    print(
        "N issues with unique user/filters:",
        users_with_change_and_mult_issues.n_issues.sum(),
        f"({users_with_change_and_mult_issues.n_issues.sum() / stats.n_issues.sum() * 100:.2f}%)",
    )

    # we will make a cumulative time plot

    def get_counts(changed_df, unchanged_users, issues_df, min_date):
        _df = changed_df[pd.to_datetime(changed_df.from_date) >= min_date]

        # _df = changed_df.copy()

        _df_stats = _df.groupby("author").apply(
            lambda for_user: user_subscriptions_statistics(
                for_user,
                pd.Series(),
                pd.to_datetime(_df.from_date.min()),
                pd.to_datetime(_df.from_date.max()),
                [],
                (
                    (issues_df.author == for_user.name)
                    & (pd.to_datetime(issues_df.created_at) >= min_date)
                ).sum(),
            )
        )

        users_with_no_changes_and_mult_issues = _df_stats[(_df_stats.n_changes == 0)]

        users_with_no_change = unchanged_users[
            pd.to_datetime(unchanged_users.max_date) >= min_date
        ]

        users_with_change_and_mult_issues = _df_stats[
            (_df_stats.min_duration != np.infty) & (_df_stats.n_changes > 1)
        ]

        # print(users_with_change_and_mult_issues.n_issues.sum())
        return {
            "n_users_with_no_changes": len(users_with_no_change)
            + len(users_with_no_changes_and_mult_issues),
            "n_users_with_changes_and_mult_issues": len(
                users_with_change_and_mult_issues
            ),
            "n_issues_with_changes_and_mult_issues": users_with_change_and_mult_issues.n_issues.sum(),
            "n_issues_with_no_changes": users_with_no_change.n_issues.sum()
            + users_with_no_changes_and_mult_issues.n_issues.sum(),
            "proportion_users_with_changes_and_mult_issues": len(
                users_with_change_and_mult_issues
            )
            / (len(_df_stats) + len(users_with_no_change)),
            "proportion_issues_with_changes_and_mult_issues": users_with_change_and_mult_issues.n_issues.sum()
            / (pd.to_datetime(issues_df.created_at) >= min_date).sum(),
        }

    CURRENT_CUTOFF = pd.to_datetime(user_changes_df.from_date).max()

    Ys = {
        "n_users_with_no_changes": [],
        "n_users_with_changes_and_mult_issues": [],
        "n_issues_with_changes_and_mult_issues": [],
        "n_issues_with_no_changes": [],
        "proportion_users_with_changes_and_mult_issues": [],
        "proportion_issues_with_changes_and_mult_issues": [],
    }

    X = []

    fig, ax = plt.subplots()

    while CURRENT_CUTOFF > pd.to_datetime(user_changes_df.from_date).min():

        counts_dict = get_counts(
            user_changes_df, unchanged_users, issues_df, CURRENT_CUTOFF
        )

        for k, v in counts_dict.items():
            Ys[k].append(v)

        CURRENT_CUTOFF -= timeplot_increment

        X.append(CURRENT_CUTOFF)

    ax.plot(
        X,
        Ys["proportion_issues_with_changes_and_mult_issues"],
        label="Issues with changes and multiple issues",
    )

    ax.set_ylabel("Number of users")
    ax.set_xlabel("Time")
    ax.set_title("User subscriptions changes over time")
    ax.invert_xaxis()
    ax.legend()


def users_stability_and_distance_from_default_stats(
    unchanged_users: pd.DataFrame, adblocker_conf: dict
):

    unchanged_users["distance_from_default"] = unchanged_users.filters.apply(
        lambda x: _get_distance_from_default(x, adblocker_conf)
    )

    print(unchanged_users.distance_from_default.describe())


# -------------------------------------------------------
# FILTERLISTS FINGERPRINTING MAPPING STATISTICS
# -------------------------------------------------------


def usage_frequency(fingerprints: pd.DataFrame, marker_to_set: dict):
    
    if len(marker_to_set) == 0:
        return {}

    counts = {}
    
    is_key_str = isinstance(list(marker_to_set.keys())[0], str)

    for fingerprint in fingerprints.best_mask:
        for marker in json.loads(fingerprint):
            if marker < 0:
                marker = -marker
                
            if marker == 0.01:
                marker = 0
                
            if is_key_str:
                marker = str(marker)

            counts[marker_to_set[marker]] = counts.get(marker, 0) + 1

    return counts

def _get_sets_used_in_general(best_mark, marker_to_set: dict):  
    
    if len(marker_to_set) == 0:
        return set()
    
    best_sets = set()
    is_key_str = isinstance(list(marker_to_set.keys())[0], str)
    
    for marker in best_mark:
        if marker < 0:
            marker = -marker

        if marker == 0.01:
            marker = 0

        if is_key_str:
            marker = str(marker)

        best_sets.add(marker_to_set[marker])
        
    return best_sets
    

def load_marker_to_set(attack_fp: Path):
    
    attack_dir = Path(attack_fp).parent
    
    return json.load((attack_dir / "filterlist_names.json").open())

def equivalent_list_set_stats(
    unique_counts_fp, equivalent_sets_fp, targeted_attack_fp, general_attack_fp
):

    unique_counts = pd.read_csv(unique_counts_fp)
    equivalent_sets = json.load(open(equivalent_sets_fp))

    try:
        fingerprints = pd.read_csv(targeted_attack_fp)
        marker_to_set = load_marker_to_set(targeted_attack_fp)
    
        general_fingerprint = json.load(open(general_attack_fp))
        general_marker_to_set = load_marker_to_set(general_attack_fp)
        
    except:
        # print("No fingerprints found")
        fingerprints = pd.DataFrame(columns=["best_mask"])
        marker_to_set = {}
        general_fingerprint = {"best_mask": []}
        general_marker_to_set = {}

    set_popularity_targeted = usage_frequency(fingerprints, marker_to_set)
    used_general_set = _get_sets_used_in_general(general_fingerprint["best_mask"], general_marker_to_set)

    equiv_sets_df = pd.DataFrame(
        {
            "n_lists": [
                len(equiv_set)
                for equiv_set in equivalent_sets["equiprobable_list_sets"]
            ],
            "n_rules": [
                len(equiv_set) for equiv_set in equivalent_sets["equivalent_rules"]
            ],
        }
    )

    sets_with_one_list = set(
        [i for i, a in enumerate(equivalent_sets["equiprobable_list_sets"]) if len(a) == 1]
    )

    used_sets_targeted = set(set_popularity_targeted.keys())

    # print(f"N of list sets: {equiv_sets_df.shape[0]}")
    # print(f"N of list sets of size 1: {equiv_sets_df[equiv_sets_df.n_lists == 1].shape[0]} ({equiv_sets_df[equiv_sets_df.n_lists == 1].shape[0] / equiv_sets_df.shape[0] * 100:.2f}%)")
    # print(f"N of used sets for targeted fingerprinting: {len(set_popularity_targeted)}")
    # print(f"N of used sets for targeted fingerprinting of size 1: {len(used_lists & unique_lists)} ({len(used_lists & unique_lists) / len(used_lists) * 100:.2f}%)")

    return (
        # Stats
        {
            "n_allowed_rules": num_and_percentage(
                unique_counts.count_allowed.sum(), unique_counts.count_total.sum()
            ),
            "n_unique_lists": (unique_counts.count_unique > 0).sum(),
            "average_n_unique_rules_ratio_per_list": (unique_counts.count_unique / unique_counts.count_total).mean(),
            "n_unique_lists_ratio": (unique_counts.count_unique > 0).sum()
            / unique_counts.shape[0],
            "n_list_sets": equiv_sets_df.shape[0],
            "n_list_sets_size_1": equiv_sets_df[equiv_sets_df.n_lists == 1].shape[0],
            "n_list_sets_size_1_ratio": equiv_sets_df[equiv_sets_df.n_lists == 1].shape[
                0
            ]
            / equiv_sets_df.shape[0],
            "n_used_sets_targeted": len(set_popularity_targeted),
            "n_used_sets_targeted_size_1": len(used_sets_targeted & sets_with_one_list),
            "n_used_sets_targeted_size_1_ratio": (
                len(used_sets_targeted & sets_with_one_list) / len(used_sets_targeted)
                if len(used_sets_targeted) > 0
                else 0
            ),
            "n_used_sets_general": len(used_general_set),
            "n_used_sets_general_size_1": len(used_general_set & sets_with_one_list),
            # "n_used_sets_general_complex": len(used_general_set & complex_sets),
            "n_used_sets_general_size_1_ratio": (
                len(used_general_set & sets_with_one_list) / len(used_general_set)
                if len(used_general_set) > 0
                else 0
            ),
        },
        # Figures
        {},
    )


# -------------------------------------------------------
# DOMAIN COVERAGE STATISTICS
# -------------------------------------------------------


def domain_counts_stats(domain_rule_counts: pd.DataFrame):
    return {
        "n_domains": domain_rule_counts.shape[0],
        "max_rules": domain_rule_counts.total_rules.max(),
        "min_rules": domain_rule_counts.total_rules.min(),
        "median_rules": domain_rule_counts.total_rules.median(),
        "max_lists": domain_rule_counts.total_lists.max(),
        "min_lists": domain_rule_counts.total_lists.min(),
        "median_lists": domain_rule_counts.total_lists.median(),
    }


def domain_coverage_stats(
    domain_rule_counts: pd.DataFrame,
    attack_list_rule_counts: pd.DataFrame,
    is_notebook=False,
):

    all_lists = set(list(domain_rule_counts.columns)[1:-2])
    unique_lists = set(
        attack_list_rule_counts[attack_list_rule_counts.count_unique > 0].name.values
    )

    def get_domain_with_most_remaining(already_covered_lists: set):

        already_covered_lists = already_covered_lists & all_lists
        uncovered_lists = all_lists - already_covered_lists

        remaining_domain_rule_counts: pd.DataFrame = domain_rule_counts.drop(
            columns=list(already_covered_lists) + ["total_rules", "total_lists"]
        )

        # count the lists where the value is not 0
        remaining_domain_rule_counts["total_lists"] = (
            remaining_domain_rule_counts.apply(
                lambda x: (x[list(uncovered_lists)].values != 0).sum(), axis=1
            )
        )

        max_additional_lists = remaining_domain_rule_counts.total_lists.max()
        domain_with_max = remaining_domain_rule_counts[
            remaining_domain_rule_counts.total_lists == max_additional_lists
        ].domain.values[0]

        if max_additional_lists == 0:
            return domain_with_max, set()

        # get the columns that are not 0
        additional_covered_lists = set(
            [
                col
                for col in uncovered_lists
                if remaining_domain_rule_counts.loc[
                    remaining_domain_rule_counts.domain == domain_with_max, col
                ].values[0]
                != 0
            ]
        )

        return domain_with_max, additional_covered_lists

    already_covered = unique_lists
    chosen_domains = []

    if is_notebook:
        print(f"Total lists: {len(all_lists)}, Unique lists: {len(unique_lists)}")

    while len(already_covered) < len(all_lists):

        domain, additional_lists = get_domain_with_most_remaining(already_covered)

        already_covered.update(additional_lists)

        chosen_domains.append(
            {
                "domain": domain,
                "additional_lists": additional_lists,
                "n_additional_lists": len(additional_lists),
                "n_total_lists": len(already_covered),
            }
        )

        if is_notebook:
            print(
                f"Domain: {domain}, Additional lists: {len(additional_lists)}, Total lists: {len(already_covered)}"
            )

        if len(additional_lists) == 0:
            break

    chosen_domains = pd.DataFrame(
        chosen_domains,
        columns=["domain", "additional_lists", "n_additional_lists", "n_total_lists"],
    )

    # plot the improvement of the domain coverage

    fig, ax = plt.subplots(figsize=(10, 5))

    ax.plot(chosen_domains.n_total_lists)

    ax.set_xlabel("Number of controlled domains")
    ax.set_ylabel("Number of identifiable lists")
    ax.set_title("Impact of domain control on list identification")

    return chosen_domains, (fig, ax)


# Iterative Robustness Analysis

def iterative_robustness_stats(
    exp_dir: Path, ax, ax2, color=None, label=None, what="anon_set_entropy"
):
    summaries = []
    
    for summary_fp in (exp_dir).rglob("summary.json"):
        summaries.append(json.load(summary_fp.open()))
        
    summaries = pd.DataFrame(summaries)
    
    if summaries.empty:
        return ax, ax2
    
    summaries.sort_values("iteration", inplace=True)
    
    # make `n_usable_rules` cumulative
    summaries["n_usable_rules"] = summaries.n_usable_rules.cumsum()
    summaries["n_usable_rules"] = summaries["n_usable_rules"]  / 1e6
    
    ax.plot(summaries.iteration, summaries[what], color=color, label=label, linewidth=2.5)
    ax2.plot(summaries.iteration, summaries.n_usable_rules, color=color, linestyle="--", alpha=0.5, linewidth=2.5)
    
    return ax, ax2