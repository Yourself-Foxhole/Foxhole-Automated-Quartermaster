#!/usr/bin/env python3
"""
Test runner script for the Foxhole Logistics Bot.
"""
import os
import sys
import pytest


def main():
    """Run the test suite."""
    # Add the project root to PYTHONPATH
    project_root = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, project_root)

    # Default arguments
    args = [
        "--verbose",
        "--cov=src",
        "--cov-report=term-missing",
        "--cov-report=html",
        "tests"
    ]

    # Add any additional arguments passed to the script
    args.extend(sys.argv[1:])

    # Run pytest
    sys.exit(pytest.main(args))


if __name__ == "__main__":
    main() 