# get the path of the bash script
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
SRC_DIR=$DIR/../../src

# pip or pip3
if [ -x "$(command -v pip3)" ]; then
    pip3=pip3
else
    pip3=pip
fi

# define a function to install a library
function install_lib {
    lib_name=$1
    setup_file=$SRC_DIR/$lib_name/setup.py
    if [ -f $setup_file ]; then
        echo "Installing library $lib_name"
        pip3 install -e $SRC_DIR/$lib_name
    else
        echo "Library $lib_name does not exist"
    fi
}

# if first argument is add <lib_name> then add the library to the project

if [ "$1" == "add" ]; then
    lib_name=$2
    if [ -d "$SRC_DIR/$lib_name" ]; then
        echo "Library $lib_name already exists"
        install_lib $lib_name
    # make sure library not installed in pip
    elif pip show $lib_name > /dev/null; then
        echo "Library $lib_name already installed in pip"
    else
        echo "Adding library $lib_name"
        mkdir -p $SRC_DIR/$lib_name
        mkdir -p $SRC_DIR/$lib_name/$lib_name
        touch $SRC_DIR/$lib_name/$lib_name/__init__.py
        
        # create setup.py
        cat > $SRC_DIR/$lib_name/setup.py <<EOF
from setuptools import setup, find_packages

setup(
    name='$lib_name',
    version='0.1',
    packages=find_packages(),
    install_requires=[
        # add dependencies here
    ]
)
EOF
        echo "Library $lib_name added"
        install_lib $lib_name
    fi

fi

# if first argument is install <lib_name> then install the library
# if first argument is install then install all libraries

if [ "$1" == "install" ]; then
    if [ "$2" ]; then
        install_lib $2
    else
        for lib in $SRC_DIR/*; do
            if [ -d $lib ]; then
                install_lib $(basename $lib)
            fi
        done
    fi
fi
