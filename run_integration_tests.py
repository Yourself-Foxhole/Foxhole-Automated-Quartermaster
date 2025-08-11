import glob
import subprocess
import sys

import dotenv

INTEGRATION_TEST_PATTERN = "tests/**/integration_*.py"

def main():
    # Load environment variables from .env if present
    dotenv.load_dotenv()
    print("Running all integration tests...")
    # Use glob to expand the pattern to a list of files
    test_files = glob.glob(INTEGRATION_TEST_PATTERN, recursive=True)
    if not test_files:
        print("No integration tests found.")
        sys.exit(1)
    # noinspection SpellCheckingInspection
    # Doesn't accept max fail spelling
    result = subprocess.run([
        sys.executable, "-m", "pytest", *test_files,
        "--maxfail=5", "--disable-warnings",
    ], check=False)
    sys.exit(result.returncode)

if __name__ == "__main__":
    main()
