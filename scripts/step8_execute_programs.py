import argparse
import csv
import json
import os
import resource
import signal
import subprocess
import tempfile
import time
from collections import Counter
from pathlib import Path

# --------------------------------------------------
# STEP 1: Define our project folders
# --------------------------------------------------

DATASET = Path("dataset/ICPC_Eval_Dataset/ICPC_Eval_30.jsonl")
BIN_FOLDER = Path("outputs/bin")
OUTPUT_FOLDER = Path("outputs/raw")
RESULTS_FOLDER = Path("results")

MODELS = ["gpt", "gemini", "claude", "meta"]

OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)
RESULTS_FOLDER.mkdir(parents=True, exist_ok=True)

# --------------------------------------------------
# STEP 2: Read compilation results
# --------------------------------------------------

compilation_status = {}

with open("results/compilation_results.csv",
          newline="", encoding="utf-8") as f:

    for row in csv.DictReader(f):
        key = (int(row["problem_id"]), row["model"])
        compilation_status[key] = row["status"]

# --------------------------------------------------
# STEP 3: Set the memory limit
# --------------------------------------------------

def apply_memory_limit(memory_mb):
    limit_bytes = int(memory_mb) * 1024 * 1024

    resource.setrlimit(
        resource.RLIMIT_AS,
        (limit_bytes, limit_bytes)
    )

# --------------------------------------------------
# STEP 4: Execute one program on one test input
# --------------------------------------------------

def execute_program(executable, test_input,
                    time_limit_ms, memory_limit_mb,
                    stdout_path, stderr_path):

    # Use a temporary input file so large inputs
    # do not have to be passed through memory pipes.

    with tempfile.TemporaryFile(mode="w+b") as input_file:

        input_file.write(test_input.encode("utf-8"))
        input_file.seek(0)

        with open(stdout_path, "wb") as stdout_file, \
             open(stderr_path, "wb") as stderr_file:

            start = time.perf_counter()

            try:
                process = subprocess.Popen(
                    [str(executable.resolve())],
                    stdin=input_file,
                    stdout=stdout_file,
                    stderr=stderr_file,
                    preexec_fn=lambda: apply_memory_limit(
                        memory_limit_mb
                    ),
                    start_new_session=True
                )

                try:
                    return_code = process.wait(
                        timeout=time_limit_ms / 1000
                    )

                    if return_code == 0:
                        status = "EXIT_0"
                    else:
                        status = "RUNTIME_ERROR"

                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
                    return_code = None
                    status = "TIMEOUT"

            except OSError:
                return_code = None
                status = "EXECUTION_ERROR"

            elapsed_ms = (
                time.perf_counter() - start
            ) * 1000

    return {
        "status": status,
        "return_code": return_code,
        "wall_time_ms": round(elapsed_ms, 2)
    }

# --------------------------------------------------
# STEP 5: Evaluate all models for one problem
# --------------------------------------------------

def evaluate_problem(problem):

    problem_id = int(problem["id"])
    title = problem["title"]

    time_limit_ms = int(problem["time_limit_ms"])
    memory_limit_mb = int(problem["memory_limit_mb"])

    test_cases = problem["test_cases"]

    print("\n" + "=" * 55)
    print(f"PROBLEM {problem_id}: {title}")
    print("Test cases:", len(test_cases))
    print("Time limit:", time_limit_ms, "ms")
    print("Memory limit:", memory_limit_mb, "MB")

    problem_folder = OUTPUT_FOLDER / f"id{problem_id}"
    problem_folder.mkdir(parents=True, exist_ok=True)

    results = []

    for model in MODELS:

        print(f"\nMODEL: {model.upper()}")

        executable = BIN_FOLDER / f"{model}_id{problem_id}"

        compiled = (
            compilation_status.get((problem_id, model))
            == "COMPILED"
        )

        counts = Counter()

        for test_id, (test_input, expected_output) in enumerate(
            test_cases
        ):

            stdout_path = (
                problem_folder / f"{model}_test{test_id:02d}.out"
            )

            stderr_path = (
                problem_folder / f"{model}_test{test_id:02d}.err"
            )

            if not compiled:
                execution = {
                    "status": "COMPILATION_ERROR",
                    "return_code": None,
                    "wall_time_ms": None
                }

                stdout_file = ""
                stderr_file = ""

            elif not executable.exists():
                execution = {
                    "status": "MISSING_EXECUTABLE",
                    "return_code": None,
                    "wall_time_ms": None
                }

                stdout_file = ""
                stderr_file = ""

            else:
                execution = execute_program(
                    executable,
                    test_input,
                    time_limit_ms,
                    memory_limit_mb,
                    stdout_path,
                    stderr_path
                )

                stdout_file = str(stdout_path)
                stderr_file = str(stderr_path)

            status = execution["status"]
            counts[status] += 1

            results.append({
                "problem_id": problem_id,
                "test_id": test_id,
                "model": model,
                "status": status,
                "return_code": execution["return_code"],
                "wall_time_ms": execution["wall_time_ms"],
                "stdout_file": stdout_file,
                "stderr_file": stderr_file
            })

            print(f"Test {test_id + 1:02d}: {status}")

        print("SUMMARY:", dict(counts))

    # Save execution results for this problem

    result_path = (
        RESULTS_FOLDER / f"raw_execution_id{problem_id}.csv"
    )

    fields = [
        "problem_id",
        "test_id",
        "model",
        "status",
        "return_code",
        "wall_time_ms",
        "stdout_file",
        "stderr_file"
    ]

    with open(result_path, "w", newline="",
              encoding="utf-8") as f:

        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(results)

    print("\nSaved results to:", result_path)
    print("Total execution records:", len(results))

# --------------------------------------------------
# STEP 6: Choose which problems to execute
# --------------------------------------------------

parser = argparse.ArgumentParser()

group = parser.add_mutually_exclusive_group(required=True)

group.add_argument(
    "--problem",
    type=int,
    help="Execute one problem, for example --problem 9"
)

group.add_argument(
    "--all",
    action="store_true",
    help="Execute all 30 problems"
)

args = parser.parse_args()

found = False

with open(DATASET, "r", encoding="utf-8") as f:

    for line in f:

        problem = json.loads(line)
        problem_id = int(problem["id"])

        if args.all or problem_id == args.problem:

            evaluate_problem(problem)
            found = True

            if not args.all:
                break

if not found:
    print("ERROR: Requested problem was not found.")
else:
    print("\nExecution stage completed.")
