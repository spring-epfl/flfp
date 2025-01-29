# Double-Edged Shield: On the Fingerprintability of Customized Ad Blockers

Artifact release for our paper "Double-Edged Shield: On the Fingerprintability of Customized Ad Blockers", published at USENIX '25.

In this repository, we provide two of the three code components used in the paper:

- [A. Main Experiment: Fingerprinting Evaluation](#a-main-experiment-fingerprinting-evaluation) in the `/filterlist-fingerprint` directory. Instructions [here](/filterlist-fingerprint/README.md).
- [B. Web Measurements and Ad-Blocker Benchmarking](#b-web-measurements-and-ad-blocker-benchmarking) in the `/measurements-adblockers` directory. Instructions [here](/measurements-adblockers/README.md).

The third component, [C. Proof of Concept Honeypage](#c-proof-of-concept-honeypage), is available in a separate repository at [flfp-demo/flfp-demo.github.io](https://github.com/flfp-demo/flfp-demo-builder).

We also provide pre-scraped and computed datasets in https://zenodo.org/records/14710669.


# System Requirements
All pieces of code should be able to run on any modern operating system (Windows, Linux, MacOS) with Python 3.10 or higher installed. The code has been tested on Ubuntu 20.04 LTS and MacOS 14.2. 

To make it easy to reproduce, we try to offer Dockerfile methods where possible. We recommend using Docker to run the experiments where indicated. Further details are provided in the corresponding source code instructions.

Some components, especially running the fingerprint attacks might take considerable time on end-user machines with limited resources. Also, running the web measurements and ad-blocker benchmarking might require a stable internet connection and increase network traffic (so appropriate care to network usage should be taken).

# Reproducibility Instructions

In general, we provide detailed instruction `README.md` files for reproducing each component in the corresponding directories. The following sections provide a brief overview of each component.

## A. Main Experiment: Fingerprinting Evaluation

The main experiment includes the fingerprinting study including the following study sections: 
- forum issue scraping (Sections 5)
- attack coverage over filter-lists (Section 6.1)
- user anonymity evaluation (Section 6.)
- fingerprint stability evaluation (Section 6.3)
- attacker domain coverage impact on fingerprint quality (Section 6.4)
- iterative robustness mitigation evaluation (Section 7.2)

The pre-collected and pre-computed data files contain directories and files for the various stages and components of the evaluation including issue datasets, parsed filter-list rules, commit history of filter-lists, generated fingerprints, etc.

After extracting the source code, to use the pre-computed dataset, extract the `data-usenix.zip` file which creates a `data` directory. Move the `data` directory to the root of the extracted source code directory.

To run the main experiment, follow the instructions in the [`README.md`](/filterlist-fingerprint/README.md) file in the extracted source code directory.

**Note:** Unless you are using the issues from the pre-collected dataset, the forum issue scraping may intermittently fail due to GitHub API rate limits, and fingerprinting success may vary based on shifts in filter-list selection patterns. The results may vary based on the network conditions, unforeseen changes in the ad-blocking software, changes in ad-blocker forum structures, changes in filter-list repositories structures, etc.

## B. Web Measurements and Ad-Blocker Benchmarking

This component provides supporting in-the-wild measurements for the following:

- benchmarking the impact of increasing filter-lists on ad-blocker runtime performance (Figure 4 and Section 7.1)
- measuring the popularity of web features (HTML, CSS, JS) used by proposed fingerprint attacks (Table A2 and Section 7.3)

After extracting the source code, to use the pre-computed dataset, extract the `measurement-adblocker-data.zip` file which creates a `data` directory. Move the `data` directory anywhere in the extracted source code directory, and make sure to use correct paths to reach the requested directories in the instructions.

To run the web measurements and ad-blocker benchmarking, follow the instructions in the [`README.md`](/measurements-adblockers/README.md) file in the extracted source code directory.

**Note:** Reproducing this artifact depends on the conditions in which the experiment was conducted. The results may vary based on the network conditions, shifts in web design practices, and unforeseen changes in the ad-blocking software.


## C. Proof of Concept Honeypage

We provide the source code necessary to build a local version of the honeypage deployed over https://flfp-demo.github.io/. The honeypage is used to demonstrate
the fingerprinting attack in a controlled environment.

After extracting the source code, to run the honeypage, follow the instructions in the `README.md` file in the extracted source code directory.

You can also directly visit the live honeypage at https://flfp-demo.github.io/.

# Paper

**Double-Edged Shield: On the Fingerprintability of Customized Ad Blockers** Saiid El Hajj Chehade, Ben Stock, Carmela Troncoso *USENIX Security Symposium (USENIX), 2025*

**Abstract** -- Web tracking is expanding to cookie-less techniques, like browser fingerprinting, to evade popular privacy-enhancing web extensions, namely ad blockers. To mitigate tracking, privacy-aware users are motivated to optimize their privacy setups by adopting proposed anti-fingerprinting configurations and customizing ad blocker settings to maximize the number of blocked trackers. However, users’ choices can counter-intuitively undermine their privacy. In this work, we quantify the risk incurred by modifying ad-blocker filter-list selections. We evaluate the fingerprintability of ad-blocker customization and its implications on privacy. We present three scriptless attacks that evade SoTA fingerprinting detectors and mitigations. Our attacks identify 84% of filter lists, capture stable fingerprints with 0.72 normalized entropy, and reduce the relative anonymity set of users to a median of 48 users (0.2% of the population) using only 45 rules out of 577K. Finally, we provide recommendations and precautionary measures to all parties involved.

The full paper link will be provided once available.

## Citation
If you use the code/data in your research, please cite our work as follows:

```bibtex
@inproceedings{ElHajjChehade25FLFP,
  title     = {Double-Edged Shield: On the Fingerprintability of Customized Ad Blockers},
  author    = {Saiid El Hajj Chehade, Ben Stock, Carmela Troncoso},
  booktitle = {USENIX Security Symposium (USENIX)},
  year      = {2025}
}
```


# Contact

For any questions or issues, please contact Saiid El Hajj Chehade at [saiid.elhajjchehade@epfl.ch](mailto:saiid.elhajjchehade@epfl.ch).

