import csv
from collections import defaultdict, Counter

INPUT = "results/final_pair_voting.csv"
OUTPUT = "results/failure_overlap_summary.csv"

with open(INPUT, newline="", encoding="utf-8") as f:
    records = list(csv.DictReader(f))

groups = defaultdict(Counter)

for row in records:

    pair = (row["model1"], row["model2"])
    counts = groups[pair]

    v1 = row["verdict1"]
    v2 = row["verdict2"]
    outcome = row["outcome"]

    if outcome == "UNASSESSED":
        counts["unassessed"] += 1
        continue

    counts["total"] += 1

    if v1 == "PASS" and v2 == "PASS":
        counts["both_correct"] += 1

    elif v1 != "PASS" and v2 != "PASS":
        counts["both_failed"] += 1

    else:
        counts["one_failed"] += 1

    if outcome == "ACCEPTED_WRONG":
        counts["agreed_wrong"] += 1

summary = []

print("\nPAIRWISE FAILURE OVERLAP")
print("=" * 65)

for pair, c in sorted(groups.items()):

    total = c["total"]
    overlap_rate = 100 * c["both_failed"] / total

    print(f"\n{pair[0].upper()} + {pair[1].upper()}")
    print("Evaluated inputs:", total)
    print("Both correct:", c["both_correct"])
    print("Both failed:", c["both_failed"])
    print("Only one failed:", c["one_failed"])
    print("Agreed wrong:", c["agreed_wrong"])
    print(f"Joint failure rate: {overlap_rate:.2f}%")

    summary.append({
        "model1": pair[0],
        "model2": pair[1],
        "evaluated_inputs": total,
        "both_correct": c["both_correct"],
        "both_failed": c["both_failed"],
        "one_failed": c["one_failed"],
        "agreed_wrong": c["agreed_wrong"],
        "joint_failure_rate_pct": round(overlap_rate, 4)
    })

with open(OUTPUT, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=summary[0].keys())
    writer.writeheader()
    writer.writerows(summary)

print("\nAnalysis completed.")
print("Saved to:", OUTPUT)
