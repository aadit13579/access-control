import os
from typing import Generator
from dotenv import load_dotenv
from psycopg import Connection
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "")

# Initialize a connection pool (min 4, max 20 connections).
# open=False delays connection opening until lifespan startup.
db_pool = ConnectionPool(
    conninfo=DATABASE_URL,
    min_size=4,
    max_size=20,
    open=False,
    kwargs={"row_factory": dict_row},
)


def get_db() -> Generator[Connection, None, None]:
    """FastAPI dependency that yields a database connection from the pool."""
    with db_pool.connection() as conn:
        yield conn
