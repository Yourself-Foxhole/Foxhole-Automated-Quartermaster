# Dependencies

This project relies on several Python packages and external tools. Below is a list of the main dependencies as specified in `requirements.txt`.

## Python Packages

- **dissnake**: Discord API wrapper for building bots.
- **peewee**: Lightweight ORM for database interactions.
- **pytest**: Testing framework for Python.
- **pytest-asyncio**: Async support for pytest.
- **pytest-cov**: Coverage reporting for pytest.
- **pytest-func-cov**: Function coverage reporting for pytest.
- **pytest-mock**: Mocking plugin for pytest.
- **python-dotenv**: Loads environment variables from `.env` files.
- **loguru**: Logging library for Python.
- **apscheduler**: Advanced Python scheduler for running jobs.
- **networkx**: Library for graph-based computations.
- **mypy**: Static type checker for Python.
- **types-python-dateutil**: Type stubs for `python-dateutil`.
- **sqlalchemy-stubs**: Type stubs for SQLAlchemy.
- **pydantic**: Data validation and settings management using Python type annotations.

## External Dependencies

- **SQLite**: Used as the database backend.

## Notes

- All Python dependencies are listed in `requirements.txt`.
- Install them with:

  ```sh
  pip install -r requirements.txt
  ```

- Some features may require additional system libraries (e.g., SQLite, Tesseract for OCR if used elsewhere).
