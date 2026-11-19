import csv
from pathlib import Path
from collections import defaultdict, Counter

RESULTS = Path("results")
MODELS = ["gpt", "gemini", "claude", "meta"]

EXCLUDED = {0, 10, 12, 15, 16, 19, 21}
UNASSESSED = {
    "PENDING_SPECIAL_JUDGE",
    "PENDING_LARGE_OUTPUT",
    "MISSING_OUTPUT"
}

# --------------------------------------------------
# 1. Individual LLM performance
# --------------------------------------------------

with open(
    RESULTS / "judged_results_float.csv",
    newline="", encoding="utf-8"
) as f:
    records = list(csv.DictReader(f))

individual = defaultdict(Counter)

for row in records:
    if int(row["problem_id"]) in EXCLUDED:
        continue

    verdict = row["verdict"]
    model = row["model"]

    if verdict in UNASSESSED:
        individual[model]["unassessed"] += 1
        continue

    individual[model]["total"] += 1

    if verdict == "PASS":
        individual[model]["correct"] += 1
    else:
        individual[model]["failed"] += 1

# --------------------------------------------------
# 2. Two-version voter performance
# --------------------------------------------------

with open(
    RESULTS / "final_pair_voting.csv",
    newline="", encoding="utf-8"
) as f:
    voting_records = list(csv.DictReader(f))

pairs = defaultdict(Counter)

for row in voting_records:
    pair = (row["model1"], row["model2"])
    outcome = row["outcome"]

    if outcome == "UNASSESSED":
        pairs[pair]["unassessed"] += 1
        continue

    pairs[pair]["total"] += 1
    pairs[pair][outcome] += 1

# --------------------------------------------------
# 3. Calculate rates
# --------------------------------------------------

def percentage(numerator, denominator):
    if denominator == 0:
        return 0.0
    return 100 * numerator / denominator

print("\n" + "=" * 65)
print("INDIVIDUAL LLM DEPENDABILITY")
print("=" * 65)

for model in MODELS:
    c = individual[model]
    total = c["total"]

    print(f"\n{model.upper()}")
    print("Evaluated inputs:", total)
    print("Correct answers:", c["correct"])
    print("Failures:", c["failed"])
    print("Unassessed:", c["unassessed"])
    print(
        f"Correct-answer rate: "
        f"{percentage(c['correct'], total):.2f}%"
    )
    print(
        f"Failure probability: "
        f"{percentage(c['failed'], total):.2f}%"
    )

print("\n" + "=" * 65)
print("TWO-VERSION VOTER DEPENDABILITY")
print("=" * 65)

summary_rows = []

for pair, c in sorted(pairs.items()):
    total = c["total"]

    correct = c["ACCEPTED_CORRECT"]
    wrong = c["ACCEPTED_WRONG"]
    rejected = c["REJECTED"]

    correct_rate = percentage(correct, total)
    wrong_rate = percentage(wrong, total)
    rejection_rate = percentage(rejected, total)
    failure_rate = percentage(wrong + rejected, total)

    print(f"\n{pair[0].upper()} + {pair[1].upper()}")
    print("Evaluated inputs:", total)
    print("Accepted correct:", correct)
    print("Accepted wrong:", wrong)
    print("Rejected:", rejected)
    print("Unassessed:", c["unassessed"])

    print(f"Correct-answer rate: {correct_rate:.2f}%")
    print(f"Incorrect-acceptance rate: {wrong_rate:.2f}%")
    print(f"Rejection rate: {rejection_rate:.2f}%")
    print(f"Failure probability: {failure_rate:.2f}%")

    summary_rows.append({
        "model1": pair[0],
        "model2": pair[1],
        "evaluated_inputs": total,
        "accepted_correct": correct,
        "accepted_wrong": wrong,
        "rejected": rejected,
        "unassessed": c["unassessed"],
        "correct_rate_pct": round(correct_rate, 4),
        "incorrect_acceptance_pct": round(wrong_rate, 4),
        "rejection_rate_pct": round(rejection_rate, 4),
        "failure_rate_pct": round(failure_rate, 4)
    })

# --------------------------------------------------
# 4. Save summary
# --------------------------------------------------

output = RESULTS / "dependability_summary.csv"

with open(output, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=summary_rows[0].keys()
    )
    writer.writeheader()
    writer.writerows(summary_rows)

print("\n" + "=" * 65)
print("Dependability analysis completed.")
print("Results saved to:", output)
