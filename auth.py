import hashlib
import hmac
import streamlit as st
from config import setting
from db import query, execute

def hash_password(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def seed_admin():
    username = setting("APP_ADMIN_USERNAME", "admin")
    password = setting("APP_ADMIN_PASSWORD", "")
    if not password:
        return

    exists = query("SELECT id FROM users WHERE username=%s", (username,))
    if not exists:
        execute(
            "INSERT INTO users(username,password_hash,full_name,role) "
            "VALUES(%s,%s,%s,'admin')",
            (username, hash_password(password), "System Administrator")
        )

def login():
    if st.session_state.get("user"):
        return True

    st.title("🔐 बळीराजा शेतकरी संघटना")
    st.subheader("Admin / Staff Login")

    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")

    if submitted:
        rows = query(
            "SELECT * FROM users WHERE username=%s AND active=1",
            (username,)
        )

        if rows and hmac.compare_digest(
            rows[0]["password_hash"],
            hash_password(password)
        ):
            st.session_state.user = rows[0]
            st.rerun()

        st.error("Username किंवा Password चुकीचा आहे.")

    return False

def is_admin():
    return (
        st.session_state.get("user", {}).get("role") == "admin"
    )
