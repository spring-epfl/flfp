#!/usr/bin/env python3
# https://stackoverflow.com/questions/3748136/how-is-cpu-usage-calculated

from collections import defaultdict
from multiprocessing import Pool
import os
import json
import numpy as np
import matplotlib.pyplot as plt
import sys
from tqdm import tqdm
from pathlib import Path

# get the datapath from the command line
if len(sys.argv) < 3:
    print("Usage: python3 process_cpu_data.py <data_path> <output_path>")
    sys.exit(1)

DATA_PATH = Path(sys.argv[1])

if not os.path.exists(DATA_PATH) or not os.path.isdir(DATA_PATH):
    print("Invalid path")
    sys.exit(1)

OUTPUT_PATH = Path(sys.argv[2])

# check if directory is not empty or is a file
if os.path.exists(OUTPUT_PATH):
    if os.path.isfile(OUTPUT_PATH):
        print("Invalid output path")
        sys.exit(1)
    elif len(os.listdir(OUTPUT_PATH)) > 0:
        print("Output path is not empty")
        sys.exit(1)

OUTPUT_PATH.mkdir(parents=True, exist_ok=True)

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
plt.rcParams.update({"font.size": 12})

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


RULE_COUNTS = {
    "adguard": {"default": "1k", "mid": "4k", "all": "8k"},
    "ublock": {"default": "2k", "mid": "6k", "all": "7k"},
}


def sort(feature_dict):
    zipped = zip(
        feature_dict[extn_lst[0]],
        feature_dict[extn_lst[1]],
        feature_dict[extn_lst[2]],
        feature_dict[extn_lst[3]],
    )
    sorted_zipped = sorted(zipped)
    unzipped = list(zip(*sorted_zipped))
    for i in range(len(extn_lst)):
        feature_dict[extn_lst[i]] = list(unzipped[i])
    return feature_dict


class NpEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super(NpEncoder, self).default(obj)


def generate_stats_dict(data_dict):
    websites = np.array(data_dict["websites"])

    dele = defaultdict(dict)
    d = defaultdict(dict)

    ret = defaultdict(dict)

    colors = ["b", "g", "r"]

    for extn in extn_lst:
        if extn == "control":
            continue

        plt.figure(figsize=(4, 3))

        for fl, c in tqdm(
            zip(fl_lst, colors), desc=f"Plotting for {extn}", total=len(fl_lst)
        ):
            # extn_stat.append(np.array(stat_plot[1][extn]))
            dele[extn][fl] = np.array(stat_plot[1][extn][fl])
            d[extn][fl] = {}

            # filter all -1 values from stat_plot
            dummy = np.array(stat_plot[1]["control"]["default"])
            index = np.where(dele[extn][fl] == -1)

            np.delete(dele[extn][fl], index)
            np.delete(dummy, index)

            mask2 = (np.abs(dummy) > 30000) | (dummy < 0)

            mask1 = (np.abs(dele[extn][fl]) > 30000) | (dele[extn][fl] < 0)
            extn_stats = dele[extn][fl][~mask1 & ~mask2]
            dummy = dummy[~mask1 & ~mask2]

            zipped = zip((extn_stats - dummy) / dummy, websites)
            sorted_zipped = sorted(zipped)
            unzipped = list(zip(*sorted_zipped))
            x = list(unzipped[1])  # x -> website
            y = list(unzipped[0])  # y -> extn_time - ctrl_time

            ret[extn][fl] = np.sort(np.array(y))

            for j in range(len(x)):
                d[extn][fl][x[j]] = y[j]

            # # plot
            plt.plot(
                np.sort(np.array(y) * 100),
                label=f"{fl}: {RULE_COUNTS[extn][fl]} rules",
                color=c,
                linewidth=2,
                alpha=0.7,
            )

        plt.legend()
        plt.title(f"Page load time difference for {extn}", fontsize=10)
        plt.xlabel("Websites Sorted")
        plt.ylabel("Additional Page Load Time (%)")
        plt.yscale("log")

        plt.show()
        plt.savefig(OUTPUT_PATH / f"stat_{extn}.pdf", bbox_inches="tight")

        # print the medians
        print(f"{extn} median LOAD TIME (std) (%):")

        for fl in fl_lst:
            print(f"{fl}: {np.median(ret[extn][fl])} ({np.std(ret[extn][fl])})")
    return ret


# list of all files in /data folder
path = str(DATA_PATH.absolute()) + "/"
dir_list = os.listdir(path)

extn_lst = ["control", "ublock", "adguard"]

fl_lst = ["default", "mid", "all"]

data_dict = {"websites": []}

for extn in extn_lst:
    data_dict[extn] = (
        {}
    )  # data_dict = {'websites': [list_of_websites], 'extn_lst[i]': [list of [usr, sys, iowait, stats]]}

    if extn == "control":
        data_dict[extn]["default"] = []
    else:
        for fl in fl_lst:
            data_dict[extn][fl] = []


faulty_sites = defaultdict(dict)
# faulty_extn = {}
for extn in extn_lst:
    faulty_sites[extn] = {}

    if extn == "control":
        faulty_sites[extn]["default"] = []
    else:
        for fl in fl_lst:
            faulty_sites[extn][fl] = []


def check_for_keys(website_data, website):
    # website_data -> data dict of each website, website -> website
    global faulty_sites

    for extn in extn_lst:
        if extn == "control":
            if f"/data/{website}" not in website_data.keys():
                faulty_sites[extn]["default"].append(website)
                # progressbar.update(3)
        else:
            if extn not in website_data.keys():

                for fl in fl_lst:
                    faulty_sites[extn][fl].append(website)

                # progressbar.update(3)

            else:
                for fl in fl_lst:
                    if (
                        fl not in website_data[extn].keys()
                        or len(website_data[extn][fl]["usr"]) < 4
                    ):
                        faulty_sites[extn][fl].append(website)
                    else:
                        # if the duration is larger than 60 seconds, then it is faulty
                        dur = (
                            website_data[extn][fl]["webStats"][1]
                            - website_data[extn][fl]["webStats"][0]
                        )

                        if dur > 60000:
                            faulty_sites[extn][fl].append(website)
                            print(website, extn, fl, dur)
                            print(website_data[extn][fl]["webStats"])
                            print()

                    # progressbar.update(1)

    # progressbar.close()


# load all the data from the files in 1 dictionary
all_data = {}


def load_website(website):
    with open(path + website, "r") as f:
        return {**json.load(f)}


site_data = []

with Pool(12) as p:
    site_data = list(tqdm(p.imap(load_website, dir_list), total=len(dir_list)))

all_data = dict(zip(dir_list, site_data))

# populate the faulty_sites dict
for website in all_data:
    check_for_keys(all_data[website]["stats"], website)

faulty_num = {}
for extn in extn_lst[1:]:

    faulty_num[extn] = {}

    for fl in fl_lst:
        faulty_num[extn][fl] = 0

for website in dir_list:
    # control case
    key = "/data/" + website
    data = all_data[website]

    if website in faulty_sites["control"]["default"]:
        continue
    for extn in extn_lst[1:]:

        for fl in fl_lst:
            if website in faulty_sites[extn][fl]:
                data["stats"][extn] = data["stats"].get(extn, {})
                data["stats"][extn][fl] = {"webStats": [-1, -1]}

    data_dict["websites"].append(website)

    try:
        usr_c = data["stats"][key]["default"]["usr"]
        sys_c = data["stats"][key]["default"]["sys"]
        iowait_c = data["stats"][key]["default"]["iowait"]
        webStats_c = data["stats"][key]["default"]["webStats"]
        data_dict["control"] = data_dict.get("control", {})
        data_dict["control"]["default"].append([usr_c, sys_c, iowait_c, webStats_c])
    except KeyError as k:
        # print(website, k, "- dropping website")
        faulty_sites += 1
        data_dict["websites"] = data_dict["websites"][:-1]
        continue

    # extn case
    for extn in extn_lst[1:]:  # opting out the 'control' case
        for fl in fl_lst:
            key = extn
            try:
                usr = data["stats"][key][fl]["usr"]
                syst = data["stats"][key][fl]["sys"]
                iowait = data["stats"][key][fl]["iowait"]
                webStats = data["stats"][key][fl]["webStats"]
                data_dict[extn] = data_dict.get(extn, {})
                data_dict[extn][fl].append([usr, syst, iowait, webStats])
            except KeyError as k:
                usr = usr_c
                syst = sys_c
                iowait = iowait_c
                webStats = webStats_c
                data_dict[extn] = data_dict.get(extn, {})
                data_dict[extn][fl].append([usr, syst, iowait, webStats])
                faulty_num[extn][fl] += 1
                # print(website, extn,  k)
                pass

print(faulty_num)  # manually removed the 0.0 extries corresponding to the number here

max_plot = [{}, {}, {}]  # for usr, sys, iowait
avg_plot = [{}, {}, {}]
stat_plot = [{}, {}]

for i in range(4):  # initialization
    for extn in data_dict:

        if extn not in extn_lst:
            continue

        for fl in data_dict[extn]:

            if extn == "control" and fl != "default":
                continue

            if extn != "websites":
                if i == 3:
                    stat_plot[0][extn] = stat_plot[0].get(extn, {})
                    stat_plot[1][extn] = stat_plot[1].get(extn, {})
                    stat_plot[0][extn][fl] = []
                    stat_plot[1][extn][fl] = []
                else:
                    max_plot[i][extn] = max_plot[i].get(extn, {})
                    avg_plot[i][extn] = avg_plot[i].get(extn, {})
                    max_plot[i][extn][fl] = []
                    avg_plot[i][extn][fl] = []

for i in range(len(data_dict["control"]["default"])):
    for extn in data_dict:

        if extn not in extn_lst:
            continue

        for fl in data_dict[extn]:

            if extn == "control" and fl != "default":
                continue

            for j in range(4):
                if extn != "websites":

                    if j == 3:
                        # # filter out -1 values from stat_plot
                        # if data_dict[extn][i][j][0] == -1 or data_dict[extn][i][j][1] == -1:
                        #     continue

                        stat_plot[0][extn][fl].append(data_dict[extn][fl][i][j][0])
                        stat_plot[1][extn][fl].append(data_dict[extn][fl][i][j][1])
                    else:

                        try:
                            # max
                            max_plot[j][extn][fl].append(max(data_dict[extn][fl][i][j]))

                            # avg
                            avg_plot[j][extn][fl].append(
                                sum(data_dict[extn][fl][i][j][:-3])
                                / len(data_dict[extn][fl][i][j][:-3])
                            )  # can do [:-1] so that last entry can be ignored (which would mostly be close to 0) bcoz I did run mpstat for 5 extra cycle
                        except Exception as e:
                            print(e, extn, fl, i, j)
                            print(data_dict[extn][fl][i])

                            raise e


# generate_stats_dict(data_dict)

avg_np = {}
max_np = {}
for extn in extn_lst:

    for fl in fl_lst:

        if extn == "control" and fl != "default":
            continue

        avg_np[extn] = avg_np.get(extn, {})
        max_np[extn] = max_np.get(extn, {})
        avg_np[extn][fl] = np.array(avg_plot[0][extn][fl])  # 0 - usr, 1 - sys
        max_np[extn][fl] = np.array(max_plot[0][extn][fl])  # 0 - usr, 1 - sys
        # sys_avg[extn] = np.array(avg_plot[1][extn]) # 0 - usr, 1 - sys
        # sys_max[extn] = np.array(max_plot[1][extn]) # 0 - usr, 1 - sys


def plot_max():
    median_lst = []
    mean_lst = []

    colors = ["b", "g", "r"]
    for extn in max_np.keys():

        if extn not in extn_lst:
            continue

        if extn != "control":
            plt.figure()

            for fl, c in zip(fl_lst, colors):
                median_lst.append(
                    np.median(max_np[extn][fl] - max_np["control"]["default"])
                )
                mean_lst.append(
                    np.mean(max_np[extn][fl] - max_np["control"]["default"])
                )
                # print('max')
                # print(f'median -> {median_lst}')
                # print(f'mean -> {mean_lst}')
                plt.plot(
                    np.sort(max_np[extn][fl] - max_np["control"]["default"]),
                    label=f"{fl}: {RULE_COUNTS[extn][fl]} rules",
                    color=c,
                )
                plt.axhline(
                    np.median(max_np[extn][fl] - max_np["control"]["default"]),
                    linestyle="dashed",
                    color=c,
                )

            plt.legend()
            plt.title(
                f"Maximum CPU Additional Usage Relative to Control for {extn}",
                fontsize=10,
            )
            plt.xlabel("Sorted Website")
            plt.ylabel("CPU Usage (%)")
            # plt.yscale('log')

            plt.show()
            plt.savefig(OUTPUT_PATH / f"max_{extn}.pdf")


def plot_avg():
    median_lst = []
    mean_lst = []
    colors = ["b", "g", "r"]

    for extn in avg_np.keys():

        if extn not in extn_lst:
            continue

        if extn != "control":

            plt.figure()
            for fl, c in zip(fl_lst, colors):
                median_lst.append(
                    np.median(avg_np[extn][fl] - avg_np["control"]["default"])
                )
                mean_lst.append(
                    np.mean(avg_np[extn][fl] - avg_np["control"]["default"])
                )

                plt.plot(
                    np.sort(avg_np[extn][fl] - avg_np["control"]["default"]),
                    label=f"{fl}: {RULE_COUNTS[extn][fl]} rules",
                    color=c,
                )
                plt.axhline(
                    np.median(avg_np[extn][fl] - avg_np["control"]["default"]),
                    linestyle="dashed",
                    color=c,
                )

            plt.legend()
            plt.title(
                f"Average CPU Additional Usage Relative to Control for {extn}",
                fontsize=10,
            )
            plt.xlabel("Sorted Website")
            plt.ylabel("CPU Usage (%)")
            # plt.yscale('log')

            plt.show()
            plt.savefig(OUTPUT_PATH / f"avg_{extn}.pdf")

            # print the medians
            print(f"{extn} median CPU USAGE (std):")

            for fl in fl_lst:
                print(
                    f"{fl}: {np.median(avg_np[extn][fl] - avg_np['control']['default'])} ({np.std(avg_np[extn][fl] - avg_np['control']['default'])})"
                )


plot_max()
plot_avg()

ret_data = defaultdict(dict)
usr_max = defaultdict(dict)
usr_avg = defaultdict(dict)
sys_max = defaultdict(dict)
sys_avg = defaultdict(dict)
cpu_avg = defaultdict(dict)
load_time = defaultdict(dict)

# print(np.max(avg_plot[0]['control']))
# print(np.min(avg_plot[0]['control']))

progressbar = tqdm(total=len(extn_lst) * len(fl_lst), desc="Generating Statistics")
for extn in extn_lst[1:]:

    for fl in fl_lst:

        usr_max[extn][fl] = np.sort(
            np.array(max_plot[0][extn][fl])
            - np.array(max_plot[0]["control"]["default"])
        )
        usr_avg[extn][fl] = np.sort(
            np.array(avg_plot[0][extn][fl])
            - np.array(avg_plot[0]["control"]["default"])
        )
        sys_max[extn][fl] = np.sort(
            np.array(max_plot[1][extn][fl])
            - np.array(max_plot[1]["control"]["default"])
        )
        sys_avg[extn][fl] = np.sort(
            np.array(avg_plot[1][extn][fl])
            - np.array(avg_plot[1]["control"]["default"])
        )
        cpu_avg[extn][fl] = np.sort(
            np.array(avg_plot[0][extn][fl])
            + np.array(avg_plot[1][extn][fl])
            - np.array(avg_plot[0]["control"]["default"])
        )

        progressbar.update(1)

progressbar.close()

ret_data["usr_max"] = usr_max
ret_data["usr_avg"] = usr_avg
ret_data["sys_max"] = sys_max
ret_data["sys_avg"] = sys_avg
ret_data["cpu_avg"] = cpu_avg
ret_data["load_time"] = generate_stats_dict(data_dict)

with open(OUTPUT_PATH / "plot_performance.json", "w") as f:
    json.dump(ret_data, f, cls=NpEncoder)


# Plot the faulty site distribution across filter lists


def plot_faulty_sites():

    colors = ["b", "g", "r"]

    # should be a matrix
    #               | fails for all | doesn't fail for all|
    # |fails for mid |              |                     |
    # |doesn't fail for mid|        |                     |

    for extn in extn_lst[1:]:

        matrix = np.zeros((2, 2))

        sites_faulty_for_control = set(faulty_sites["control"]["default"])
        sites_faulty_for_default = set(faulty_sites[extn]["default"])

        site_failures = defaultdict(set)

        for fl in fl_lst[1:]:

            for site in faulty_sites[extn][fl]:

                if site in sites_faulty_for_default:
                    continue

                site_failures[site].add(fl)

        for site in site_failures:

            if len(site_failures[site]) == 0:
                matrix[1][1] += 1
            else:

                if "mid" in site_failures[site] and "all" in site_failures[site]:
                    matrix[0][0] += 1

                elif "mid" in site_failures[site]:
                    matrix[0][1] += 1

                elif "all" in site_failures[site]:
                    matrix[1][0] += 1

        # make it latex table

        print(f"{extn}:\n")
        print("\\begin{table}[H]")
        print("\\centering")
        print("\\begin{tabular}{|c|c|c|}")
        print("\\hline")
        print(" & Fails for mid & Doesn't fail for mid \\\\")
        print("\\hline")
        print("Fails for all &", matrix[0][0], "&", matrix[0][1], "\\\\")
        print("\\hline")
        print("Doesn't fail for all &", matrix[1][0], "&", matrix[1][1], "\\\\")
        print("\\hline")
        print("\\end{tabular}")
        print(f"\\caption{{Faulty site distribution for {extn}}}")
        print("\\end{table}")

        print(matrix)


plot_faulty_sites()


sys.exit(0)
