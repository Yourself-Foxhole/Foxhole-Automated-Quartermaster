import subprocess
import sys

# The default path to check is current directory
path = sys.argv[1] if len(sys.argv) > 1 else "."

try:
    result = subprocess.run(["ruff", path], check=False)
    sys.exit(result.returncode)
except FileNotFoundError:
    print("Ruff is not installed. Please install it with 'pip install ruff'.")
    sys.exit(1)

