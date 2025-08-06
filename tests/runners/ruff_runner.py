import subprocess
import sys

path = sys.argv[1] if len(sys.argv) > 1 else "."

# Run Ruff linter
try:
    print("Running Ruff linter...")
    lint_result = subprocess.run(["ruff", path], check=False)
    if lint_result.returncode != 0:
        print("Ruff linting issues found.")
    else:
        print("Ruff linting passed.")
except FileNotFoundError:
    print("Ruff is not installed. Please install it with 'pip install ruff'.")
    sys.exit(1)

# Run Ruff formatter
try:
    print("Running Ruff formatter...")
    fmt_result = subprocess.run(["ruff", "format", path], check=False)
    if fmt_result.returncode != 0:
        print("Ruff formatting issues found.")
    else:
        print("Ruff formatting passed.")
except FileNotFoundError:
    print("Ruff is not installed. Please install it with 'pip install ruff'.")
    sys.exit(1)

# Exit with nonzero if either failed
if lint_result.returncode != 0 or fmt_result.returncode != 0:
    sys.exit(1)
sys.exit(0)
