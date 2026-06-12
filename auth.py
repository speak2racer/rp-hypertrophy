import hashlib
import os
import streamlit as st
from database import (
    get_conn, _placeholder, _fetchone_as_dict,
    create_session, get_user_by_token, delete_session
)

_LS_KEY = "rp_session"
_COOKIE_MAX_AGE = 60 * 60 * 24 * 30  # 30 days (used as JS expiry hint only)


# ── localStorage helpers via streamlit-js-eval ────────────────────────────────

def _js_get_token() -> str | None:
    """Read token from localStorage. Returns None on first render (async)."""
    from streamlit_js_eval import streamlit_js_eval
    return streamlit_js_eval(
        js_expressions=f"localStorage.getItem('{_LS_KEY}')",
        key="_rp_ls_get"
    )


def _js_set_token(token: str):
    from streamlit_js_eval import streamlit_js_eval
    # Escape token (hex string, safe) and set with expiry timestamp hint
    streamlit_js_eval(
        js_expressions=f"localStorage.setItem('{_LS_KEY}', '{token}'); '{token}'",
        key="_rp_ls_set"
    )


def _js_clear_token():
    from streamlit_js_eval import streamlit_js_eval
    streamlit_js_eval(
        js_expressions=f"localStorage.removeItem('{_LS_KEY}'); 'cleared'",
        key="_rp_ls_clear"
    )


# ── Password helpers ──────────────────────────────────────────────────────────

def _hash_password(password: str, salt: str) -> str:
    return hashlib.sha256(f"{salt}{password}".encode()).hexdigest()


def _new_salt() -> str:
    return os.urandom(16).hex()


def _new_token() -> str:
    return os.urandom(32).hex()


# ── Register / Login ──────────────────────────────────────────────────────────

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


def login_user(username: str, password: str) -> tuple[bool, str, dict | None, str | None]:
    username = username.strip().lower()
    p = _placeholder()
    conn = get_conn()
    c = conn.cursor()
    c.execute(f"SELECT id, username, password_hash, salt FROM users WHERE username={p}", (username,))
    row = _fetchone_as_dict(c)
    conn.close()
    if not row:
        return False, "Benutzername nicht gefunden.", None, None
    if _hash_password(password, row["salt"]) != row["password_hash"]:
        return False, "Falsches Passwort.", None, None
    user = {"id": row["id"], "username": row["username"]}
    token = _new_token()
    create_session(row["id"], token)
    return True, "Erfolgreich eingeloggt.", user, token


# ── Auth flow ─────────────────────────────────────────────────────────────────

def init_auth() -> bool:
    """
    Call at top of every page before any st.stop().

    Flow:
      - If auth_user in session_state → already logged in, return True
      - First render: localStorage not read yet → show loading, st.stop()
        streamlit-js-eval triggers automatic rerun when JS resolves
      - Second+ render: localStorage value available
        → validate token → set session_state → return True
        → no valid token → return False (show login)
    """
    # Already authenticated
    if "auth_user" in st.session_state:
        return True

    # Read token from localStorage (returns None on first render)
    token = _js_get_token()

    if token is None:
        # Component hasn't executed JS yet — will auto-rerun when it does
        st.markdown(
            "<div style='display:flex;align-items:center;justify-content:center;"
            "height:80vh;color:#444;font-size:0.9rem'>Laden …</div>",
            unsafe_allow_html=True,
        )
        st.stop()

    # token is "" (empty string) or a real token
    if token:
        user = get_user_by_token(str(token))
        if user:
            st.session_state["auth_user"] = user
            st.session_state["auth_token"] = str(token)
            return True

    return False


def set_auth_token(token: str):
    """Persist token to localStorage after login."""
    _js_set_token(token)


def get_current_user() -> dict | None:
    return st.session_state.get("auth_user")


def require_auth() -> dict:
    """Call after init_auth(). Redirects to login if not authenticated."""
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
    _js_clear_token()


def render_sidebar_user():
    user = get_current_user()
    if user:
        with st.sidebar:
            st.markdown(f"""
            <div style='padding:10px 4px 14px;border-bottom:1px solid #1e1e1e;margin-bottom:8px'>
                <div style='font-size:0.72rem;color:#555;text-transform:uppercase;
                            letter-spacing:.06em'>Eingeloggt als</div>
                <div style='font-size:0.95rem;font-weight:700;color:#f0f0f0;
                            margin-top:4px'>{user['username']}</div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("Abmelden", use_container_width=True):
                logout()
                st.rerun()
