import streamlit as st
from streamlit_cookies_controller import CookieController
from cryptography.fernet import Fernet
from dotenv import load_dotenv
import os
import json
import pandas as pd
import sqlite3
from datetime import datetime, timedelta, timezone
import geocoder 
import plotly.express as px
from werkzeug.security import check_password_hash

st.set_page_config(layout="wide")

# Load environment variables
load_dotenv()
encryption_key = os.getenv('ENCRYPTION_KEY')  # This should be securely generated and stored
website = os.getenv('WEBSITE')
metrics_db_path = os.getenv('LOCAL_DB_PATH', 'health_metrics.db')
auth_db_path = os.getenv('AUTH_DB_PATH', 'auth_users.db')
admin_email = "healthmetrics@changh.simplelogin.com"

# Initialize the cookie controller and encryption suite
cookie_controller = CookieController()
cipher_suite = Fernet(encryption_key.encode())


def get_metrics_db_connection():
    conn = sqlite3.connect(metrics_db_path)
    conn.row_factory = sqlite3.Row
    return conn


def get_auth_db_connection():
    conn = sqlite3.connect(auth_db_path)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_database():
    with get_auth_db_connection() as conn:
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

    with get_metrics_db_connection() as conn:
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

# Helper functions for encryption and decryption
def encrypt_data(data):
    """Encrypts data using Fernet encryption."""
    return cipher_suite.encrypt(data.encode()).decode()

def decrypt_data(encrypted_data):
    """Decrypts data using Fernet decryption."""
    return cipher_suite.decrypt(encrypted_data.encode()).decode()


def get_user_by_email(email):
    with get_auth_db_connection() as conn:
        user = conn.execute(
            "SELECT id, email, password_hash FROM users WHERE email = ?",
            (email,),
        ).fetchone()
    return user


def get_user_by_id(user_id):
    with get_auth_db_connection() as conn:
        user = conn.execute(
            "SELECT id, email FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
    return user

# Login function
def login_user(email, password):
    user = get_user_by_email(email)
    if not user or not check_password_hash(user["password_hash"], password):
        st.error("Login failed: invalid email or password.")
        return

    st.session_state["user"] = {"id": user["id"]}
    st.session_state["email"] = email
    # Encrypt and set cookies
    cookie_controller.set("email", encrypt_data(email))
    cookie_controller.set("user", encrypt_data(str(user["id"])))
    st.success("Login successful!")
    st.rerun()

# Logout function
def logout_user():
    st.session_state.pop("user", None)
    st.session_state.pop("email", None)
    st.session_state.pop("view", None)
    st.session_state.pop("pending_action", None)
    st.session_state.pop("admin_feedback", None)
    st.session_state.pop("confirm_action_password", None)
    cookie_controller.remove("email")
    cookie_controller.remove("user")
    st.success("Logout successful!")
    st.rerun()


def is_admin_user():
    current_email = st.session_state.get("email", "")
    return current_email.lower() == admin_email.lower()


def verify_current_user_password(password):
    current_email = st.session_state.get("email")
    if not current_email:
        return False
    user = get_user_by_email(current_email)
    if not user:
        return False
    return check_password_hash(user["password_hash"], password)

# Check for cookies and load session state
def load_session_from_cookies():
    cookie_email = cookie_controller.get("email")
    cookie_user = cookie_controller.get("user")
    if cookie_email and cookie_user:
        try:
            # Decrypt cookies before loading into session
            email = decrypt_data(cookie_email)
            user_id = int(decrypt_data(cookie_user))
            user = get_user_by_id(user_id)
            if user and user["email"] == email:
                st.session_state["email"] = email
                st.session_state["user"] = {"id": user_id}
            else:
                cookie_controller.remove("email")
                cookie_controller.remove("user")
        except Exception as e:
            st.error(f"Failed to load session from cookies: {e}")

# Get all documents from the database with pagination
def get_all_documents():
    with get_metrics_db_connection() as conn:
        rows = conn.execute(
            """
            SELECT date, systolic_bp, diastolic_bp, heart_rate, weight, note
            FROM health_entries
            WHERE email = ?
            ORDER BY date ASC
            """,
            (st.session_state["email"],),
        ).fetchall()

    documents = [dict(row) for row in rows]
    return {"documents": documents}


def get_all_user_emails():
    with get_auth_db_connection() as conn:
        rows = conn.execute(
            "SELECT email FROM users ORDER BY email ASC"
        ).fetchall()
    return [row["email"] for row in rows]


def get_entries_for_email(email):
    with get_metrics_db_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, email, date, systolic_bp, diastolic_bp, heart_rate, weight, note
            FROM health_entries
            WHERE email = ?
            ORDER BY date DESC
            """,
            (email,),
        ).fetchall()
    return [dict(row) for row in rows]


def update_entry(entry_id, new_data):
    with get_metrics_db_connection() as conn:
        conn.execute(
            """
            UPDATE health_entries
            SET date = ?, systolic_bp = ?, diastolic_bp = ?, heart_rate = ?, weight = ?, note = ?
            WHERE id = ?
            """,
            (
                new_data["date"],
                new_data["systolic_bp"],
                new_data["diastolic_bp"],
                new_data["heart_rate"],
                new_data["weight"],
                new_data["note"],
                entry_id,
            ),
        )
        conn.commit()


def delete_entry(entry_id):
    with get_metrics_db_connection() as conn:
        conn.execute("DELETE FROM health_entries WHERE id = ?", (entry_id,))
        conn.commit()


@st.dialog("Confirm Action")
def show_data_change_confirm_dialog():
    pending = st.session_state.get("pending_action")
    if not pending:
        return

    action = pending["action"]

    st.markdown(
        """
        <style>
        div[data-testid="stDialog"] .stButton > button {
            min-height: 3rem;
            font-size: 1.05rem;
            font-weight: 600;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.warning("This will change stored data. Please confirm carefully.")
    if action == "update":
        st.write("You are trying to change (Original data) to (New data). Proceed?")
        st.text("Original data")
        st.code(json.dumps(pending["original"], indent=2), language="json")
        st.text("New data")
        st.code(json.dumps(pending["new"], indent=2), language="json")
    elif action == "delete":
        st.write("You are trying to delete this entry. Proceed?")
        st.text("Original data")
        st.code(json.dumps(pending["original"], indent=2), language="json")

    password_confirmation = st.text_input(
        "Re-enter your password to confirm",
        type="password",
        key="confirm_action_password",
    )

    col_yes, col_no = st.columns(2)
    if col_yes.button("Yes, Proceed", type="primary", use_container_width=True):
        if not password_confirmation:
            st.error("Password is required to confirm this action.")
        elif not verify_current_user_password(password_confirmation):
            st.error("Password confirmation failed.")
        else:
            if action == "update":
                update_entry(pending["entry_id"], pending["new"])
                st.session_state["admin_feedback"] = "Entry updated successfully."
            elif action == "delete":
                delete_entry(pending["entry_id"])
                st.session_state["admin_feedback"] = "Entry deleted successfully."

            st.session_state.pop("pending_action", None)
            st.session_state.pop("confirm_action_password", None)
            st.rerun()

    if col_no.button("No, Cancel", use_container_width=True):
        st.session_state.pop("pending_action", None)
        st.session_state.pop("confirm_action_password", None)
        st.session_state["admin_feedback"] = "Action canceled."
        st.rerun()

# Add a new document to the database
def add_document(data):
    if "email" not in st.session_state:
        st.error("You must be logged in to add data.")
        return
    data["email"] = st.session_state["email"]
    with get_metrics_db_connection() as conn:
        conn.execute(
            """
            INSERT INTO health_entries (
                email, date, systolic_bp, diastolic_bp, heart_rate, weight, note, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data["email"],
                data["date"],
                data["systolic_bp"],
                data["diastolic_bp"],
                data["heart_rate"],
                data["weight"],
                data["note"],
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        conn.commit()

# load documents into a pandas dataframe
def load_data():
    documents = get_all_documents()
    data = []
    
    for document in documents['documents']:
        # Extract relevant fields
        entry = {
            "date": document.get("date"),
            "systolic_bp": document.get("systolic_bp"),
            "diastolic_bp": document.get("diastolic_bp"),
            "heart_rate": document.get("heart_rate"),
            "weight": document.get("weight"),
            "note": document.get("note")
        }
        data.append(entry)
    
    # Convert the list of dictionaries to a pandas DataFrame
    df = pd.DataFrame(data)
    
    if df.empty:
        return df

    # Ensure metric columns are numeric even if source data has unexpected text/null values.
    metric_cols = ["systolic_bp", "diastolic_bp", "heart_rate", "weight"]
    for col in metric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Parse stored timestamps as UTC before converting to local timezone.
    df['date'] = pd.to_datetime(df['date'], utc=True)
    
    # Sort by date to ensure interpolation happens in chronological order
    df = df.sort_values(by='date')

    # Localize time to device location time
    g = geocoder.ip('me')
    device_timezone = g.geojson['features'][0]['properties']['raw']['timezone']
    df['date'] = df['date'].dt.tz_convert(device_timezone)

    # Remove timezone information for display
    df['date'] = df['date'].dt.tz_localize(None)
    
    # Interpolate missing weight values linearly
    df['weight'] = df['weight'].interpolate(method='linear')

    return df

def add_data():
    date = datetime.now(timezone.utc).isoformat()
    systolic = st.number_input("Systolic BP", min_value=0)
    diastolic = st.number_input("Diastolic BP", min_value=0)
    heart_rate = st.number_input("Heart Rate", min_value=0)
    weight = st.number_input("Weight", min_value=0.0, value=None)
    note = st.text_input("Note", value=None)

    if st.button("Add Entry"):
        # Check if systolic, diastolic and heartrate have data
        if not systolic or not diastolic or not heart_rate:
            st.write("Please enter all the required fields")
        else:
            new_entry = {
                "date": date,
                "systolic_bp": systolic,
                "diastolic_bp": diastolic,
                "heart_rate": heart_rate,
                "weight": weight,
                "note": note
            }
            add_document(new_entry)
            st.rerun()

def homepage():
    st.link_button("Home", website, type="primary")


def render_health_dashboard():
    df = load_data()
    if df.empty:
        st.write("No data to display.")
        return

    plot_columns = ["systolic_bp", "diastolic_bp", "heart_rate", "weight"]
    plot_columns = [col for col in plot_columns if df[col].notna().any()]

    if not plot_columns:
        st.warning("No numeric metric data available for plotting.")
        return

    end_date = datetime.now() + timedelta(days=1)
    start_date = end_date - timedelta(days=30)
    fig = px.line(
        df,
        x='date',
        y=plot_columns,
        title='Health Metrics Over Time'
    )
    fig.update_xaxes(range=[start_date, end_date])
    fig.update_layout(height=520)
    st.plotly_chart(fig, use_container_width=True)

    display_df = df.copy()
    display_df['date'] = display_df['date'].dt.strftime('%Y-%m-%d %H:%M')

    st.dataframe(
        display_df.sort_values(by='date', ascending=False),
        use_container_width=True,
        height=520,
        column_config={
            "note": st.column_config.TextColumn("Note", width="large"),
        },
    )


def render_data_editor():
    st.subheader("Edit Data")

    if st.button("Back to Dashboard", key="back_to_dashboard_top"):
        st.session_state["view"] = "main"
        st.rerun()

    if is_admin_user():
        st.caption(f"Signed in as admin: {admin_email}")
    else:
        st.caption(f"Signed in as: {st.session_state.get('email', '')}")

    if st.session_state.get("admin_feedback"):
        st.success(st.session_state["admin_feedback"])
        st.session_state.pop("admin_feedback", None)

    if is_admin_user():
        editable_users = get_all_user_emails()
        if not editable_users:
            st.info("No users found.")
            return
        current_email = st.session_state.get("email", "")
        editable_users = sorted(
            editable_users,
            key=lambda email: (email.lower() != current_email.lower(), email.lower()),
        )
        default_index = editable_users.index(current_email) if current_email in editable_users else 0
        target_email = st.selectbox(
            "User to edit",
            editable_users,
            index=default_index,
            key="admin_target_email",
        )
    else:
        target_email = st.session_state.get("email", "")
        st.text_input("User to edit", value=target_email, disabled=True)

    entries = get_entries_for_email(target_email)

    if not entries:
        st.info("This user has no entries to edit.")
        return

    st.dataframe(
        pd.DataFrame(entries),
        use_container_width=True,
        height=320,
        column_config={"note": st.column_config.TextColumn("Note", width="large")},
    )

    entry_labels = [
        f"ID {entry['id']} | {entry['date']} | HR {entry['heart_rate']} | BP {entry['systolic_bp']}/{entry['diastolic_bp']}"
        for entry in entries
    ]
    selected_label = st.selectbox("Entry to edit", entry_labels, key="admin_entry_label")
    selected_entry = entries[entry_labels.index(selected_label)]

    st.markdown("### Edit Selected Entry")
    date_value = st.text_input("Date (ISO8601)", value=selected_entry["date"], key=f"edit_date_{selected_entry['id']}")
    systolic_value = st.number_input("Systolic BP", min_value=0, value=int(selected_entry["systolic_bp"]), key=f"edit_sys_{selected_entry['id']}")
    diastolic_value = st.number_input("Diastolic BP", min_value=0, value=int(selected_entry["diastolic_bp"]), key=f"edit_dia_{selected_entry['id']}")
    heart_rate_value = st.number_input("Heart Rate", min_value=0, value=int(selected_entry["heart_rate"]), key=f"edit_hr_{selected_entry['id']}")
    weight_default = 0.0 if selected_entry["weight"] is None else float(selected_entry["weight"])
    weight_value = st.number_input("Weight", min_value=0.0, value=weight_default, key=f"edit_weight_{selected_entry['id']}")
    note_default = "" if selected_entry["note"] is None else str(selected_entry["note"])
    note_value = st.text_area("Note", value=note_default, key=f"edit_note_{selected_entry['id']}")

    if st.button("Review Change", type="primary"):
        original_data = {
            "email": selected_entry["email"],
            "date": selected_entry["date"],
            "systolic_bp": selected_entry["systolic_bp"],
            "diastolic_bp": selected_entry["diastolic_bp"],
            "heart_rate": selected_entry["heart_rate"],
            "weight": selected_entry["weight"],
            "note": selected_entry["note"],
        }
        new_data = {
            "date": date_value,
            "systolic_bp": int(systolic_value),
            "diastolic_bp": int(diastolic_value),
            "heart_rate": int(heart_rate_value),
            "weight": float(weight_value),
            "note": note_value,
        }
        st.session_state["pending_action"] = {
            "action": "update",
            "entry_id": selected_entry["id"],
            "original": original_data,
            "new": new_data,
        }
        show_data_change_confirm_dialog()

    st.markdown("---")
    st.warning("Delete permanently removes this entry.")
    if st.button("Delete Entry"):
        original_data = {
            "email": selected_entry["email"],
            "date": selected_entry["date"],
            "systolic_bp": selected_entry["systolic_bp"],
            "diastolic_bp": selected_entry["diastolic_bp"],
            "heart_rate": selected_entry["heart_rate"],
            "weight": selected_entry["weight"],
            "note": selected_entry["note"],
        }
        st.session_state["pending_action"] = {
            "action": "delete",
            "entry_id": selected_entry["id"],
            "original": original_data,
        }
        show_data_change_confirm_dialog()

    st.markdown("---")
    if st.button("Back to Dashboard", key="back_to_dashboard_bottom"):
        st.session_state["view"] = "main"
        st.rerun()

# Main application function
def main():
    initialize_database()
    st.title("Health Metrics App")
 
    # Check if user is cookie authenticated
    if "user" not in st.session_state:
        load_session_from_cookies()

    if "user" in st.session_state:
        if "view" not in st.session_state:
            st.session_state["view"] = "main"

        # User-specific data display
        with st.sidebar:
            homepage()
            add_data()
            st.markdown("---")
            if st.button("Edit Data"):
                st.session_state["view"] = "admin"
                st.rerun()
            # Logout button
            # Separator to visually distinguish the logout button
            st.markdown("---")
            if st.button("Logout"):
                logout_user()

        if st.session_state.get("view") == "admin":
            render_data_editor()
        else:
            render_health_dashboard()

        
    else:
        # Login interface
        st.subheader("Login")
        login_email = st.text_input("Login Email", key="login_email")
        login_password = st.text_input("Login Password", type="password", key="login_password")
        if st.button("Login"):
            login_user(login_email, login_password)

if __name__ == '__main__':
    main()
