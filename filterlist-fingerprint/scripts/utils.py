from zipp import Path
import numpy as np

def get_attack_names(conf_dir: Path):

    # the name of the yaml files in <project_dir>/conf/attack
    
    return [f.name.split(".yaml")[0]
            for f in (conf_dir / "attack").iterdir() if f.name.endswith(".yaml") 
            # and not f.name == "default.yaml"
            ]
    
    

def logarithmic_bins(values, num_bins):
    
    start = min(values)
    end = max(values)
    
    return np.logspace(np.log10(start), np.log10(end), num_bins)

def logarithmic_bins_base2(values):
    
    start = min(values)
    end = max(values)
    
    bins = []
    
    while start < end:
        bins.append(start)
        start *= 2
    
    return np.array(bins)
    
    