import csv
import math
from pathlib import Path
from itertools import combinations
from collections import Counter, defaultdict

# ==================================================
# 1. CONFIGURATION
# ==================================================

MODELS = ["gpt", "gemini", "claude", "meta"]

INPUT_FILE = Path("results/judged_results_float.csv")
RESULTS_DIR = Path("results")

# Constructive problems requiring additional validators
PENDING_PROBLEMS = {0, 10, 12, 15, 16, 19, 21}

# Floating-point problems and their tolerances
FLOAT_TOLERANCES = {
    4: 1e-9,
    11: 1e-4,
    14: 1e-6,
    25: 1e-9
}

MAX_BYTES = 32 * 1024 * 1024

# ==================================================
# 2. LOAD EXISTING JUDGED RESULTS
# ==================================================

with open(INPUT_FILE, newline="", encoding="utf-8") as f:
    records = list(csv.DictReader(f))

results = {}

for record in records:
    pid = int(record["problem_id"])
    tid = int(record["test_id"])
    model = record["model"]

    results[(pid, tid, model)] = record

test_keys = sorted({
    (int(r["problem_id"]), int(r["test_id"]))
    for r in records
    if int(r["problem_id"]) not in PENDING_PROBLEMS
})

print("Total records available:", len(records))
print("Problems included:", len(set(p for p, t in test_keys)))
print("Test inputs included:", len(test_keys))

# ==================================================
# 3. READ ACTUAL PROGRAM OUTPUT
# ==================================================

def read_output(record):

    if record["execution_status"] != "EXIT_0":
        return None

    path_text = record["stdout_file"]

    if not path_text:
        return None

    path = Path(path_text)

    if not path.is_file():
        return None

    if path.stat().st_size > MAX_BYTES:
        return None

    return path.read_bytes().split()

# ==================================================
# 4. DEFINE OUTPUT AGREEMENT
# ==================================================

def outputs_agree(pid, output1, output2):

    if output1 is None or output2 is None:
        return False

    # Numeric problems: compare with tolerance
    if pid in FLOAT_TOLERANCES:

        if len(output1) != len(output2):
            return False

        tolerance = FLOAT_TOLERANCES[pid]

        try:
            for a, b in zip(output1, output2):

                x = float(a)
                y = float(b)

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

    # Fixed-answer problems: ignore whitespace differences
    return output1 == output2

# ==================================================
# 5. INDIVIDUAL LLM PERFORMANCE
# ==================================================

print("\n" + "=" * 55)
print("INDIVIDUAL LLM RESULTS")
print("=" * 55)

for model in MODELS:

    counts = Counter(
        results[(pid, tid, model)]["verdict"]
        for pid, tid in test_keys
    )

    print(f"\n{model.upper()}")
    print("Correct:", counts["PASS"])
    print("Wrong answer:", counts["WRONG_ANSWER"])
    print("Timeout:", counts["TIMEOUT"])
    print("Runtime error:", counts["RUNTIME_ERROR"])
    print("Compilation error:", counts["COMPILATION_ERROR"])
    print(
        "Unassessed:",
        sum(v for k, v in counts.items()
            if k.startswith("PENDING") or k == "MISSING_OUTPUT")
    )

# ==================================================
# 6. TWO-VERSION VOTING + FAILURE OVERLAP
# ==================================================

pairs = list(combinations(MODELS, 2))

pair_counts = {pair: Counter() for pair in pairs}
detailed_results = []

UNASSESSED = {
    "PENDING_SPECIAL_JUDGE",
    "PENDING_LARGE_OUTPUT",
    "MISSING_OUTPUT"
}

for pid, tid in test_keys:

    # Read each model output once per test case
    case_records = {
        model: results[(pid, tid, model)]
        for model in MODELS
    }

    outputs = {
        model: read_output(case_records[model])
        for model in MODELS
    }

    for model1, model2 in pairs:

        r1 = case_records[model1]
        r2 = case_records[model2]

        counts = pair_counts[(model1, model2)]
        counts["TOTAL"] += 1

        v1 = r1["verdict"]
        v2 = r2["verdict"]

        # Do not invent correctness for unassessed cases
        if v1 in UNASSESSED or v2 in UNASSESSED:
            outcome = "UNASSESSED"
            counts["UNASSESSED"] += 1

        else:

            failed1 = v1 != "PASS"
            failed2 = v2 != "PASS"

            if failed1 and failed2:
                counts["BOTH_FAILED"] += 1

            # Voter examines outputs, not correct answers
            agreement = outputs_agree(
                pid,
                outputs[model1],
                outputs[model2]
            )

            if not agreement:
                outcome = "REJECTED"

            elif v1 == "PASS":
                # The voter returns model1's agreed output.
                # Its correctness is evaluated after voting.
                outcome = "ACCEPTED_CORRECT"

            else:
                outcome = "ACCEPTED_WRONG"

            counts[outcome] += 1

        detailed_results.append({
            "problem_id": pid,
            "test_id": tid,
            "model1": model1,
            "model2": model2,
            "verdict1": v1,
            "verdict2": v2,
            "outcome": outcome
        })

# ==================================================
# 7. DISPLAY RESULTS
# ==================================================

print("\n" + "=" * 55)
print("TWO-VERSION AGREEMENT VOTING")
print("=" * 55)

for pair in pairs:

    counts = pair_counts[pair]

    print(f"\nPAIR: {pair[0].upper()} + {pair[1].upper()}")

    print("Total inputs:", counts["TOTAL"])
    print("Both failed:", counts["BOTH_FAILED"])
    print("Accepted correct:", counts["ACCEPTED_CORRECT"])
    print("Accepted wrong:", counts["ACCEPTED_WRONG"])
    print("Rejected:", counts["REJECTED"])
    print("Unassessed:", counts["UNASSESSED"])

# ==================================================
# 8. SAVE RESULTS
# ==================================================

output_file = RESULTS_DIR / "final_pair_voting.csv"

with open(
    output_file,
    "w",
    newline="",
    encoding="utf-8"
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=detailed_results[0].keys()
    )

    writer.writeheader()
    writer.writerows(detailed_results)

print("\n" + "=" * 55)
print("Analysis completed.")
print("Voting decisions:", len(detailed_results))
print("Saved to:", output_file)
