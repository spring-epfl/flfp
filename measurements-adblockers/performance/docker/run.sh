#!/bin/bash

# running cmd: bash run.sh logs inner_list.json chrome

set -e

# Check if the correct number of arguments are provided
if [ "$#" -ne 5 ]; then
    echo "Usage: bash $0 <LOGS_PATH> <DOMAINS_LIST_PATH> <METRIC> <CPUS> <BROWSER>"
    echo "Example: bash $0 logs  ../../websites_inner_pages.json cpu 4 chrome"
    exit 1
fi

SELFPATH=$(dirname $(realpath "$0"))
LOGS=$(realpath "${1}")
DOMAINS_LIST=$(realpath "${2}")
METRIC=${3}
CPUS=${4}
BROWSER=${5}

mkdir -p ${LOGS}

# if [ "${3}" = "cpu" ] || [ "${3}" = "ram" ]; then 
#     echo "Testing for Metric ${METRIC}"
# else 
#     echo "Metric not in cpu|ram"
#     exit 0
# fi 

if [ "${5}" = "chrome" ] || [ "${5}" = "firefox" ]; then 
    echo "Testing on Browser ${Browser}"
else 
    echo "Browser not in chrome|firefox"
    exit 0
fi 

pushd "${SELFPATH}/chrome" > /dev/null
make docker
popd > /dev/null

# wrapper.py assumes that various files are in the same directory
# pushd "${SELFPATH}/../docker" > /dev/null

# create data directory with suitable permissions
mkdir -p "${SELFPATH}/chrome/data"
mkdir -p "${SELFPATH}/chrome/webdata"
sudo chmod 777 "${SELFPATH}/chrome/data"
sudo chmod 777 "${SELFPATH}/chrome/webdata"

# source ~/work/pes/pes/bin/activate
python3 -m venv ./measure
source ./measure/bin/activate

# while true; do
UUID=$(uuidgen -t)
echo "Starting measurement run '${UUID}' at $(date)"
python3 "${METRIC}_wrapper.py" \
${LOGS}/${UUID}.log \
${DOMAINS_LIST} \
${CPUS} \
${BROWSER}
echo "Completed measurement run '${UUID}' at $(date)"