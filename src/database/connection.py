"""
Create and provide resusable SQLAlchemy database engine.

Other files can import this module to get a database engine without having to create one themselves.
"""

from sqlalchemy import create_engine, text

from sqlalchemy.engine import Engine

from src.config.settings import SQLALCHEMY_DATABASE_URL

# ============================================================
# Create the shared database engine
# ============================================================

engine = create_engine(SQLALCHEMY_DATABASE_URL, pool_pre_ping=True,) # Create a SQLAlchemy engine with the database URL and enable connection pool pre-ping to check connections before using them.

# Return the database engine
def get_engine() -> Engine:
    return engine

# TEst if Python can connect to PostgreSQL database using the engine
def test_connection() -> bool:
    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1 AS connection_test")) # Execute a simple SQL query to test the connection

        value = result.scalar_one() # Get the scalar value from the result
    return value == 1

# Run database connection test if the script is executed directly
def main() -> None:
    print("Testing database connection...")
    if test_connection():
        print("Database connection successful.")
        with engine.connect() as connection:
            print(
                "current_database():",
                connection.execute(text("SELECT current_database()")).scalar_one(),
            )
            print(
                "current_user:",
                connection.execute(text("SELECT current_user")).scalar_one(),
            )
            tables = connection.execute(
                text(
                    """
                    SELECT table_schema, table_name
                    FROM information_schema.tables
                    WHERE (table_schema, table_name) IN (
                        ('metadata', 'pipeline_runs'),
                        ('analytics', 'dim_locations'),
                        ('raw', 'weather_hourly')
                    )
                    ORDER BY table_schema, table_name
                    """
                )
            ).fetchall()

            for row in tables:
                print(f"{row.table_schema}.{row.table_name}")
    else:
        print("Database connection failed.")

if __name__ == "__main__":
    main()
