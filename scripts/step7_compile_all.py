import csv
import subprocess
import hashlib
from pathlib import Path
from collections import Counter

# ------------------------------------------
# STEP 1: Define folders
# ------------------------------------------

solutions_folder = Path("solutions")
binary_folder = Path("outputs/bin")
results_folder = Path("results")
errors_folder = results_folder / "compile_errors"

binary_folder.mkdir(parents=True, exist_ok=True)
results_folder.mkdir(parents=True, exist_ok=True)
errors_folder.mkdir(parents=True, exist_ok=True)

models = ["gpt", "gemini", "claude", "meta"]

# ------------------------------------------
# STEP 2: Read our 30 problem IDs
# ------------------------------------------

with open("results/problem_metadata.csv", newline="", encoding="utf-8") as f:
    problems = list(csv.DictReader(f))

print("Total problems:", len(problems))
print("Models:", ", ".join(models))
print("Expected programs:", len(problems) * len(models))

compiler = subprocess.run(
    ["g++", "--version"],
    capture_output=True,
    text=True,
    check=True
).stdout.splitlines()[0]

print("Compiler:", compiler)

# ------------------------------------------
# STEP 3: Compile every solution
# ------------------------------------------

output_file = results_folder / "compilation_results.csv"

fieldnames = [
    "problem_id",
    "model",
    "source_file",
    "source_sha256",
    "status",
    "compiler",
    "error_file"
]

counts = Counter()

with open(output_file, "w", newline="", encoding="utf-8") as f:

    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()

    for problem in problems:

        problem_id = int(problem["problem_id"])

        for model in models:

            source = solutions_folder / model / f"id{problem_id}.cpp"
            executable = binary_folder / f"{model}_id{problem_id}"
            error_file = errors_folder / f"{model}_id{problem_id}.txt"

            # Remove any older executable
            if executable.exists():
                executable.unlink()

            if error_file.exists():
                error_file.unlink()

            print(
                f"Compiling Problem {problem_id:02d} "
                f"| {model.upper()}",
                end=" ... ",
                flush=True
            )

            if not source.exists():
                status = "MISSING_SOURCE"
                source_hash = ""
                error_text = "Source file not found."

            else:
                source_hash = hashlib.sha256(
                    source.read_bytes()
                ).hexdigest()

                try:
                    result = subprocess.run(
                        [
                            "g++",
                            "-std=c++23",
                            "-O2",
                            str(source),
                            "-o",
                            str(executable)
                        ],
                        capture_output=True,
                        text=True,
                        timeout=90
                    )

                    if result.returncode == 0:
                        status = "COMPILED"
                        error_text = ""
                    else:
                        status = "COMPILATION_ERROR"
                        error_text = result.stderr

                except subprocess.TimeoutExpired:
                    status = "COMPILATION_TIMEOUT"
                    error_text = "Compilation exceeded 90 seconds."

            # Save compiler errors for later analysis
            if status != "COMPILED":
                error_file.write_text(
                    error_text,
                    encoding="utf-8"
                )
                error_path = str(error_file)
            else:
                error_path = ""

            counts[status] += 1

            writer.writerow({
                "problem_id": problem_id,
                "model": model,
                "source_file": str(source),
                "source_sha256": source_hash,
                "status": status,
                "compiler": compiler,
                "error_file": error_path
            })

            f.flush()

            print(status)

# ------------------------------------------
# STEP 4: Display summary
# ------------------------------------------

print("\n" + "=" * 50)
print("COMPILATION SUMMARY")
print("=" * 50)

print("Total programs:", sum(counts.values()))

for status, count in sorted(counts.items()):
    print(f"{status}: {count}")

print("\nResults saved to:", output_file)
print("Executables saved to:", binary_folder)
print("Compiler errors saved to:", errors_folder)
print("\nStep 7 completed.")
