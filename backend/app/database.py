import os
from psycopg_pool import ConnectionPool
from psycopg.rows import dict_row
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# Initialize a connection pool (min 4, max 20 connections)
db_pool = ConnectionPool(
    conninfo=DATABASE_URL,
    min_size=4,
    max_size=20,
    kwargs={"row_factory": dict_row}
)

def get_db():
    """FastAPI dependency that yields a database connection from the pool."""
    with db_pool.connection() as conn:
        yield conn