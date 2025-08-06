import subprocess
import sys

# Default test path is current directory or user-specified
path = sys.argv[1] if len(sys.argv) > 1 else "."

try:
    result = subprocess.run([
        "pytest", "--cov", path, "--cov-report=term-missing"
    ], check=False)
    sys.exit(result.returncode)
except FileNotFoundError:
    print("pytest or pytest-cov is not installed. Please install them with 'pip install pytest pytest-cov'.")
    sys.exit(1)

