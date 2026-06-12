import hashlib
import os
import streamlit as st
from database import get_conn, _placeholder, _fetchone_as_dict, _use_postgres


def _hash_password(password: str, salt: str) -> str:
    return hashlib.sha256(f"{salt}{password}".encode()).hexdigest()


def _new_salt() -> str:
    return os.urandom(16).hex()


def register_user(username: str, password: str) -> tuple[bool, str]:
    username = username.strip().lower()
    if len(username) < 3:
        return False, "Benutzername muss mindestens 3 Zeichen haben."
    if len(password) < 6:
        return False, "Passwort muss mindestens 6 Zeichen haben."
    p = _placeholder()
    conn = get_conn()
    c = conn.cursor()
    c.execute(f"SELECT id FROM users WHERE username={p}", (username,))
    if c.fetchone():
        conn.close()
        return False, "Benutzername bereits vergeben."
    salt = _new_salt()
    pw_hash = _hash_password(password, salt)
    c.execute(
        f"INSERT INTO users (username, password_hash, salt) VALUES ({p},{p},{p})",
        (username, pw_hash, salt)
    )
    conn.commit()
    conn.close()
    return True, "Registrierung erfolgreich."


def login_user(username: str, password: str) -> tuple[bool, str, dict | None]:
    username = username.strip().lower()
    p = _placeholder()
    conn = get_conn()
    c = conn.cursor()
    c.execute(f"SELECT id, username, password_hash, salt FROM users WHERE username={p}", (username,))
    row = _fetchone_as_dict(c)
    conn.close()
    if not row:
        return False, "Benutzername nicht gefunden.", None
    expected = _hash_password(password, row["salt"])
    if expected != row["password_hash"]:
        return False, "Falsches Passwort.", None
    return True, "Erfolgreich eingeloggt.", {"id": row["id"], "username": row["username"]}


def get_current_user() -> dict | None:
    return st.session_state.get("auth_user")


def require_auth() -> dict:
    """Call at top of every page. Returns user dict or stops the page."""
    user = get_current_user()
    if not user:
        st.switch_page("app.py")
        st.stop()
    return user


def logout():
    st.session_state.pop("auth_user", None)


def render_sidebar_user():
    user = get_current_user()
    if user:
        with st.sidebar:
            st.markdown(f"""
            <div style='padding:10px 4px 14px;border-bottom:1px solid #1e1e1e;margin-bottom:8px'>
                <div style='font-size:0.72rem;color:#555;text-transform:uppercase;letter-spacing:.06em'>Eingeloggt als</div>
                <div style='font-size:0.95rem;font-weight:700;color:#f0f0f0;margin-top:4px'>{user['username']}</div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("Abmelden", use_container_width=True):
                logout()
                st.rerun()
