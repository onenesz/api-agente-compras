import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from psycopg.rows import dict_row

load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)


def connect_database():
    """Cada conexión mantiene una instantánea consistente y de solo lectura."""
    return psycopg.connect(
        host=os.environ["POSTGRES_HOST"],
        port=int(os.environ["POSTGRES_PORT"]),
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.getenv("POSTGRES_PASSWORD", ""),
        connect_timeout=10,
        options="-c default_transaction_read_only=on "
                "-c default_transaction_isolation=repeatable\\ read "
                "-c statement_timeout=10000",
        row_factory=dict_row,
    )


def get_database():
    with connect_database() as connection:
        yield connection
