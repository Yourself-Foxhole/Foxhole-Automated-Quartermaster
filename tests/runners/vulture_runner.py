import subprocess
import sys

# Default path to check is the parent directory or user-specified
# This allows running vulture on the main project directory by default
path = sys.argv[1] if len(sys.argv) > 1 else "../../"

try:
    result = subprocess.run(["vulture", path], check=False)
    sys.exit(result.returncode)
except FileNotFoundError:
    print("Vulture is not installed. Please install it with 'pip install vulture'.")
    sys.exit(1)
