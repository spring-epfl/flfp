# Double-Edged Shield: On the Fingerprintability of Customized Ad Blockers

Project to explore the use of AdBlocker filterlists to fingerprint users.

## Pre-requisites
- Python 3.X
- NodeJS with npm or yarn

## Folder Structure
- `conf/` : Configuration files for the experiments. parsed with hydra. 
- `data/` : Data files and datasets
- `docs/` : Documentation and notes
- `src/`  : Source code for tools, libraries, and pipelines you develop
- `scripts/` : All scripts associated with running and analyzing the experiments.
    - `run/` : Scripts for running experiments. 
    - `paper_stats/` : Scripts for generating statistics for the paper.
    - `statistics_from_adblockers/` : Statistics provided by adblockers about filter list usage.
    - `manage/` : Scripts for managing the project. Don't modify these scripts unless you know what you are doing.

## Setup

We provide two methods to setup the project. The first method is to install the project locally and the second method is to use a docker container with preconfigured environment.

### Local Installation

1. Clone the repository
2. Install the required python environment from `environment.yml` using conda with the following command:
    ```bash
    conda env create -f environment.yml
    ```

3. Activate the environment
    ```bash
    conda activate scraping
    ```

4. Update the environment variables in `.env` file. You can copy the `.env.example` file and update the values.
    ```bash
    cp .env.example .env
    ```
    
> [!IMPORTANT]
>   
> To be able to scrape issues and commits from GitHub, you need to provide a GitHub API token. You can create a token from [here](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens), and update the `GITHUB_TOKEN` value in the `.env` file.

### Docker Installation

1. Create an empty directory `/data` in the root of the project, or extract the `data.zip` file in the root of the project (for the precomputed data).

1. Load the docker image from the docker hub
    ```bash
    docker pull filterlistfingerprint/filterlistfingerprint:latest
    ```

2. Run the docker image
    ```bash
    docker container create -it \
    -env-file .env \
    -v $(pwd)/data:/flfp/data \
    filterlistfingerprint/filterlistfingerprint:latest
    ```

## Reproducing the Experiments

To reproduce our results, we provide a comprehensive instruction manual in [docs/REPRODUCING.md](docs/REPRODUCING.md).

## Contributing
- [Developers Guide](docs/DEV.md)

