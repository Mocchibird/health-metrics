# Health Metrics

A self-hostable Streamlit app for tracking personal health metrics with local SQLite storage, authenticated access, and simple dashboard views.

It is intentionally lightweight: no managed cloud database, no large backend stack, and no complicated deployment requirements. It is designed for personal use and small-scale self-hosting.

## Features

- Email/password login
- Encrypted cookie-based session persistence
- Local SQLite storage for both authentication and metric data
- Add and view health entries
- Time-series dashboard with plots and table view
- Edit and delete entries with confirmation and password re-entry
- Admin account support for managing all users' entries
- Docker support for simple deployment

### Important:
- **In-app user registration is disabled.**
- **Creating and deleting users must be done from the terminal.**

## Metrics tracked

Each health entry can include:

- systolic blood pressure
- diastolic blood pressure
- heart rate
- weight
- note
- timestamp

## Tech stack

- Streamlit
- SQLite
- Pandas
- Plotly
- Cryptography (Fernet)
- Docker

## Local data storage

The app uses two SQLite databases:

- `auth_users.db` for user authentication data
- `health_metrics.db` for health metric entries

No separate database server is required.

## Environment variables

Configure the app through a `.env` file:

- `ENCRYPTION_KEY` – Fernet key used for cookie encryption
- `WEBSITE` – URL used for the Home button
- `LOCAL_DB_PATH` – path to the health metrics database  
  Default: `health_metrics.db`
- `AUTH_DB_PATH` – path to the auth database  
  Default: `auth_users.db`

## Run locally

1. Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Install dependencies

```bash
pip install -r requirements.txt
```

3. Start the app

```bash
streamlit run app.py
```

## Docker

Build and run with Docker:

```bash
docker build -t health-metrics-app .
docker run -p 8501:8501 --env-file .env health-metrics-app
```
The container exposes the Streamlit app on port `8501`

## User management

In-app registration is intentionally disabled.

Users are managed from the terminal by writing directly to the authentication database.  
The current repository includes example one-line commands for:

- listing users
- creating users
- deleting users

This keeps the app simple while still allowing controlled account management.

## User Management Commands

Run these from the project root with your virtual environment activated:

1. Show current users

```bash
python -c "import sqlite3; c=sqlite3.connect('auth_users.db'); rows=c.execute('SELECT id,email,created_at FROM users ORDER BY id').fetchall(); print('\n'.join(str(r) for r in rows) or 'No users found'); c.close()"
```

2. Create a user

```bash
python -c "import sqlite3; from datetime import datetime, timezone; from werkzeug.security import generate_password_hash as h; email='newuser@example.com'; pw='ChangeThisPassword123'; c=sqlite3.connect('auth_users.db'); cur=c.cursor(); cur.execute('INSERT INTO users (email,password_hash,created_at) VALUES (?,?,?)',(email,h(pw),datetime.now(timezone.utc).isoformat())); c.commit(); print('rows_inserted=',cur.rowcount); c.close()"
```

3. Delete a user

```bash
python -c "import sqlite3; email='user_to_delete@example.com'; c=sqlite3.connect('auth_users.db'); cur=c.cursor(); cur.execute('DELETE FROM users WHERE lower(email)=lower(?)',(email,)); c.commit(); print('rows_deleted=',cur.rowcount); c.close()"
```

Notes:

- Replace the example emails/passwords before running commands.
- Use strong passwords and avoid shell special characters unless escaped.

## Security notes

- Sessions are stored using encrypted cookies
- Edit and delete operations require password re-entry
- For self-hosted deployments behind a reverse proxy, binding Streamlit to localhost is the safer default

## Notes

This is a small personal project, not a production medical platform.  
The focus is on lightweight self-hosting, straightforward data entry, and simple visualization.

## License

MIT License. See `LICENSE`.
