import subprocess
import sys

runners = [
    ("Ruff", "ruff_runner.py"),
    ("Safety", "safety_runner.py"),
    ("Vulture", "vulture_runner.py"),
    ("Bandit", "bandit_runner.py"),
    ("Pytest-Cov", "pycov_runner.py"),
]

base_path = sys.argv[1] if len(sys.argv) > 1 else "."

for name, script in runners:
    print(f"\n=== Running {name} ===")
    result = subprocess.run([sys.executable, script, base_path], cwd="./tests/runners")
    if result.returncode != 0:
        print(f"{name} checks failed.")
    else:
        print(f"{name} checks passed.")

