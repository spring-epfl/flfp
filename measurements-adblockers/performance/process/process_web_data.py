import os
from pathlib import Path
import json
import sys
import numpy as np
import pandas as pd
from tqdm import tqdm
from multiprocessing import Pool

__dir__ = os.path.dirname(os.path.abspath(__file__))


# get the datapath from the command line
if len(sys.argv) < 3:
    print("Usage: python3 process_web_data.py <data_path> <output_path>")
    sys.exit(1)

DATA_PATH = Path(sys.argv[1])

if not os.path.exists(DATA_PATH) or not os.path.isdir(DATA_PATH):
    print("Invalid path")
    sys.exit(1)

OUTPUT_PATH = Path(sys.argv[2])

if not os.path.exists(OUTPUT_PATH) or not os.path.isdir(OUTPUT_PATH):
    print("Invalid path")
    sys.exit(1)

OUTPUT_PATH.mkdir(parents=True, exist_ok=True)


def load_website(site_fp):
    website = str(site_fp).split("/webdata/")[1].split("/stats.json")[0]
    with open(site_fp, "r") as f:
        return {**json.loads(f.read()), "website": website}


site_data = []

with Pool(12) as p:
    site_data = list(
        tqdm(p.imap(load_website, DATA_PATH.rglob("stats.json")), total=30000)
    )


print(f"Number of successful sites: {len(site_data)}")


def lazy_loading_stats(site_data):

    # | site | n_lazy | n_total | n_percent | has_lazy |

    lazy_loading = []
    no_image_sites = 0

    for site in site_data:

        # consider a site with no image as outlier
        if site["lazy_loading"]["count"]["total"] == 0:
            no_image_sites += 1
            continue

        lazy_loading.append(
            {
                "site": site["website"],
                "n_lazy": site["lazy_loading"]["count"]["lazy"],
                "n_total": site["lazy_loading"]["count"]["total"],
                "n_percent": site["lazy_loading"]["count"]["lazy"]
                / site["lazy_loading"]["count"]["total"],
                "has_lazy": site["lazy_loading"]["count"]["lazy"] > 0,
            }
        )

    lazy_loading_df = pd.DataFrame(lazy_loading)

    lazy_loading_df.to_csv(OUTPUT_PATH / "lazy_loading_stats.csv", index=False)

    print("-------------------------")
    print("LAZY LOADING STATS")
    print(f"Number of sites with no image: {no_image_sites}")
    print(
        f"Number of sites with lazy loading: {lazy_loading_df['has_lazy'].sum()} / {len(lazy_loading_df)} ({lazy_loading_df['has_lazy'].sum() / len(lazy_loading_df) * 100:.2f}%)"
    )
    print(
        f"Average lazy loading percentage: {lazy_loading_df['n_percent'].mean() * 100:.2f}% +/- {lazy_loading_df['n_percent'].std() * 100:.2f}%"
    )
    print(
        f"Median lazy loading percentage: {lazy_loading_df['n_percent'].median() * 100:.2f}%"
    )
    print(
        f"Max lazy loading percentage: {lazy_loading_df['n_percent'].max() * 100:.2f}%"
    )
    print(
        f"Min lazy loading percentage: {lazy_loading_df['n_percent'].min() * 100:.2f}%"
    )
    print(
        f"Average lazy loading count: {lazy_loading_df['n_lazy'].mean(): .2f} +/- {lazy_loading_df['n_lazy'].std() : .2f}"
    )
    print(f"Median lazy loading count: {lazy_loading_df['n_lazy'].median()}")
    print(f"Max lazy loading count: {lazy_loading_df['n_lazy'].max()}")
    print(f"Min lazy loading count: {lazy_loading_df['n_lazy'].min()}")

    return {
        "count_no_image": no_image_sites,
        "count_lazy_loading": lazy_loading_df["has_lazy"].sum(),
        "average_lazy_loading_percentage": lazy_loading_df["n_percent"].mean() * 100,
        "median_lazy_loading_percentage": lazy_loading_df["n_percent"].median() * 100,
        "max_lazy_loading_percentage": lazy_loading_df["n_percent"].max() * 100,
        "min_lazy_loading_percentage": lazy_loading_df["n_percent"].min() * 100,
        "average_lazy_loading_count": lazy_loading_df["n_lazy"].mean(),
        "median_lazy_loading_count": lazy_loading_df["n_lazy"].median(),
        "max_lazy_loading_count": lazy_loading_df["n_lazy"].max(),
        "min_lazy_loading_count": lazy_loading_df["n_lazy"].min(),
    }


def container_style_stats(site_data):

    container_styles = []

    for site in site_data:

        if site["container_style"]:

            container_styles.append(
                {
                    "site": site["website"],
                    "n_container": len(site["container_style"]),
                    "n_style_container": sum(
                        [
                            1
                            for style in site["container_style"]
                            if style["hasStyle"] is True
                        ]
                    ),
                }
            )

        else:
            container_styles.append(
                {
                    "site": site["website"],
                    "n_container": 0,
                    "n_style_container": 0,
                }
            )

    container_styles_df = pd.DataFrame(container_styles)

    container_styles_df.to_csv(OUTPUT_PATH / "container_style_stats.csv", index=False)

    print("-------------------------")
    print("CONTAINER STYLE STATS")
    print(
        f"Number of sites with no @container: {len(container_styles_df[container_styles_df['n_container'] == 0])}"
    )
    print(
        f"Number of sites with @container: {len(container_styles_df[container_styles_df['n_container'] > 0])} / {len(container_styles_df)} ({len(container_styles_df[container_styles_df['n_container'] > 0]) / len(container_styles_df) * 100:.2f}%)"
    )
    print(
        f"Number of sites with @container and style: {len(container_styles_df[container_styles_df['n_style_container'] > 0])} / {len(container_styles_df)} ({len(container_styles_df[container_styles_df['n_style_container'] > 0]) / len(container_styles_df) * 100:.2f}%)"
    )
    print(
        f"Average number of @container: {container_styles_df['n_container'].mean(): .2f} +/- {container_styles_df['n_container'].std() : .2f}"
    )
    print(f"Median number of @container: {container_styles_df['n_container'].median()}")
    print(f"Max number of @container: {container_styles_df['n_container'].max()}")
    print(f"Min number of @container: {container_styles_df['n_container'].min()}")
    print(
        f"Average number of @container with style: {container_styles_df['n_style_container'].mean(): .2f} +/- {container_styles_df['n_style_container'].std() : .2f}"
    )
    print(
        f"Median number of @container with style: {container_styles_df['n_style_container'].median()}"
    )
    print(
        f"Max number of @container with style: {container_styles_df['n_style_container'].max()}"
    )
    print(
        f"Min number of @container with style: {container_styles_df['n_style_container'].min()}"
    )

    return {
        "count_no_container": len(
            container_styles_df[container_styles_df["n_container"] == 0]
        ),
        "count_container": len(
            container_styles_df[container_styles_df["n_container"] > 0]
        ),
        "count_container_style": len(
            container_styles_df[container_styles_df["n_style_container"] > 0]
        ),
        "average_container": container_styles_df["n_container"].mean(),
        "median_container": container_styles_df["n_container"].median(),
        "max_container": container_styles_df["n_container"].max(),
        "min_container": container_styles_df["n_container"].min(),
    }


def image_alt_stats(site_data):

    image_alts = []
    site_no_image = 0

    for site in site_data:

        if site["image_alt"]["count"]["total"] == 0:
            site_no_image += 1
            continue

        image_with_alt_bg = 0
        image_with_alt_bg_img = 0

        for match in site["image_alt"]["matches"]:

            # if the "background" value starts with rgba(0,0,0,0) ignore
            if (
                "background" in match["style"]
                and match["style"]["background"]
                == "rgba(0, 0, 0, 0) none repeat scroll 0% 0% / auto padding-box border-box"
            ):
                continue

            if "background-image" in match["style"]:
                image_with_alt_bg_img += 1

            elif (
                "background" in match["style"] and "url" in match["style"]["background"]
            ):
                image_with_alt_bg_img += 1

            image_with_alt_bg += 1

        image_alts.append(
            {
                "site": site["website"],
                "n_image": site["image_alt"]["count"]["total"],
                "n_image_alt": site["image_alt"]["count"]["withAlt"],
                "n_image_alt_bg": image_with_alt_bg,
                "n_image_alt_bg_img": image_with_alt_bg_img,
            }
        )

    image_alts_df = pd.DataFrame(image_alts)

    image_alts_df.to_csv(OUTPUT_PATH / "image_alt_stats.csv", index=False)

    print("-------------------------")
    print("IMAGE ALT STATS")
    print(f"Number of sites with no image: {site_no_image}")
    print(
        f"Number of sites with image: {len(image_alts_df)} / {len(site_data)} ({len(image_alts_df) / len(site_data) * 100:.2f}%)"
    )
    print(
        f"Number of sites with image alt: {len(image_alts_df[image_alts_df['n_image_alt'] > 0])} / {len(image_alts_df)} ({len(image_alts_df[image_alts_df['n_image_alt'] > 0]) / len(image_alts_df) * 100:.2f}%)"
    )
    print(
        f"Number of sites with image alt background: {len(image_alts_df[image_alts_df['n_image_alt_bg'] > 0])} / {len(image_alts_df)} ({len(image_alts_df[image_alts_df['n_image_alt_bg'] > 0]) / len(image_alts_df) * 100:.2f}%)"
    )
    print(
        f"Number of sites with image alt background image: {len(image_alts_df[image_alts_df['n_image_alt_bg_img'] > 0])} / {len(image_alts_df)} ({len(image_alts_df[image_alts_df['n_image_alt_bg_img'] > 0]) / len(image_alts_df) * 100:.2f}%)"
    )
    print(
        f"Average number of image with alt: {image_alts_df['n_image_alt'].mean(): .2f} +/- {image_alts_df['n_image_alt'].std() : .2f}"
    )
    print(f"Median number of image with alt: {image_alts_df['n_image_alt'].median()}")
    print(f"Max number of image with alt: {image_alts_df['n_image_alt'].max()}")
    print(f"Min number of image with alt: {image_alts_df['n_image_alt'].min()}")
    print(
        f"Average number of image with alt background: {image_alts_df['n_image_alt_bg'].mean(): .2f} +/- {image_alts_df['n_image_alt_bg'].std() : .2f}"
    )
    print(
        f"Median number of image with alt background: {image_alts_df['n_image_alt_bg'].median()}"
    )
    print(
        f"Max number of image with alt background: {image_alts_df['n_image_alt_bg'].max()}"
    )
    print(
        f"Min number of image with alt background: {image_alts_df['n_image_alt_bg'].min()}"
    )
    print(
        f"Average number of image with alt background image: {image_alts_df['n_image_alt_bg_img'].mean(): .2f} +/- {image_alts_df['n_image_alt_bg_img'].std() : .2f}"
    )
    print(
        f"Median number of image with alt background image: {image_alts_df['n_image_alt_bg_img'].median()}"
    )
    print(
        f"Max number of image with alt background image: {image_alts_df['n_image_alt_bg_img'].max()}"
    )
    print(
        f"Min number of image with alt background image: {image_alts_df['n_image_alt_bg_img'].min()}"
    )

    return {
        "count_no_image": site_no_image,
        "count_image": len(image_alts_df),
        "count_image_alt": len(image_alts_df[image_alts_df["n_image_alt"] > 0]),
        "count_image_alt_bg": len(image_alts_df[image_alts_df["n_image_alt_bg"] > 0]),
        "count_image_alt_bg_img": len(
            image_alts_df[image_alts_df["n_image_alt_bg_img"] > 0]
        ),
        "average_image_alt": image_alts_df["n_image_alt"].mean(),
        "median_image_alt": image_alts_df["n_image_alt"].median(),
        "max_image_alt": image_alts_df["n_image_alt"].max(),
        "min_image_alt": image_alts_df["n_image_alt"].min(),
        "average_image_alt_bg": image_alts_df["n_image_alt_bg"].mean(),
        "median_image_alt_bg": image_alts_df["n_image_alt_bg"].median(),
        "max_image_alt_bg": image_alts_df["n_image_alt_bg"].max(),
        "min_image_alt_bg": image_alts_df["n_image_alt_bg"].min(),
        "average_image_alt_bg_img": image_alts_df["n_image_alt_bg_img"].mean(),
        "median_image_alt_bg_img": image_alts_df["n_image_alt_bg_img"].median(),
        "max_image_alt_bg_img": image_alts_df["n_image_alt_bg_img"].max(),
        "min_image_alt_bg_img": image_alts_df["n_image_alt_bg_img"].min(),
    }


def iframe_post_message_stats(site_data):

    iframe_post_message = []

    for site in site_data:

        iframe_post_message.append(
            {
                "site": site["website"],
                "n_iframe": site["iframe_post_message"]["count"]["iframes"],
                "n_listen": site["iframe_post_message"]["count"]["listenMessage"],
                "n_post": site["iframe_post_message"]["count"]["postMessage"],
                "n_static_post": site["iframe_post_message"]["count"][
                    "staticPostMessage"
                ],
            }
        )

    iframe_post_message_df = pd.DataFrame(iframe_post_message)

    iframe_post_message_df.to_csv(
        OUTPUT_PATH / "iframe_post_message_stats.csv", index=False
    )

    print("-------------------------")
    print("IFRAME POST MESSAGE STATS")
    print(
        f"Number of sites with iframe: {len(iframe_post_message_df[iframe_post_message_df['n_iframe'] > 0])} / {len(iframe_post_message_df)} ({len(iframe_post_message_df[iframe_post_message_df['n_iframe'] > 0]) / len(iframe_post_message_df) * 100:.2f}%)"
    )
    print(
        f"Number of sites with iframe post message: {len(iframe_post_message_df[iframe_post_message_df['n_post'] > 0])} / {len(iframe_post_message_df)} ({len(iframe_post_message_df[iframe_post_message_df['n_post'] > 0]) / len(iframe_post_message_df) * 100:.2f}%)"
    )
    print(
        f"Number of sites with static iframe post message: {len(iframe_post_message_df[iframe_post_message_df['n_static_post'] > 0])} / {len(iframe_post_message_df)} ({len(iframe_post_message_df[iframe_post_message_df['n_static_post'] > 0]) / len(iframe_post_message_df) * 100:.2f}%)"
    )
    print(
        f"Number of sites with listen message: {len(iframe_post_message_df[iframe_post_message_df['n_listen'] > 0])} / {len(iframe_post_message_df)} ({len(iframe_post_message_df[iframe_post_message_df['n_listen'] > 0]) / len(iframe_post_message_df) * 100:.2f}%)"
    )
    print(
        f"Average number of iframe: {iframe_post_message_df['n_iframe'].mean(): .2f} +/- {iframe_post_message_df['n_iframe'].std() : .2f}"
    )
    print(f"Median number of iframe: {iframe_post_message_df['n_iframe'].median()}")
    print(f"Max number of iframe: {iframe_post_message_df['n_iframe'].max()}")
    print(f"Min number of iframe: {iframe_post_message_df['n_iframe'].min()}")
    print(
        f"Average number of listen message: {iframe_post_message_df['n_listen'].mean(): .2f} +/- {iframe_post_message_df['n_listen'].std() : .2f}"
    )
    print(
        f"Median number of listen message: {iframe_post_message_df['n_listen'].median()}"
    )
    print(f"Max number of listen message: {iframe_post_message_df['n_listen'].max()}")
    print(f"Min number of listen message: {iframe_post_message_df['n_listen'].min()}")
    print(
        f"Average number of post message: {iframe_post_message_df['n_post'].mean(): .2f} +/- {iframe_post_message_df['n_post'].std() : .2f}"
    )
    print(f"Median number of post message: {iframe_post_message_df['n_post'].median()}")
    print(f"Max number of post message: {iframe_post_message_df['n_post'].max()}")
    print(f"Min number of post message: {iframe_post_message_df['n_post'].min()}")
    print(
        f"Average number of static post message: {iframe_post_message_df['n_static_post'].mean(): .2f} +/- {iframe_post_message_df['n_static_post'].std() : .2f}"
    )
    print(
        f"Median number of static post message: {iframe_post_message_df['n_static_post'].median()}"
    )
    print(
        f"Max number of static post message: {iframe_post_message_df['n_static_post'].max()}"
    )
    print(
        f"Min number of static post message: {iframe_post_message_df['n_static_post'].min()}"
    )

    return {
        "count_iframe": len(
            iframe_post_message_df[iframe_post_message_df["n_iframe"] > 0]
        ),
        "count_post_message": len(
            iframe_post_message_df[iframe_post_message_df["n_post"] > 0]
        ),
        "count_static_post_message": len(
            iframe_post_message_df[iframe_post_message_df["n_static_post"] > 0]
        ),
        "count_any_post_message": len(
            iframe_post_message_df[
                (iframe_post_message_df["n_post"] > 0)
                | (iframe_post_message_df["n_static_post"] > 0)
            ]
        ),
        "count_listen_message": len(
            iframe_post_message_df[iframe_post_message_df["n_listen"] > 0]
        ),
        "average_iframe": iframe_post_message_df["n_iframe"].mean(),
        "median_iframe": iframe_post_message_df["n_iframe"].median(),
        "max_iframe": iframe_post_message_df["n_iframe"].max(),
        "min_iframe": iframe_post_message_df["n_iframe"].min(),
        "average_listen_message": iframe_post_message_df["n_listen"].mean(),
        "median_listen_message": iframe_post_message_df["n_listen"].median(),
        "max_listen_message": iframe_post_message_df["n_listen"].max(),
        "min_listen_message": iframe_post_message_df["n_listen"].min(),
        "average_post_message": iframe_post_message_df["n_post"].mean(),
        "median_post_message": iframe_post_message_df["n_post"].median(),
        "max_post_message": iframe_post_message_df["n_post"].max(),
        "min_post_message": iframe_post_message_df["n_post"].min(),
        "average_static_post_message": iframe_post_message_df["n_static_post"].mean(),
        "median_static_post_message": iframe_post_message_df["n_static_post"].median(),
        "max_static_post_message": iframe_post_message_df["n_static_post"].max(),
        "min_static_post_message": iframe_post_message_df["n_static_post"].min(),
    }


def animation_stats(site_data):

    stats = []

    for site in site_data:
        
        if "animation" not in site:
            continue

        try:
            stats.append(
                {
                    "site": site["website"],
                    "n_animations": len(site["animation"]),
                    "n_background": len([f for f in site["animation"] if f["hasBackground"]]),
                    "n_background_image": len(
                        [f for f in site["animation"] if f["hasBackgroundImage"]]
                    ),
                    "n_makes_request": len(
                        [f for f in site["animation"] if f["makesRequest"]]
                    ),
                }
            )
        except Exception as e:
            print(site['animation'])
            print(e)

    stats_df = pd.DataFrame(stats)

    stats_df.to_csv(OUTPUT_PATH / "animation_stats.csv", index=False)

    print("-------------------------")
    print("ANIMATION STATS")
    print(
        f"Number of sites with animation: {len(stats_df[stats_df['n_animations'] > 0])} / {len(stats_df)} ({len(stats_df[stats_df['n_animations'] > 0]) / len(stats_df) * 100:.2f}%)"
    )
    print(
        f"Number of sites with background animation: {len(stats_df[stats_df['n_background'] > 0])} / {len(stats_df)} ({len(stats_df[stats_df['n_background'] > 0]) / len(stats_df) * 100:.2f}%)"
    )
    print(
        f"Number of sites with background image animation: {len(stats_df[stats_df['n_background_image'] > 0])} / {len(stats_df)} ({len(stats_df[stats_df['n_background_image'] > 0]) / len(stats_df) * 100:.2f}%)"
    )
    print(
        f"Number of sites with animation that makes request: {len(stats_df[stats_df['n_makes_request'] > 0])} / {len(stats_df)} ({len(stats_df[stats_df['n_makes_request'] > 0]) / len(stats_df) * 100:.2f}%)"
    )
    print(
        f"Average number of animations: {stats_df['n_animations'].mean(): .2f} +/- {stats_df['n_animations'].std() : .2f}"
    )
    print(f"Median number of animations: {stats_df['n_animations'].median()}")
    print(f"Max number of animations: {stats_df['n_animations'].max()}")
    print(f"Min number of animations: {stats_df['n_animations'].min()}")
    print(
        f"Average number of background animations: {stats_df['n_background'].mean(): .2f} +/- {stats_df['n_background'].std() : .2f}"
    )
    print(
        f"Median number of background animations: {stats_df['n_background'].median()}"
    )
    print(f"Max number of background animations: {stats_df['n_background'].max()}")
    print(f"Min number of background animations: {stats_df['n_background'].min()}")
    print(
        f"Average number of background image animations: {stats_df['n_background_image'].mean(): .2f} +/- {stats_df['n_background_image'].std() : .2f}"
    )
    print(
        f"Median number of background image animations: {stats_df['n_background_image'].median()}"
    )
    print(
        f"Max number of background image animations: {stats_df['n_background_image'].max()}"
    )
    print(
        f"Min number of background image animations: {stats_df['n_background_image'].min()}"
    )
    print(
        f"Average number of animations that makes request: {stats_df['n_makes_request'].mean(): .2f} +/- {stats_df['n_makes_request'].std() : .2f}"
    )
    print(
        f"Median number of animations that makes request: {stats_df['n_makes_request'].median()}"
    )
    print(
        f"Max number of animations that makes request: {stats_df['n_makes_request'].max()}"
    )
    print(
        f"Min number of animations that makes request: {stats_df['n_makes_request'].min()}"
    )

    return {
        "count_animation": len(stats_df[stats_df["n_animations"] > 0]),
        "count_background": len(stats_df[stats_df["n_background"] > 0]),
        "count_background_image": len(stats_df[stats_df["n_background_image"] > 0]),
        "count_makes_request": len(stats_df[stats_df["n_makes_request"] > 0]),
        "average_animation": stats_df["n_animations"].mean(),
        "median_animation": stats_df["n_animations"].median(),
        "max_animation": stats_df["n_animations"].max(),
        "min_animation": stats_df["n_animations"].min(),
        "average_background": stats_df["n_background"].mean(),
        "median_background": stats_df["n_background"].median(),
        "max_background": stats_df["n_background"].max(),
        "min_background": stats_df["n_background"].min(),
        "average_background_image": stats_df["n_background_image"].mean(),
        "median_background_image": stats_df["n_background_image"].median(),
        "max_background_image": stats_df["n_background_image"].max(),
        "min_background_image": stats_df["n_background_image"].min(),
        "average_makes_request": stats_df["n_makes_request"].mean(),
        "median_makes_request": stats_df["n_makes_request"].median(),
        "max_makes_request": stats_df["n_makes_request"].max(),
        "min_makes_request": stats_df["n_makes_request"].min(),
    }


def make_json_serializable(obj):
    if isinstance(obj, np.int64):
        return int(obj)

    elif isinstance(obj, np.float64):
        return float(obj)

    elif isinstance(obj, dict):
        return {k: make_json_serializable(v) for k, v in obj.items()}

    elif isinstance(obj, list):
        return [make_json_serializable(v) for v in obj]

    return obj


stats = {
    "n_sites": len(site_data),
}
stats["lazy_loading"] = lazy_loading_stats(site_data)
stats["container_style"] = container_style_stats(site_data)
stats["image_alt"] = image_alt_stats(site_data)
stats["iframe_post_message"] = iframe_post_message_stats(site_data)
stats["animation"] = animation_stats(site_data)

with open(OUTPUT_PATH / "stats.json", "w") as f:
    f.write(json.dumps(make_json_serializable(stats), indent=4))
