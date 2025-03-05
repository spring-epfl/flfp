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

We provide two methods to setup the project. The [first method](#local-installation) is to install the project locally; **we prefer this method to reduce project configuration issues**. The [second method](#docker-installation) is to use a docker container with preconfigured environment.

> [!IMPORTANT]
>   
> To be able to scrape issues and commits from GitHub, you need to provide a GitHub API token. You can create a token from [here](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens), and update the `GITHUB_TOKEN` value in the `.env` file.


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

### Docker Installation

1. Create an empty directory `/data` in the root of the project, or extract the `data.zip` file in the root of the project (for the precomputed data).
2. Update the environment variables in `.env` file. You can copy the `.env.example` file and update the values.
    ```bash
    cp .env.example .env
    ```


3. Load the docker image from the docker hub
    ```bash
    docker pull saiidhc/flfp:usenix
    ```
    You can also build the docker image from the Dockerfile in the root of the project.
    ```bash
    docker build -t saiidhc/flfp:usenix --platform=linux/amd64 .
    ```
2. Run the docker image
    ```bash
    docker run -it \
    --env-file .env \
    -v $(pwd)/data:/flfp/data \
    -v $(pwd)/scripts:/flfp/scripts \
    saiidhc/flfp:usenix
    ```
    This command will start the docker container, mount the `/data` directory to the `/flfp/data` directory in the container, and attach your terminal to the container. If you exit the container, the container will be killed including any running processes. We recommend running this command from some terminal multiplexer like `tmux`.

    We add both volumes to be able to access the data and the `scripts/paper_stats/commits.py` script, which you might to edit during the experiment.

## Reproducing the Experiments

To reproduce our results, we provide a comprehensive instruction manual in [docs/REPRODUCING.md](docs/REPRODUCING.md).

## Contributing
- [Developers Guide](docs/DEV.md)

