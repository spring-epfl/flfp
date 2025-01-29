# 2.3. Fingerprinting Attacks

We adapted fingerprinting attack with size constraints methods from Gulyas *et al.* [1]. Two methods of attacks are implemented:
1. `targeted`: Vector of lists to best identify a specific user.
2. `general`: Vector of lists to best seperate users generally within a dataset of users.

## 2.3.1. Targeted Attack
```bash
python scripts/run/fingerprinting.py \
     method=targeted \ 
     adblocker=<adblocker> \
     attack=<filterlist-attack-name> \
     source_dir=<path-to-issues_conf_identified.csv>
```

This generates a `fingewrprints.csv` file.

For targeted fingerprinting, we also propose a "fast" algorithm which you can enable by setting the option `algorithm='fast'` for the function `targeted_fingerprinting()` in `scripts/run/fingerprinting.py`. The fast algorithm is a heuristic that reduces the number of iterations required to find the optimal fingerprint vector, but it may not always find the optimal solution.

## 2.3.2. General Attack
```bash
python scripts/run/fingerprint.py -m \
    method=general \
    adblocker=<adblocker> \
    attack=<filterlist-attack-name> \
    source_dir=<path-to-issues_conf_identified.csv>
    general.max_size=5,10,15,20,25,30,35,40,45,50,55,60,70,80,90
```

This generates multiple runs for different `max_size` values and stores associated fingerprint vectors in `fingerprint.json` files. You can set the values to iterate over as you wish.

---
[[1]](https://petsymposium.org/popets/2016/popets-2016-0051.php) Gabor Gyorgy Gulyas, Gergely Acs, Claude Castelluccia: Near-Optimal Fingerprinting with Constraints. PET Symposium 2016. 