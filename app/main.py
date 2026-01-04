import streamlit as st
from auth import validate_password, hash_password, verify_password
from database import get_db, init_db
from streamlit_app import render_app

# -------------------------------------------------
# Init
# -------------------------------------------------
init_db()

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user" not in st.session_state:
    st.session_state.user = None

# -------------------------------------------------
# Login Page
# -------------------------------------------------
def login_page():
    st.title("🔐 Login")

    username = st.text_input(
        "Username",
        key="login_username"
    )

    password = st.text_input(
        "Password",
        type="password",
        key="login_password"
    )

    if st.button("Login", key="login_button"):
        db = get_db()
        row = db.execute(
            "SELECT password_hash FROM users WHERE username=?",
            (username,)
        ).fetchone()

        if row and verify_password(password, row[0]):
            st.session_state.authenticated = True
            st.session_state.user = username
            st.success("Login successful")
            st.rerun()
        else:
            st.error("Invalid credentials")

# -------------------------------------------------
# Register Page
# -------------------------------------------------
def register_page():
    st.title("📝 Register")

    username = st.text_input(
        "New Username",
        key="register_username"
    )

    password = st.text_input(
        "Password",
        type="password",
        key="register_password"
    )

    confirm = st.text_input(
        "Confirm Password",
        type="password",
        key="register_confirm"
    )

    if st.button("Create Account", key="register_button"):
        if password != confirm:
            st.error("Passwords do not match")
            return

        if not validate_password(password):
            st.error("Weak password")
            return

        try:
            db = get_db()
            db.execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                (username, hash_password(password))
            )
            db.commit()
            st.success("Account created. Please login.")
        except:
            st.error("Username already exists")

# -------------------------------------------------
# Router
# -------------------------------------------------
if not st.session_state.authenticated:
    tab1, tab2 = st.tabs(["Login", "Register"])
    with tab1:
        login_page()
    with tab2:
        register_page()
else:
    render_app()
