# Reproducing Results

We can divide the flow to produce the results into three consecutive steps:
- **(I) Data Collection**: Collect the data from the internet. 
- **(II) Data Processing**: Process the data to compute the fingerprints, stability results, and other intermediate representations. 
- **(III) Statistics and Figures**: Analyze the data and produce the results appearing in the paper.

We recognize four experimental outcomes:
- (F) **Fingerprinting Study**: Study the power of different attacks to uniquely identify filter lists and users (Paper Sections 6.1 and 6.2).
- (S) **Stability Study**: Study the stability of the filter lists over time and the fingerprinting templates accordingly (Paper Section 6.3).
- (D) **Domain Coverage Study**: Study the domain coverage required by attackers to gain advantage (Paper Section 6.4).
- (R) **Robustness to Mitigations Study**: Study the robustness of filter-list fingerprints to mitigations (Paper Section 7.2).


For each step, we can provide precomputed data as input (`data.zip`) which can be extracted to fill `./data` folder. However, we also provide the scripts to reproduce all data from scratch.

We can also provide a **Docker image** with pre-installed dependencies to run the scripts.

## Supported Ad blocker Data Sources
- `adguard`: [Adguard Github Issues](https://github.com/AdguardTeam/AdguardFilters/issues)
- `ublock`: [Ublock Origin Github Issues](https://github.com/uBlockOrigin/uAssets/issues)


>[!NOTE]
>
> ## How are commands specified
>
> We use [Hydra](https://hydra.cc/) to manage the configuration files. Hydra allows us to define configuration files in YAML format and override them from the command line. We provide default configuration files in the `conf/` directory. You can override the default configuration by specifying the configuration file and the parameters you want to override.
> 
> For example if a configuration file `conf/scrape.conf.yaml` contains the following configuration:
> 
> ```yaml
> pages_limit: 10
> duration:
>     start: 2021-01-01
>     end: 2021-01-31
> ```
> 
> to override the `pages_limit` parameter and `duration.start` parameter, you can run the following command:
> 
> ```bash
> python scrape.py forum=adguard pages_limit=5 duration.start=2021-01-15
> ```

## (I) Data Collection

This steps collects the data from the internet. If you intend to reproduce this data, you might find variations that depend on the dataset parameters you choose (e.g. the number of forum issues, the date range, etc.).

The following table contains the source data to download and instructions to download them. 

| Data Source | Description | Pre-Download Instructions |  Download Script | Download Options | Output Folder | Post-Download Instructions |
| --- | --- | --- | --- | --- | --- | --- |
| Github Issues | github issues to get the configurations of the filterlists | - | `python scripts/run/issues.py forum=<adblocker>` | Override options from [issues.conf.yaml](../conf/issues.conf.yaml) in the command like date range or page limit. **We recommend you define at least `pages_limit` or `date_limit`  | `data/issues/<adblocker>/<timestamp>/issues_confs.csv` | Update `<adblocker>_CONFS_DIR` `scripts/paper_stats/common.py`<br/><br/> If the adblocker is `ublock`, deduplicate posts with `python scripts/run/issues.py forum=ublock +forum.dedup_from=<downloaded-ublock-issues-dir>`, then update `UBLOCK_DEDUP_CONFS_DIR` with the same dir in the command.  |
| Filterlists | filterlist files containing rules | - | `python scripts/run/filterlists.py action=download filterlists=<adblocker>` | - | `data/filterlists/<adblocker>/download/default` | Parse the rules and extract their metadata using <br> `python scripts/run/filterlists.py action=parse filterlists=<adblocker> parse.download_fp=<path-to-download-dir>` | 
| Github Commits | Only required for outcome S. Ad-blocker rule changes commit history | - |  `python scripts/run/commits.py action=scrape forum=<adblocker> filterlists=<adblocker>` | Override options from [commits.conf.yaml](../conf/commits.conf.yaml) in the command like date range or page limit| `data/commits/<adblocker>/scrape/<timestamp>/changes.csv` | Parse commits `python scripts/run/commits.py forum=<adblocker> filterlists=<adblocker> action=parse parse.scrape_fp=<commits-scrape-path>`. Update `<adblocker>_COMMITS_FP` in `scripts/paper_stats/common.py` |
| Rule Last Seen | Only required for outcome S. measuring the last time a filter rule is seen. Depends on the *Filterlists* data. | Requires having **(II) Data Processing** and attack summaries | `python scripts/run/commits.py forum=<adblocker> filterlists=<adblocker> action=history filterlists=<adblocker>` | Override options from [commits.conf.yaml](../conf/commits.conf.yaml) in the command like time intervals `history.deltas` or attack type `attack_type=null\|targeted\|general`| `data/commits/<adblocker>/history/<timestamp>/` | Update `scripts/paper_stats/common.py` with the correct path and timestamp `<adblocker>_RULE_LAST_SEEN_DOWNLOAD_TIMESTAMP` and `<adblocker>_RULE_LAST_SEEN_FP` |

## (II) Data Processing

In this step, we transform downloaded datasets into intermediate representations conditioned by the attack to study. We also provide precomputed data for this step in `data.zip`.

### Supported Browser Attacks

We support multiple attacks based on which rules they can detect. The following table lists the supported attacks and the rules they can detect. To add a new attack or modify an existing one, update the `conf/attack` directory.

| Attack Name | Description | Rules Detected |
| --- | --- | --- |
| `default` | Use all possible rules | All |
| `baseline` | Baseline attack from paper | Cosmetic and Network Rules |
| `css-animation-attack` | CSS Animation Attacks | *Generic* Cosmetic and Network Rules |
| `css-container-query-attack` | CSS Container Query Attacks | *Generic* Cosmetic Rules that *hide* elements |
| `stat-generic` | Used to generate statistics about using all generic rules | *Generic* Cosmetic and Network Rules |
| `stat-generic-network` | Used to generate statistics about using all generic network rules | *Generic* Network Rules |
| `stat-generic-cosmetic` | Used to generate statistics about using all generic cosmetic rules | *Generic* Cosmetic Rules |

Now we detail the specific preprocessing steps in order of dependency.

### II.1 Attack-specific Filter-list datasets

To generate an attack-specific filter-list rules dataset, run the following command:

```bash
python scripts/run/filterlists.py action=fingerprint filterlists=<adblocker> 
attack=<attack-name>
fingerprint.issues_fp=<path-to-dir-containing-issues-confs-csv>
```

This will create 
- a copy of the issues csv into `issues_confs_identified.csv` with a new column `identifiable_lists` containing the lists that are identifiable by the attack.
- a csv file containing the encoded activated rule set for each issue in `user_rules.csv` representing a fingerprinting vector.

### II.2 Running Fingerprinting Attacks (Outcome F)

After creating the attack-specific filter-list datasets, we can run the fingerprinting attacks to identify the filter lists and users, and compute the optimal fingerprinting templates. We adapted fingerprinting attack with size constraints methods from Gulyas et al. [1]. We implement two methods of the attack "Targeted" and "General".

**You have to at least run the attacks for `baseline`, `css-animation-attack`, `stat-*` attacks to reproduce the results in the paper.**

#### II.2.1 Targeted Attack

```bash
python scripts/run/fingerprinting.py \
     method=targeted \ 
     encoding=filterlist \ 
     adblocker=<adblocker> \
     attack=<attack-name> \
```

This generates a csv file `data/fingerprinting/<adblocker>/<attack-name>filterlist/targeted/fingerprints.csv`.

#### II.2.2 General Attack

```bash
python scripts/run/fingerprinting.py -m \
    method=general \
    adblocker=<adblocker> \
    attack=<filterlist-attack-name> \
    general.max_size=5,10,15,20,25,30,35,40,45,50,55,60,70,80,90
```

This generates multiple runs for different `max_size` values and stores associated fingerprint vectors in `fingerprint.json` files. You can set the values to iterate over as you wish.

### II.3 Attack Summary (Outcome S)

To be able to run the stability study, we need to run the attack summarization script. This script will summarize the attack results that are used in the stability study.

```bash
python scripts/run/summarize_attack_rules.py \
    adblocker=<adblocker> \
    attack=<attack-name> 
```

This generates a directory containing the summary in `data/fingerprinting/<adblocker>/<attack-name>/filterlist/summary/`.

### II.4 Iterative Robustness Experiment (Outcome R)

To run the iterative robustness experiment, we need to run the following script:

```bash
python scripts/run/iterative_robustness.py \
    adblocker=<adblocker> \
    attack=<attack-name> 
```

This generates a directory containing the results in `data/iterative_robustness/<adblocker>/<attack-name>/`.

Additional options can be set in the command line to override the default values in the configuration file [iterative_robustness.conf.yaml](../conf/iterative_robustness.conf.yaml).

### II.5 Domain Coverage Study (Outcome D)

To run the domain coverage study for each list of an ad-blocker, we need to run the following script:

```bash
python scripts/run/domain_coverage.py \
    filterlists=<adblocker>
```

This will output the coverage results per list in separate folders.

Next, to generate the analysis of the results and aggregate the results, run the following script:

```bash
python scripts/run/domain_coverage.py \
    filterlists=<adblocker> \
    action=analyze
```
This will generate a `data/filterlists/<adblocker>/domain_coverage/.analysis` folder containing the aggregated results.

## (III) Statistics and Figures

This step requires the precomputed data from the previous steps. As a reminder, we provide the precomputed data in `data.zip`.

All scripts to generate the figures and statistics present in the paper can be found in `scripts/paper_stats/`. Figures and tables will be stored in `scripts/paper_stats/figures/`.

We organize the scripts per paper section:
- `5_dataset_stats.py`: Generate statistics about the dataset (Section 5).
- `6_1_rule_and_list_coverage.py`: Stats and figures for the filter list coverage study (Section 6.1).
- `6_2_reducing_user_anonymity.py`: Stats and figures for the user identification study (Section 6.2).
- `6_3_stability.py`: Stats and figures for the stability study (Section 6.3).
- `6_4_domain_coverage.py`: Stats and figures for the domain coverage study (Section 6.4).
- `7_2_iterative_robustness.py`: Stats and figures for the robustness to mitigations study (Section 7.2).

You can run any script from the terminal and get the statistics printed to the terminal:

```bash
python scripts/paper_stats/<script-name>.py
```

# Reproducibility Limitations
* GitHub forum changes for the ad-blockers that change their structures.
* Filter-lists changing their source-content URL or repository structure. 
* If you plan to re-download filter list files, their content will must surely have changed since the original study. 

# FAQ

## I got `gh_scraper.scrape_issues.IssueListError: Invalid response: <Response [500]> - ` error while scraping issues. What should I do?

This seems to be a GitHub API rate limit issue. You can try to run the script again after a while. If you still face the issue, you can try to reduce the `pages_limit` in the configuration file to scrape fewer pages at a time.

----
*References* 

[\[1\]]([1]) Gabor Gyorgy Gulyas, Gergely Acs, Claude Castelluccia: Near-Optimal Fingerprinting with Constraints. PET Symposium 2016.