import subprocess
import sys

path = sys.argv[1] if len(sys.argv) > 1 else "."

try:
    result = subprocess.run(["bandit", "-r", path], check=False)
    sys.exit(result.returncode)
except FileNotFoundError:
    print("Bandit is not installed. Please install it with 'pip install bandit'.")
    sys.exit(1)

