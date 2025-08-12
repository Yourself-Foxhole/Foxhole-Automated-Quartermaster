import sqlite3
import os
from typing import Any

DB_PATH = os.path.join(os.path.dirname(__file__), 'update61.db')

def connect_db(db_path=DB_PATH):
    """Connect to the static game data SQLite database."""
    conn = sqlite3.connect(db_path)
    return conn

def list_tables(conn):
    """List all tables in the database."""
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    return [t[0] for t in tables]

def read_table(conn, table_name, limit=10):
    """Read data from a table (default: first 10 rows)."""
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM {table_name} LIMIT ?", (limit,))
    cols = [desc[0] for desc in cursor.description]
    rows = cursor.fetchall()
    return cols, rows

def read_table_as_dicts(connection: object, table_name: object, limit: object = 10) \
        -> list[dict[Any, Any]]:
    """Read data from a table and return as a list of dictionaries (default: first 10 rows)."""
    cursor = connection.cursor()
    cursor.execute(f"SELECT * FROM {table_name} LIMIT ?", (limit,))
    cols: list[Any] = [desc[0] for desc in cursor.description]
    all_rows: object = cursor.fetchall()
    return [dict(zip(cols, cur_row)) for cur_row in all_rows]

if __name__ == "__main__":
    conn = connect_db()
    print("Connected to %s", DB_PATH)
    tables = list_tables(conn)
    print("Available tables:", tables)
    if tables:
        columns, rows = read_table(conn, tables[0])
        print(f"\nSample data from table '{tables[0]}':")
        print(columns)
        for row in rows:
            print(row)
        # Example usage of the new function
        dict_rows = read_table_as_dicts(conn, tables[0])
        print(f"\nSample data as dicts from table '{tables[0]}':")
        for d in dict_rows:
            print(d)
    conn.close()
