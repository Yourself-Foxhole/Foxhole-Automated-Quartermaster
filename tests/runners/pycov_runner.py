"""Runner script to execute pytest with coverage reporting on a specified or current directory.

This script attempts to run pytest with the pytest-cov plugin. If either is not installed,
it prompts the user to install the required packages.
"""

import subprocess
import sys

# The default test path is current directory or user-specified
path = sys.argv[1] if len(sys.argv) > 1 else "."

try:
    result = subprocess.run(["pytest", "--cov", path, "--cov-report=term-missing"], check=False)
    sys.exit(result.returncode)
except FileNotFoundError:
    print("pytest or pytest-cov is not installed. Please install them with 'pip install pytest pytest-cov'.")
    sys.exit(1)
