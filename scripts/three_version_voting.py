import csv
import math
from pathlib import Path
from itertools import combinations
from collections import Counter

# ==================================================
# 1. CONFIGURATION
# ==================================================

MODELS = ["gpt", "gemini", "claude", "meta"]

RESULTS_DIR = Path("results")
INPUT_FILE = RESULTS_DIR / "judged_results_float.csv"

# These problems need additional semantic checkers.
EXCLUDED = {0, 10, 12, 15, 16, 19, 21}

FLOAT_TOLERANCES = {
    4: 1e-9,
    11: 1e-4,
    14: 1e-6,
    25: 1e-9
}

MAX_OUTPUT_BYTES = 32 * 1024 * 1024

# ==================================================
# 2. LOAD EXECUTION AND CORRECTNESS RECORDS
# ==================================================

with open(INPUT_FILE, newline="", encoding="utf-8") as f:
    rows = list(csv.DictReader(f))

records = {
    (
        int(r["problem_id"]),
        int(r["test_id"]),
        r["model"]
    ): r
    for r in rows
}

test_cases = sorted({
    (int(r["problem_id"]), int(r["test_id"]))
    for r in rows
    if int(r["problem_id"]) not in EXCLUDED
})

triples = list(combinations(MODELS, 3))

print("Problems:", len(set(p for p, t in test_cases)))
print("Test cases:", len(test_cases))
print("Three-version combinations:", len(triples))

# ==================================================
# 3. READ A PROGRAM'S OUTPUT
# ==================================================

def read_output(record):

    if record["execution_status"] != "EXIT_0":
        return None

    filename = record["stdout_file"]

    if not filename:
        return None

    path = Path(filename)

    if not path.is_file():
        return None

    if path.stat().st_size > MAX_OUTPUT_BYTES:
        return None

    return path.read_bytes().split()

# ==================================================
# 4. COMPARE TWO OUTPUTS
# ==================================================

def agree(pid, a, b):

    if a is None or b is None:
        return False

    if pid not in FLOAT_TOLERANCES:
        return a == b

    if len(a) != len(b):
        return False

    tolerance = FLOAT_TOLERANCES[pid]

    try:
        for x, y in zip(a, b):

            x = float(x)
            y = float(y)

            if not math.isfinite(x) or not math.isfinite(y):
                return False

            if not math.isclose(
                x, y,
                rel_tol=tolerance,
                abs_tol=tolerance
            ):
                return False

        return True

    except (ValueError, OverflowError):
        return False

# ==================================================
# 5. THREE-VERSION MAJORITY VOTER
# ==================================================

def majority_voter(pid, model_outputs):

    # The voter uses only program outputs.
    # It does not know the correct answer.

    for i, j in combinations(range(3), 2):

        if agree(pid, model_outputs[i], model_outputs[j]):

            # Return the index of the selected version.
            return i

    # No two outputs agree.
    return None

# ==================================================
# 6. EVALUATE ALL THREE-VERSION COMBINATIONS
# ==================================================

details = []
summary = {}

UNASSESSED = {
    "PENDING_SPECIAL_JUDGE",
    "PENDING_LARGE_OUTPUT",
    "MISSING_OUTPUT"
}

for triple in triples:

    counts = Counter()

    for pid, tid in test_cases:

        case_records = [
            records[(pid, tid, model)]
            for model in triple
        ]

        outputs = [
            read_output(r)
            for r in case_records
        ]

        # First perform voting, without ground truth.
        winner = majority_voter(pid, outputs)

        # Only afterward evaluate correctness.
        if winner is None:
            outcome = "REJECTED"

        else:
            verdict = case_records[winner]["verdict"]

            if verdict == "PASS":
                outcome = "ACCEPTED_CORRECT"

            elif verdict in UNASSESSED:
                outcome = "UNASSESSED"

            else:
                outcome = "ACCEPTED_WRONG"

        counts[outcome] += 1

        details.append({
            "problem_id": pid,
            "test_id": tid,
            "model1": triple[0],
            "model2": triple[1],
            "model3": triple[2],
            "selected_model": (
                triple[winner] if winner is not None else ""
            ),
            "outcome": outcome
        })

    summary[triple] = counts

# ==================================================
# 7. DISPLAY RESULTS
# ==================================================

print("\n" + "=" * 55)
print("THREE-VERSION MAJORITY VOTING")
print("=" * 55)

for triple, counts in summary.items():

    print("\nCOMBINATION:", " + ".join(m.upper() for m in triple))

    print("Accepted correct:", counts["ACCEPTED_CORRECT"])
    print("Accepted wrong:", counts["ACCEPTED_WRONG"])
    print("Rejected:", counts["REJECTED"])
    print("Unassessed:", counts["UNASSESSED"])

# ==================================================
# 8. SAVE RESULTS
# ==================================================

output_file = RESULTS_DIR / "three_version_voting.csv"

with open(output_file, "w", newline="", encoding="utf-8") as f:

    writer = csv.DictWriter(
        f,
        fieldnames=details[0].keys()
    )

    writer.writeheader()
    writer.writerows(details)

print("\n" + "=" * 55)
print("Three-version voting completed.")
print("Total voting decisions:", len(details))
print("Saved to:", output_file)
