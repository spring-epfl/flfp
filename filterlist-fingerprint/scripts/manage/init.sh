DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

# if data folder does not exist, create it

if [ ! -d "$DIR/../../data" ]; then
    mkdir -p $DIR/../../data
    echo "data directory created"
fi

# if results folder does not exist, create it

if [ ! -d "$DIR/../../results" ]; then
    mkdir -p $DIR/../../results
    echo "results directory created"
fi