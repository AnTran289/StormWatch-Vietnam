"""
Read the init.sql file and execute it against PostgreSQL database.

This creates schemas, tables, constraints and indexes.
"""
from pathlib import Path
from src.database.connection import get_engine

PROJECT_ROOT = Path(__file__).resolve().parents[2] # Get the parent directory of the current file (create_tables.py) and then its parent (project root)
SQL_FILE_PATH = PROJECT_ROOT / "docker/postgres/init.sql" # Path to the init.sql file in the docker/postgres directory

# Read the SQL schema file into a Python string
def load_sql_file() -> str:
    if not SQL_FILE_PATH.exists():
        raise FileNotFoundError(f"SQL file not found: {SQL_FILE_PATH}")
    return SQL_FILE_PATH.read_text(encoding="utf-8") # Read the contents of the SQL file and return it as a string

# Execute the SQL schema against postgresql
def create_database_objects()->None:
    engine = get_engine() # Get the database engine
    sql = load_sql_file() # Load the SQL schema from the file
    raw_connection = engine.raw_connection() # Get a raw connection from the engine
    try:
        with raw_connection.cursor() as cursor:
            cursor.execute(sql) # Execute the SQL schema
        raw_connection.commit() # Commit the transaction

    except Exception as e:
        raw_connection.rollback() # Rollback the transaction on error
        raise e # Re-raise the exception
    finally:
        raw_connection.close() # Close the raw connection

# Create initial database objects
def main() -> None:
    print("Creating PostgreSQL schemas, tables,...")
    create_database_objects() # Create the database objects
    print("Database schemas and tables created successfully.")

if __name__ == "__main__":
    main() # Run the main function if the script is executed directly



