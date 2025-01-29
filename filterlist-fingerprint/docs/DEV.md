## Setting up the development environment
Before you start developing, 
1. install conda
2. clone the repository
3. Create conda environment as explained in the next section
4. Activate the conda environment
5. Run 
    ```bash
    bash scripts/manage/manage.sh init
    ```
6. If you have libraries in `src` folder, install them according to the instructions in "Installing the libraries" section.

## Environment management
### Creating conda environment from YAML file
```bash
conda env create --file environment.yml
```

### Activating conda environment
```bash
conda activate ./env
```

### Updating conda environment from YAML file
```bash
conda env update --prefix ./env --file environment.yml  --prune
```

### Adding a new package
1. install it manually using conda or pip
2. add it to the environment.yml file

## Development

### Adding libraries for reusable code.
Any "project", "tool", "library", "pipeline" that represent reusable code or is the subject of the study should be added as a library in the `src` folder. Add a new library by running the following command:
```bash
bash scripts/manage/manage.sh lib add <library_name>
```

### Installing the libraries
In case you added a library automatically, or would like to install existing libraries, run the following command:
```bash
bash scripts/manage/manage.sh lib install
```
