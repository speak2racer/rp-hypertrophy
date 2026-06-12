import hashlib
import os
import streamlit as st
from database import (
    get_conn, _placeholder, _fetchone_as_dict, _use_postgres,
    create_session, get_user_by_token, delete_session
)

_COOKIE_NAME = "rp_session"
_COOKIE_MAX_AGE = 60 * 60 * 24 * 30  # 30 days


def _get_cookie_manager():
    import extra_streamlit_components as stx
    return stx.CookieManager(key="rp_cookie_mgr")


def _hash_password(password: str, salt: str) -> str:
    return hashlib.sha256(f"{salt}{password}".encode()).hexdigest()


def _new_salt() -> str:
    return os.urandom(16).hex()


def _new_token() -> str:
    return os.urandom(32).hex()


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
    user = {"id": row["id"], "username": row["username"]}
    # Create persistent token
    token = _new_token()
    create_session(row["id"], token)
    return True, "Erfolgreich eingeloggt.", user, token


def get_current_user() -> dict | None:
    # 1. Already in session state (fast path)
    if "auth_user" in st.session_state:
        return st.session_state["auth_user"]
    # 2. Try cookie
    try:
        cm = _get_cookie_manager()
        token = cm.get(_COOKIE_NAME)
        if token:
            user = get_user_by_token(token)
            if user:
                st.session_state["auth_user"] = user
                st.session_state["auth_token"] = token
                return user
    except Exception:
        pass
    return None


def set_auth_cookie(token: str):
    try:
        cm = _get_cookie_manager()
        cm.set(_COOKIE_NAME, token, max_age=_COOKIE_MAX_AGE)
    except Exception:
        pass


def require_auth() -> dict:
    user = get_current_user()
    if not user:
        st.switch_page("app.py")
        st.stop()
    return user


def logout():
    token = st.session_state.pop("auth_token", None)
    st.session_state.pop("auth_user", None)
    if token:
        delete_session(token)
    try:
        cm = _get_cookie_manager()
        cm.delete(_COOKIE_NAME)
    except Exception:
        pass


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
