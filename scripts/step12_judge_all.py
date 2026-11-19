import csv
import json
from pathlib import Path
from collections import Counter

# --------------------------------------------------
# STEP 1: Configuration
# --------------------------------------------------

DATASET = Path(
    "dataset/ICPC_Eval_Dataset/ICPC_Eval_30.jsonl"
)

RESULTS = Path("results")

# Problems requiring special correctness checking
SPECIAL_PROBLEMS = {
    0,   # Arrow a Row: alternative painting operations
    4,   # Double 11: floating-point tolerance
    10,  # Recover Statistics: multiple valid datasets
    11,  # Two Convex Holes: floating-point tolerance
    12,  # Hitoshizuku: multiple valid groupings
    14,  # Keystone Correction: floating-point tolerance
    15,  # Corrupted Scoreboard Log: reconstruction
    16,  # Boolean Function Reconstruction: expressions
    19,  # Color-Balanced Tree: multiple valid colorings
    21,  # Exploration Boundary: multiple valid weights
    25,  # Catch the Star: floating-point tolerance
}

MODELS = ["gpt", "gemini", "claude", "meta"]

MAX_OUTPUT_BYTES = 32 * 1024 * 1024

all_results = []
summary = Counter()

# --------------------------------------------------
# STEP 2: Check outputs
# --------------------------------------------------

def check_output(stdout_path, expected_output):

    path = Path(stdout_path)

    if not path.is_file():
        return "MISSING_OUTPUT"

    if path.stat().st_size > MAX_OUTPUT_BYTES:
        return "PENDING_LARGE_OUTPUT"

    # Compare whitespace-separated tokens.
    # This handles harmless differences in spacing.
    actual_tokens = path.read_bytes().split()
    expected_tokens = expected_output.encode("utf-8").split()

    if actual_tokens == expected_tokens:
        return "PASS"

    return "WRONG_ANSWER"

# --------------------------------------------------
# STEP 3: Process each problem
# --------------------------------------------------

with open(DATASET, "r", encoding="utf-8") as dataset:

    for line in dataset:

        problem = json.loads(line)

        problem_id = int(problem["id"])
        title = problem["title"]
        test_cases = problem["test_cases"]

        execution_file = (
            RESULTS / f"raw_execution_id{problem_id}.csv"
        )

        with open(
            execution_file,
            newline="",
            encoding="utf-8"
        ) as f:
            execution_records = list(csv.DictReader(f))

        counts = Counter()

        for record in execution_records:

            model = record["model"]
            test_id = int(record["test_id"])
            execution_status = record["status"]

            if test_id >= len(test_cases):
                raise ValueError("Invalid test ID")

            if execution_status != "EXIT_0":

                # Preserve compilation and execution failures
                verdict = execution_status

            elif problem_id in SPECIAL_PROBLEMS:

                # Do not incorrectly judge alternative outputs
                verdict = "PENDING_SPECIAL_JUDGE"

            else:

                expected_output = test_cases[test_id][1]

                verdict = check_output(
                    record["stdout_file"],
                    expected_output
                )

            counts[verdict] += 1
            summary[(model, verdict)] += 1

            all_results.append({
                "problem_id": problem_id,
                "title": title,
                "test_id": test_id,
                "model": model,
                "execution_status": execution_status,
                "verdict": verdict,
                "stdout_file": record["stdout_file"],
                "wall_time_ms": record["wall_time_ms"]
            })

        print(
            f"Problem {problem_id:02d}: "
            f"{title[:28]:28} | "
            f"{dict(counts)}"
        )

# --------------------------------------------------
# STEP 4: Save consolidated results
# --------------------------------------------------

output_file = RESULTS / "judged_results_preliminary.csv"

with open(
    output_file,
    "w",
    newline="",
    encoding="utf-8"
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=all_results[0].keys()
    )

    writer.writeheader()
    writer.writerows(all_results)

# --------------------------------------------------
# STEP 5: Print summary
# --------------------------------------------------

print("\n" + "=" * 55)
print("PRELIMINARY CORRECTNESS SUMMARY")
print("=" * 55)

for model in MODELS:

    print(f"\nMODEL: {model.upper()}")

    for status in [
        "PASS",
        "WRONG_ANSWER",
        "TIMEOUT",
        "RUNTIME_ERROR",
        "COMPILATION_ERROR",
        "PENDING_SPECIAL_JUDGE",
        "PENDING_LARGE_OUTPUT",
        "MISSING_OUTPUT"
    ]:

        print(
            f"{status}:",
            summary[(model, status)]
        )

print("\n" + "=" * 55)
print("Total records:", len(all_results))
print("Special-checking problem IDs:", sorted(SPECIAL_PROBLEMS))
print("Results saved to:", output_file)
print("Step 12 completed.")
