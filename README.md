# Health Metrics App

A private Streamlit app for tracking health metrics with local SQLite storage.

## Features

- Email/password login with encrypted cookie session support
- Local databases (no managed cloud database required)
- Add and view health entries with plot and table views
- Edit and delete entries with confirmation and password re-entry
- Admin account support for managing all users' entries
- Optional one-time migration from Appwrite to local SQLite

## Tech Stack

- Streamlit
- SQLite
- Pandas
- Plotly
- Cryptography (Fernet)

## Local Databases

This app uses two SQLite files:

- `auth_users.db`: user authentication records
- `health_metrics.db`: health entry records

No separate database server is required.

## Environment Variables

Configure in `.env`:

- `ENCRYPTION_KEY`: Fernet key for cookie encryption
- `WEBSITE`: URL for Home button
- `LOCAL_DB_PATH`: path to metrics database (default `health_metrics.db`)
- `AUTH_DB_PATH`: path to auth database (default `auth_users.db`)

Migration-related variables:

- `APPWRITE_ENDPOINT`
- `APPWRITE_PROJECT_ID`
- `APPWRITE_API_KEY`
- `APPWRITE_DATABASE_ID`
- `APPWRITE_COLLECTION_ID`
- `MIGRATION_DEFAULT_PASSWORD`

## Run Locally

1. Create/activate your virtual environment.
2. Install dependencies:

   pip install -r requirements.txt

3. Start Streamlit:

   streamlit run app.py

## Docker

Build and run:

1. docker build -t health-metrics-app .
2. docker run -p 8501:8501 --env-file .env health-metrics-app

## Migrate Data from Appwrite

Run one-time migration:

python migrate_appwrite_to_sqlite.py

What it migrates:

- Appwrite users -> `auth_users.db` users table
- Appwrite health documents -> `health_metrics.db` health_entries table

## Security Notes

- Migrated users receive a generated/default local password hash. Rotate passwords after migration.
- Edit and delete operations require password re-entry in the app.
- If deploying behind Nginx, bind Streamlit to localhost for tighter network exposure.

## License

MIT License. See LICENSE.
