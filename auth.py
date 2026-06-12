import hashlib
import os
import streamlit as st
from database import (
    get_conn, _placeholder, _fetchone_as_dict,
    create_session, get_user_by_token, delete_session, get_all_users
)

_LS_KEY = "rp_session"
_COOKIE_MAX_AGE = 60 * 60 * 24 * 30  # 30 days (used as JS expiry hint only)


# ── localStorage helpers via streamlit-js-eval ────────────────────────────────

def _js_get_token() -> str | None:
    """
    Returns token string, empty string (no token), or None (JS not run yet).
    Using || '' ensures null becomes '' so we can distinguish from not-loaded.
    """
    from streamlit_js_eval import streamlit_js_eval
    return streamlit_js_eval(
        js_expressions=f"localStorage.getItem('{_LS_KEY}') || ''",
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
      - If auth_user in session_state:
          → write pending token to localStorage if queued, then return True
      - First render: localStorage not read yet (JS returns None) → show loading
        streamlit-js-eval triggers automatic rerun when JS resolves
      - Second+ render: localStorage value available
          → "" → no token → return False (show login)
          → token string → validate → set session_state → return True
    """
    # Already authenticated — write pending token if login just happened
    if "auth_user" in st.session_state:
        pending = st.session_state.pop("_pending_token_save", None)
        if pending:
            # Render the set-component NOW (page continues, browser can execute it)
            _js_set_token(pending)
        return True

    # Read token from localStorage (returns None on first render)
    token = _js_get_token()

    if token is None:
        # JS not executed yet — auto-rerun will follow when component resolves
        st.markdown(
            "<div style='display:flex;align-items:center;justify-content:center;"
            "height:80vh;color:#444;font-size:0.9rem'>Laden …</div>",
            unsafe_allow_html=True,
        )
        st.stop()

    # token is "" (no entry in localStorage) or a real hex token
    if token:
        user = get_user_by_token(str(token))
        if user:
            st.session_state["auth_user"] = user
            st.session_state["auth_token"] = str(token)
            return True

    return False


def set_auth_token(token: str):
    """Queue token to be written to localStorage on the next render."""
    st.session_state["_pending_token_save"] = token


def get_current_user() -> dict | None:
    return st.session_state.get("auth_user")


def is_admin() -> bool:
    user = get_current_user()
    return bool(user and user.get("is_admin"))


def get_viewed_user_id() -> int | None:
    """Returns the user_id whose data is currently being viewed (admin impersonation)."""
    return st.session_state.get("admin_view_user_id")


def get_effective_user_id() -> int | None:
    """Returns the user_id to use for all DB queries — impersonated user if admin is viewing."""
    override = get_viewed_user_id()
    if override:
        return override
    user = get_current_user()
    return user["id"] if user else None


def get_viewed_user() -> dict | None:
    """Returns the user dict of the currently viewed user (may differ from logged-in user)."""
    override_id = get_viewed_user_id()
    if override_id:
        viewed = st.session_state.get("admin_view_user")
        return viewed
    return get_current_user()


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
    if not user:
        return
    with st.sidebar:
        viewed = get_viewed_user() or user
        viewing_other = is_admin() and viewed["id"] != user["id"]

        label_top = "👁️ Ansicht als" if viewing_other else "Eingeloggt als"
        badge = " 🔑" if user.get("is_admin") else ""
        st.markdown(f"""
        <div style='padding:10px 4px 14px;border-bottom:1px solid #1e1e1e;margin-bottom:8px'>
            <div style='font-size:0.72rem;color:#555;text-transform:uppercase;
                        letter-spacing:.06em'>{label_top}</div>
            <div style='font-size:0.95rem;font-weight:700;color:#f0f0f0;
                        margin-top:4px'>{viewed['username']}{badge}</div>
            {"<div style='font-size:0.72rem;color:#555;margin-top:2px'>Admin: " + user['username'] + "</div>" if viewing_other else ""}
        </div>
        """, unsafe_allow_html=True)

        if is_admin():
            all_users = get_all_users()
            options = [u for u in all_users]
            usernames = [u["username"] for u in options]
            current_idx = next(
                (i for i, u in enumerate(options) if u["id"] == viewed["id"]), 0
            )
            chosen_name = st.selectbox(
                "User anzeigen",
                usernames,
                index=current_idx,
                key="_admin_user_select",
            )
            chosen = next(u for u in options if u["username"] == chosen_name)
            if chosen["id"] != viewed["id"]:
                if chosen["id"] == user["id"]:
                    st.session_state.pop("admin_view_user_id", None)
                    st.session_state.pop("admin_view_user", None)
                else:
                    st.session_state["admin_view_user_id"] = chosen["id"]
                    st.session_state["admin_view_user"] = chosen
                st.rerun()

        if st.button("Abmelden", use_container_width=True):
            logout()
            st.rerun()
