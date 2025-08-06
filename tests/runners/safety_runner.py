import subprocess
import sys

# Exclude Stockpiler directory from Safety scan/check
exclude_dirs = ["Stockpiler"]
exclude_args = []
for d in exclude_dirs:
    exclude_args.extend(["--exclude", d])

# Try safety login first
try:
    print("Logging in to Safety...")
    login_result = subprocess.run(["safety", "login"], check=False)
    if login_result.returncode != 0:
        print("Safety login failed or not required. Proceeding without login.")
except FileNotFoundError:
    print("Safety is not installed. Please install it with 'pip install safety'.")
    sys.exit(1)

# Try safety scan (preferred)
try:
    print("Running Safety scan...")
    scan_result = subprocess.run(["safety", "scan", "--full-report"] + exclude_args, check=False)
    if scan_result.returncode == 0:
        sys.exit(0)
    else:
        print("Safety scan failed or not available. Trying safety check...")
        # Fallback to safety check
        check_result = subprocess.run(["safety", "check", "--full-report"] + exclude_args, check=False)
        sys.exit(check_result.returncode)
except FileNotFoundError:
    print("Safety is not installed. Please install it with 'pip install safety'.")
    sys.exit(1)
