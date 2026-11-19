import csv
import json
import math
from pathlib import Path
from collections import Counter

# --------------------------------------------------
# STEP 1: Configuration
# --------------------------------------------------

DATASET = Path("dataset/ICPC_Eval_Dataset/ICPC_Eval_30.jsonl")

INPUT_RESULTS = Path("results/judged_results_preliminary.csv")
OUTPUT_RESULTS = Path("results/judged_results_float.csv")

# Problem-specific numerical tolerances
FLOAT_PROBLEMS = {
    4: 1e-9,
    11: 1e-4,
    14: 1e-6,
    25: 1e-9
}

MAX_OUTPUT_BYTES = 32 * 1024 * 1024

# --------------------------------------------------
# STEP 2: Load expected answers
# --------------------------------------------------

expected_answers = {}

with open(DATASET, "r", encoding="utf-8") as f:
    for line in f:
        problem = json.loads(line)
        pid = int(problem["id"])

        if pid in FLOAT_PROBLEMS:
            expected_answers[pid] = [
                case[1] for case in problem["test_cases"]
            ]

if set(expected_answers) != set(FLOAT_PROBLEMS):
    raise RuntimeError("Some floating-point problems are missing")

# --------------------------------------------------
# STEP 3: Numerical correctness checker
# --------------------------------------------------

def check_floating_output(output_file, expected_text, tolerance):

    path = Path(output_file)

    if not path.is_file():
        return "MISSING_OUTPUT"

    if path.stat().st_size > MAX_OUTPUT_BYTES:
        return "PENDING_LARGE_OUTPUT"

    actual_tokens = path.read_bytes().split()
    expected_tokens = expected_text.encode("utf-8").split()

    # Different numbers of answers means incorrect output.
    if len(actual_tokens) != len(expected_tokens):
        return "WRONG_ANSWER"

    try:
        for actual_token, expected_token in zip(
            actual_tokens, expected_tokens
        ):

            actual = float(actual_token)
            expected = float(expected_token)

            # Reject NaN and infinity.
            if not math.isfinite(actual):
                return "WRONG_ANSWER"

            if not math.isfinite(expected):
                raise ValueError("Invalid reference answer")

            difference = abs(actual - expected)

            absolute_ok = difference <= tolerance

            relative_ok = (
                expected != 0
                and difference / abs(expected) <= tolerance
            )

            if not (absolute_ok or relative_ok):
                return "WRONG_ANSWER"

    except (ValueError, OverflowError):
        return "WRONG_ANSWER"

    return "PASS"

# --------------------------------------------------
# STEP 4: Update preliminary verdicts
# --------------------------------------------------

with open(
    INPUT_RESULTS,
    newline="",
    encoding="utf-8"
) as f:
    rows = list(csv.DictReader(f))

counts = Counter()

for row in rows:

    pid = int(row["problem_id"])

    if pid not in FLOAT_PROBLEMS:
        continue

    # Preserve timeouts, runtime errors and compilation errors.
    if row["verdict"] != "PENDING_SPECIAL_JUDGE":
        continue

    test_id = int(row["test_id"])

    expected = expected_answers[pid][test_id]

    row["verdict"] = check_floating_output(
        row["stdout_file"],
        expected,
        FLOAT_PROBLEMS[pid]
    )

    counts[(pid, row["verdict"])] += 1

# --------------------------------------------------
# STEP 5: Save updated results
# --------------------------------------------------

with open(
    OUTPUT_RESULTS,
    "w",
    newline="",
    encoding="utf-8"
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=rows[0].keys()
    )

    writer.writeheader()
    writer.writerows(rows)

# --------------------------------------------------
# STEP 6: Display summary
# --------------------------------------------------

print("\n" + "=" * 55)
print("FLOATING-POINT CORRECTNESS RESULTS")
print("=" * 55)

for pid in FLOAT_PROBLEMS:

    print(f"\nProblem {pid}:")
    print("PASS:", counts[(pid, "PASS")])
    print("WRONG ANSWER:", counts[(pid, "WRONG_ANSWER")])
    print(
        "Other pending:",
        sum(
            count for (p, verdict), count in counts.items()
            if p == pid and verdict not in {"PASS", "WRONG_ANSWER"}
        )
    )

print("\nTotal records:", len(rows))
print("Updated results saved to:", OUTPUT_RESULTS)
print("\nStep 13 completed.")
