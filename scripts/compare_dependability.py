import csv
from pathlib import Path
from collections import Counter

RESULTS = Path("results")
EXCLUDED = {0, 10, 12, 15, 16, 19, 21}

summary = []

def load_csv(filename):
    with open(RESULTS / filename, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def add_result(system_type, name, counts):
    total = sum(counts.values())
    if total != 460:
        raise ValueError(f"{name}: Expected 460 records, found {total}")

    correct = counts["CORRECT"]
    wrong = counts["WRONG"]
    unavailable = counts["UNAVAILABLE"]

    summary.append({
        "system_type": system_type,
        "system": name,
        "total_inputs": total,
        "correct": correct,
        "wrong_accepted": wrong,
        "rejected_or_unavailable": unavailable,
        "correct_rate_pct": round(100 * correct / total, 2),
        "wrong_acceptance_pct": round(100 * wrong / total, 2),
        "rejection_or_unavailable_pct": round(100 * unavailable / total, 2)
    })

# 1. Individual LLMs
individual = {}

for row in load_csv("judged_results_float.csv"):
    if int(row["problem_id"]) in EXCLUDED:
        continue

    model = row["model"]
    individual.setdefault(model, Counter())

    verdict = row["verdict"]

    if verdict == "PASS":
        individual[model]["CORRECT"] += 1
    elif verdict == "WRONG_ANSWER":
        individual[model]["WRONG"] += 1
    elif verdict.startswith("PENDING") or verdict == "MISSING_OUTPUT":
        raise ValueError(f"Unassessed verdict: {model}, {verdict}")
    else:
        individual[model]["UNAVAILABLE"] += 1

for model, counts in sorted(individual.items()):
    add_result("Individual", model.upper(), counts)

# 2. Two-version voting
for filename, system_type, fields in [
    ("final_pair_voting.csv", "Two-version", ["model1", "model2"]),
    ("three_version_voting.csv", "Three-version", ["model1", "model2", "model3"])
]:
    groups = {}

    for row in load_csv(filename):
        name = " + ".join(row[field].upper() for field in fields)
        groups.setdefault(name, Counter())

        outcome = row["outcome"]

        if outcome == "ACCEPTED_CORRECT":
            groups[name]["CORRECT"] += 1
        elif outcome == "ACCEPTED_WRONG":
            groups[name]["WRONG"] += 1
        elif outcome == "REJECTED":
            groups[name]["UNAVAILABLE"] += 1
        else:
            raise ValueError(f"Unexpected outcome: {outcome}")

    for name, counts in sorted(groups.items()):
        add_result(system_type, name, counts)

# 3. Save comparison
output = RESULTS / "comparison_all_systems.csv"

with open(output, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=summary[0].keys())
    writer.writeheader()
    writer.writerows(summary)

# 4. Display results
print("\nFINAL DEPENDABILITY COMPARISON")
print("=" * 90)

print(
    f"{'System':35} {'Correct %':>12} "
    f"{'Wrong %':>12} {'Rejected/Unavailable %':>23}"
)

for row in summary:
    print(
        f"{row['system']:35} "
        f"{row['correct_rate_pct']:>11.2f}% "
        f"{row['wrong_acceptance_pct']:>11.2f}% "
        f"{row['rejection_or_unavailable_pct']:>22.2f}%"
    )

print("\nSystems compared:", len(summary))
print("Test inputs per system: 460")
print("Saved to:", output)
