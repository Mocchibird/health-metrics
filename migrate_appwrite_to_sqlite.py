import os
import sqlite3
from datetime import datetime, timezone

from appwrite.client import Client
from appwrite.query import Query
from appwrite.services.databases import Databases
from appwrite.services.users import Users
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash


def get_sqlite_connection(path):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_local_databases(auth_db_path, metrics_db_path):
    with get_sqlite_connection(auth_db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.commit()

    with get_sqlite_connection(metrics_db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS health_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL,
                date TEXT NOT NULL,
                systolic_bp INTEGER NOT NULL,
                diastolic_bp INTEGER NOT NULL,
                heart_rate INTEGER NOT NULL,
                weight REAL,
                note TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_health_entries_email_date
            ON health_entries(email, date)
            """
        )
        conn.commit()


def setup_appwrite_client():
    endpoint = os.getenv("APPWRITE_ENDPOINT", "https://cloud.appwrite.io/v1")
    project_id = os.getenv("APPWRITE_PROJECT_ID")
    api_key = os.getenv("APPWRITE_API_KEY")

    if not project_id or not api_key:
        raise RuntimeError("Missing APPWRITE_PROJECT_ID or APPWRITE_API_KEY in environment.")

    client = Client()
    client.set_endpoint(endpoint)
    client.set_project(project_id)
    client.set_key(api_key)
    return client


def migrate_users(users_service, auth_db_path, default_password):
    total = 0
    offset = 0
    limit = 100

    with get_sqlite_connection(auth_db_path) as conn:
        while True:
            response = users_service.list(queries=[Query.limit(limit), Query.offset(offset)])
            users = response.get("users", [])

            for user in users:
                email = user.get("email")
                if not email:
                    continue

                created_at = user.get("$createdAt") or datetime.now(timezone.utc).isoformat()
                conn.execute(
                    """
                    INSERT INTO users (email, password_hash, created_at)
                    VALUES (?, ?, ?)
                    ON CONFLICT(email) DO NOTHING
                    """,
                    (email, generate_password_hash(default_password), created_at),
                )
                total += 1

            conn.commit()

            if len(users) < limit:
                break
            offset += limit

    return total


def migrate_health_data(databases_service, metrics_db_path, database_id, collection_id):
    total = 0
    offset = 0
    limit = 100

    with get_sqlite_connection(metrics_db_path) as conn:
        while True:
            response = databases_service.list_documents(
                database_id=database_id,
                collection_id=collection_id,
                queries=[Query.limit(limit), Query.offset(offset)],
            )
            documents = response.get("documents", [])

            for doc in documents:
                email = doc.get("email")
                date = doc.get("date") or doc.get("$createdAt")

                if not email or not date:
                    continue

                systolic_bp = int(doc.get("systolic_bp") or 0)
                diastolic_bp = int(doc.get("diastolic_bp") or 0)
                heart_rate = int(doc.get("heart_rate") or 0)
                weight = doc.get("weight")
                note = doc.get("note")
                created_at = doc.get("$createdAt") or datetime.now(timezone.utc).isoformat()

                conn.execute(
                    """
                    INSERT INTO health_entries (
                        email, date, systolic_bp, diastolic_bp, heart_rate, weight, note, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        email,
                        date,
                        systolic_bp,
                        diastolic_bp,
                        heart_rate,
                        weight,
                        note,
                        created_at,
                    ),
                )
                total += 1

            conn.commit()

            if len(documents) < limit:
                break
            offset += limit

    return total


def main():
    load_dotenv()

    auth_db_path = os.getenv("AUTH_DB_PATH", "auth_users.db")
    metrics_db_path = os.getenv("LOCAL_DB_PATH", "health_metrics.db")
    database_id = os.getenv("APPWRITE_DATABASE_ID", "health_metric_db")
    collection_id = os.getenv("APPWRITE_COLLECTION_ID")
    default_password = os.getenv("MIGRATION_DEFAULT_PASSWORD", "ChangeMe123!")

    if not collection_id:
        raise RuntimeError("Missing APPWRITE_COLLECTION_ID in environment.")

    initialize_local_databases(auth_db_path, metrics_db_path)

    client = setup_appwrite_client()
    users_service = Users(client)
    databases_service = Databases(client)

    users_count = migrate_users(users_service, auth_db_path, default_password)
    docs_count = migrate_health_data(databases_service, metrics_db_path, database_id, collection_id)

    print(f"Migrated users inserted/seen: {users_count}")
    print(f"Migrated health documents: {docs_count}")
    print("Done.")


if __name__ == "__main__":
    main()
