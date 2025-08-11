"""Module to run pylint on the main project directory, excluding virtual environments and egg-info.

This script can be executed directly. It accepts an optional base path argument (defaults to '../..'),
runs pylint with a specified configuration file, and exits with pylint's return code.
"""

import subprocess
import sys

if __name__ == "__main__":
    base_path = sys.argv[1] if len(sys.argv) > 1 else "../.."
    # Run pylint on the main project directory, excluding virtual environments and egg-info
    # noinspection PyArgumentEqualDefault
    # conflicting lint errors, better to be explicit in this case
    result = subprocess.run([
        sys.executable, "-m", "pylint", base_path,
        "--rcfile=../../.pylintrc",
        "--exit-zero",
    ], check=False)
    sys.exit(result.returncode)
