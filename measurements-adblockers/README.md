# Benchmarking adblocking extensions for performance fingerprinting attack metrics

The repository contains the web crawling code for collecting and processing web data regarding ad-blocker performance and web feature popularity.

# Acknowledgments

This codebase is an adaptation of [the codebase](https://github.com/Racro/measurements_user-concerns) for the work done by Roongta et al. [1].

This code has been used to obtain (fully/partially) the results of following research article [`From User Insights to Actionable Metrics: A User-Focused Evaluation of Privacy-Preserving Browser Extensions`](https://doi.org/10.1145/3634737.3657028) - AsiaCCS 2024

>[!NOTE]
>
>This code is for research purposes and not a production level code. Hence it could have bugs/issues. Please feel free to raise issues on the repo or contact the author directly. Pull requests are also welcome and will be entertained.

# Setup

Create a Python3 virtual environment and install the required dependencies from `requirements.txt`.

To reproduce the results, you need to perform the following steps:
1. [Data Collection](#data-collection): Collect the data for ad-blocker performance and web feature popularity. We also provide pre-collected data that can be extracted into this code base within `data_usenix` folder. 

2. [Data Processing](#data-processing): Generate the statistics and plots from the collected data.


## Prerequisites
- `python3` and `python3.10-venv`
- `docker`

## Data Collection

### Ad-blocker CPU Performance
We measure the ad-blocker performance (`adguard` and `ublock`) while using different number of filter-lists (no filterlists, mid, and all).

Inside the `performance/docker` folder, run the command 
```
bash run.sh logs/ ../../websites_inner_pages.json cpu {#cpus} chrome
```

You can use `websites_inner_pages-demo.json` instead of `websites_inner_pages.json` for a smaller dataset to test the code. 

The second argument is the website pool that can be altered. Pass a number in place `#cpus` to open multiple chrome browser instances according to your hardware capabilities. Currently the code only supports chrome but can be easily extended to firefox.

The data is stored inside `performance/docker/chrome/data` folder.

### Web Feature Popularity

We gather the frequency of HTML, CSS, and JavaScript features on the web, relevant to the attacks we propose. 

Inside the docker folder, run the command 
```
bash run.sh logs/ ../../websites_inner_pages.json web {#cpus} chrome
```
You can use `websites_inner_pages-demo.json` instead of `websites_inner_pages.json` for a smaller dataset to test the code. 

The data is stored inside `performance/docker/chrome/webdata` folder.

## Data Processing

To process the data, run the following commands inside the `performance/process` folder. *Note: all paths in the commands must be absolute paths.*

### Ad-blocker CPU Performance

```
python process_cpu_data.py <PATH TO DATA FOLDER> <OUTPUT FOLDER PATH>
```

If you have the pre-collected data, it will be stored in the `data_usenix/cpudata` folder; otherwise, you can find it in `performance/docker/chrome/data`.

### Web Feature Popularity

```
python process_web_data.py <PATH TO DATA FOLDER> <OUTPUT FOLDER PATH>
```

If you have the pre-collected data, it will be stored in the `data_usenix/webdata` folder; otherwise, you can find it in `performance/docker/chrome/webdata`.

# References
[1] Roongta, R., & Greenstadt, R. (2024). [From User Insights to Actionable Metrics: A User-Focused Evaluation of Privacy-Preserving Browser Extensions](https://doi.org/10.1145/3634737.3657028). In Proceedings of the ACM Asia Conference on Computer and Communications Security (ASIA CCS ’24).