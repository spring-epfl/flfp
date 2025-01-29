## Supported Ad blocker Data Sources
- `adguard`: [Adguard Github Issues](https://github.com/AdguardTeam/AdguardFilters/issues)
- `ublock`: [Ublock Origin Github Issues](https://github.com/uBlockOrigin/uAssets/issues)

All data will be stored in the `data` directory.

# 1.1 Github Issues

First we need to scrape the github issues to get the configurations of the filterlists. 

The configuration to run the script is in [`conf/issues.conf.yml`](../conf/issues.conf.yml)

Crawl issues by running the following command:

```bash 
python scripts/run/issues.py forum=<adblocker>
```

This will generate a csv file containing scraped issues in `data/issues/<adblocker>/<timestamp>/issues_confs.csv`, including one important column `filters` which contains the filter lists used by the user encoded in a json list.


# 1.2. Filterlists

To get the filterlists source URLs, we compile the [default ones](https://adguard.com/kb/general/ad-filtering/adguard-filters/). We add extra lists that are prominent and used by users in the issues dataset from the [filter registery](https://raw.githubusercontent.com/AdguardTeam/FiltersRegistry) hosted by adguard.

## 1.2.1. Download the filter list text files
Run the following command
```bash
python scripts/run/filterlists.py action=download filterlists=<adblocker>
```
Lists will be downloaded to `data/filterlists/<adblocker>/download/default`

## 1.2.2. Parse the filter lists
We extract metadata for the filter-rules to filter them later on by choice of attack. Run the following command
```bash
python scripts/run/filterlists.py action=parse filterlists=<adblocker> parse.download_fp=<path-to-dir-containing-lists>
```

This will generate a csv file for each list in `data/filterlists/<adblocker>/parsed/default`. 

## 1.2.3. Create attack datasets
Because different attacks detect different filter rules, they can uniquely identify different number of filter lists. We prepare datasets for each type of attack by filtering rules. 

```
python scripts/run/filterlists.py action=fingerprint filterlists=<adblocker> 
attack=<attack-name>
fingerprint.parse_fp=<path-to-dir-containing-parsed-lists>
fingerprint.issues_fp=<path-to-issues-confs-csv>
```

**Default attacks**:
In the `conf/attack` directory, we have the following attacks:
- `css-container-query-attack`
- `css-nth-child-attack`
- `iframe-observer-attack`
- `image-alt-attack`
- `lazy-image-loading-attack`

This will create 
- a copy of the issues csv into `issues_confs_identified.csv` with a new column `identifiable_lists` containing the lists that are identifiable by the attack.
- a csv file containing the encoded activated rule set for each issue in `user_rules.csv` representing a fingerprinting vector.

