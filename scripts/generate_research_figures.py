import csv
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

RESULTS = Path("results")
FIGURES = Path("figures")
FIGURES.mkdir(exist_ok=True)

# ==================================================
# FIGURE 1: DEPENDABILITY COMPARISON
# ==================================================

with open(
    RESULTS / "comparison_all_systems.csv",
    newline="",
    encoding="utf-8"
) as f:
    data = list(csv.DictReader(f))

names = [r["system"] for r in data]

correct = np.array([
    float(r["correct_rate_pct"]) for r in data
])

wrong = np.array([
    float(r["wrong_acceptance_pct"]) for r in data
])

unavailable = np.array([
    float(r["rejection_or_unavailable_pct"])
    for r in data
])

y = np.arange(len(names))

fig, ax = plt.subplots(figsize=(13, 9))

ax.barh(
    y,
    correct,
    label="Correct answers"
)

ax.barh(
    y,
    wrong,
    left=correct,
    label="Incorrect answers accepted"
)

ax.barh(
    y,
    unavailable,
    left=correct + wrong,
    label="Rejected / unavailable"
)

ax.set_yticks(y)
ax.set_yticklabels(names, fontsize=9)
ax.invert_yaxis()

ax.set_xlabel("Percentage of test inputs (%)")
ax.set_title(
    "Dependability of Individual LLMs and N-Version Voting"
)

ax.set_xlim(0, 100)
ax.grid(axis="x", alpha=0.25)
ax.set_axisbelow(True)

ax.legend(
    loc="upper center",
    bbox_to_anchor=(0.5, -0.07),
    ncol=3
)

plt.tight_layout()

fig.savefig(
    FIGURES / "dependability_comparison.png",
    dpi=300,
    bbox_inches="tight"
)

fig.savefig(
    FIGURES / "dependability_comparison.svg",
    bbox_inches="tight"
)

plt.close(fig)

# ==================================================
# FIGURE 2: PAIRWISE FAILURE OVERLAP
# ==================================================

with open(
    RESULTS / "failure_overlap_summary.csv",
    newline="",
    encoding="utf-8"
) as f:
    overlap = list(csv.DictReader(f))

overlap.sort(
    key=lambda r: float(r["joint_failure_rate_pct"])
)

pair_names = [
    f"{r['model1'].upper()} + {r['model2'].upper()}"
    for r in overlap
]

failure_rates = [
    float(r["joint_failure_rate_pct"])
    for r in overlap
]

wrong_agreements = [
    int(r["agreed_wrong"])
    for r in overlap
]

fig, ax = plt.subplots(figsize=(11, 6))

bars = ax.barh(
    pair_names,
    failure_rates
)

for bar, rate, agreed in zip(
    bars,
    failure_rates,
    wrong_agreements
):
    ax.text(
        rate + 1,
        bar.get_y() + bar.get_height() / 2,
        f"{rate:.2f}%  |  {agreed} wrong agreement(s)",
        va="center",
        fontsize=9
    )

ax.set_xlim(0, 115)
ax.set_xlabel("Joint failure rate (%)")

ax.set_title(
    "Overlapping Failures Across LLM Pairs"
)

ax.grid(axis="x", alpha=0.25)
ax.set_axisbelow(True)

plt.tight_layout()

fig.savefig(
    FIGURES / "failure_overlap.png",
    dpi=300,
    bbox_inches="tight"
)

fig.savefig(
    FIGURES / "failure_overlap.svg",
    bbox_inches="tight"
)

plt.close(fig)

print("=" * 60)
print("Research figures generated successfully.")
print("=" * 60)

print("\nFigure 1:")
print("figures/dependability_comparison.png")

print("\nFigure 2:")
print("figures/failure_overlap.png")

print("\nBoth figures are also saved in SVG format.")
