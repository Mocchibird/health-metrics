# Health Metrics App

A Streamlit app for tracking health metrics with local SQLite storage.

## Features

- Email/password login with encrypted cookie session support
- Local databases (no managed cloud database required)
- Add and view health entries with plot and table views
- Edit and delete entries with confirmation and password re-entry
- Admin account support for managing all users' entries
- No in-app user registration (accounts are managed from terminal only)

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

## Run Locally

1. Create and activate a virtual environment.

   python3 -m venv .venv
   source .venv/bin/activate

2. Install dependencies:

   pip install -r requirements.txt

3. Start Streamlit:

   streamlit run app.py

## User Management Commands

Run these from the project root with your virtual environment activated:

Important:

- Online/in-app user registration is disabled.
- Creating and deleting users must be done from terminal commands.

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

## Docker

Build and run:

1. docker build -t health-metrics-app .
2. docker run -p 8501:8501 --env-file .env health-metrics-app

## Security Notes

- Edit and delete operations require password re-entry in the app.
- If deploying behind Nginx, bind Streamlit to localhost for tighter network exposure.

## License

MIT License. See LICENSE.
