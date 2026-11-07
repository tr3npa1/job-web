"""Request-independent mysql.connector transactions; never initialize data on startup."""

import os
from contextlib import contextmanager
from pathlib import Path

import mysql.connector
from dotenv import load_dotenv

load_dotenv(Path(__file__).with_name(".env"))


@contextmanager
def transaction():
    try:
        port = int(os.getenv("DB_PORT", "3306"))
        if not 1 <= port <= 65535:
            raise ValueError
    except ValueError as error:
        raise RuntimeError("DB_PORT must be an integer between 1 and 65535.") from error
    connection = mysql.connector.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=port,
        user=os.getenv("DB_USER", "job_web"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "mydb"),
        connection_timeout=5,
        autocommit=False,
        charset="utf8mb4",
    )
    cursor = None
    try:
        cursor = connection.cursor(dictionary=True, buffered=True)
        yield cursor
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        try:
            if cursor is not None:
                cursor.close()
        finally:
            connection.close()
