from common import *

Title("Increasing Filter-List Robustness (Section 7.2)")

ATTACK_NAMES = [
    "baseline",
    "css-animation-attack",
]

for adblocker in ['ublock', 'adguard']:
    fig, ax = plt.subplots(figsize=(4, 4))
    ax2 = ax.twinx()
    colors = ['b', 'r', 'g', 'orange']
    i = 0
    for attack_name in ATTACK_NAMES:
        
        fp = DATA_DIR / "iterative_robustness" / adblocker / attack_name / "filterlist"/ "general"
        
        if not fp.exists():
            continue
        
        stats.iterative_robustness_stats(fp, ax, ax2, colors[i], attack_name)
        i+=1
    
    ax.set_xlabel('Number of iterations')
    ax.set_ylabel('Normalized Shannon Entropy')
    # ax.legend( loc="lower right")
    ax2.grid(None)
    ax2.set_ylabel('Number of rules (x $10^6$)')
    
    # make the spine for the second y-axis visible
    ax2.spines['right'].set_visible(True)
    
    fig.savefig(PAPER_FIGURES_DIR / ("iterative_robustness_{}.pdf".format(adblocker)), bbox_inches='tight')
    
    Link(f"Figure 5.a: Iterative Robustness for {adblocker} saved to: {PAPER_FIGURES_DIR / ('iterative_robustness_{}.pdf'.format(adblocker))}")
    