"""Module to run Bandit security analysis on a specified directory, excluding certain folders.

Usage:
    python bandit_runner.py [path]

If no path is provided, the current directory is scanned.
Excludes the 'Stockpiler' and '.venv' directories by default.
Requires Bandit to be installed (`pip install bandit`).
"""
import subprocess
import sys
from pathlib import Path

path = sys.argv[1] if len(sys.argv) > 1 else "."

p = Path(path).resolve()
if not p.is_dir():
    print(f"Error: '{p}' is not a valid directory.")
    sys.exit(2)

# Exclude Stockpiler directory
exclude_dirs = [
    "Stockpiler",
    ".venv",
]
exclude_args = []
for d in exclude_dirs:
    exclude_args.extend(["--exclude", d])

try:
    # noinspection PyArgumentEqualDefault
    result = subprocess.run(["bandit", "-r", str(p), *exclude_args], check=False)
    sys.exit(result.returncode)
except FileNotFoundError:
    print("Bandit is not installed. Please install it with 'pip install bandit'.")
    sys.exit(1)
