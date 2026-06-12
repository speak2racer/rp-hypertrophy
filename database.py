"""
Database layer — PostgreSQL via psycopg2 (Supabase) with SQLite fallback for local dev.
Connection string is read from st.secrets["DATABASE_URL"] or env var DATABASE_URL.
"""

import json
import os
import sqlite3
from pathlib import Path

import streamlit as st

# ── Connection setup ──────────────────────────────────────────────────────────

def _get_database_url() -> str | None:
    try:
        return st.secrets["DATABASE_URL"]
    except (KeyError, FileNotFoundError):
        pass
    return os.environ.get("DATABASE_URL")


def _use_postgres() -> bool:
    return bool(_get_database_url())


def get_conn():
    if _use_postgres():
        import psycopg2
        import psycopg2.extras
        conn = psycopg2.connect(_get_database_url())
        return conn
    else:
        db_path = Path(__file__).parent / "rp_hypertrophy.db"
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn


def _placeholder():
    """SQL parameter placeholder: %s for postgres, ? for sqlite."""
    return "%s" if _use_postgres() else "?"


def _fetchall_as_dicts(cursor) -> list[dict]:
    if _use_postgres():
        cols = [d[0] for d in cursor.description]
        return [dict(zip(cols, row)) for row in cursor.fetchall()]
    else:
        return [dict(r) for r in cursor.fetchall()]


def _fetchone_as_dict(cursor) -> dict | None:
    if _use_postgres():
        row = cursor.fetchone()
        if row is None:
            return None
        cols = [d[0] for d in cursor.description]
        return dict(zip(cols, row))
    else:
        row = cursor.fetchone()
        return dict(row) if row else None


# ── Schema init ───────────────────────────────────────────────────────────────

_SCHEMA_SQLITE = """
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        salt TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS mesocycles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER REFERENCES users(id),
        name TEXT NOT NULL,
        start_date TEXT NOT NULL,
        weeks INTEGER NOT NULL DEFAULT 5,
        deload_week INTEGER NOT NULL DEFAULT 1,
        muscle_groups TEXT NOT NULL,
        split_template TEXT,
        split_days TEXT,
        split_order TEXT,
        status TEXT DEFAULT 'active',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS meso_muscle_config (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        meso_id INTEGER NOT NULL,
        muscle_group TEXT NOT NULL,
        start_sets INTEGER NOT NULL,
        exercises TEXT NOT NULL,
        FOREIGN KEY (meso_id) REFERENCES mesocycles(id)
    );
    CREATE TABLE IF NOT EXISTS workouts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        meso_id INTEGER,
        date TEXT NOT NULL,
        week_number INTEGER NOT NULL,
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (meso_id) REFERENCES mesocycles(id)
    );
    CREATE TABLE IF NOT EXISTS sets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        workout_id INTEGER NOT NULL,
        muscle_group TEXT NOT NULL,
        exercise TEXT NOT NULL,
        set_number INTEGER NOT NULL,
        weight REAL,
        reps INTEGER,
        rpe REAL,
        pump INTEGER,
        soreness INTEGER,
        sfr INTEGER,
        FOREIGN KEY (workout_id) REFERENCES workouts(id)
    );
    CREATE TABLE IF NOT EXISTS session_feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        workout_id INTEGER NOT NULL,
        muscle_group TEXT NOT NULL,
        pump INTEGER,
        soreness INTEGER,
        performance INTEGER,
        notes TEXT,
        FOREIGN KEY (workout_id) REFERENCES workouts(id)
    );
    CREATE TABLE IF NOT EXISTS ten_rm (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER REFERENCES users(id),
        exercise TEXT NOT NULL,
        weight REAL NOT NULL,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, exercise)
    );
    CREATE TABLE IF NOT EXISTS sessions (
        token TEXT PRIMARY KEY,
        user_id INTEGER NOT NULL REFERENCES users(id),
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
"""

_SCHEMA_POSTGRES = """
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        username TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        salt TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT NOW()
    );
    CREATE TABLE IF NOT EXISTS mesocycles (
        id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES users(id),
        name TEXT NOT NULL,
        start_date TEXT NOT NULL,
        weeks INTEGER NOT NULL DEFAULT 5,
        deload_week INTEGER NOT NULL DEFAULT 1,
        muscle_groups TEXT NOT NULL,
        split_template TEXT,
        split_days TEXT,
        split_order TEXT,
        status TEXT DEFAULT 'active',
        created_at TIMESTAMP DEFAULT NOW()
    );
    CREATE TABLE IF NOT EXISTS meso_muscle_config (
        id SERIAL PRIMARY KEY,
        meso_id INTEGER NOT NULL REFERENCES mesocycles(id),
        muscle_group TEXT NOT NULL,
        start_sets INTEGER NOT NULL,
        exercises TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS workouts (
        id SERIAL PRIMARY KEY,
        meso_id INTEGER REFERENCES mesocycles(id),
        date TEXT NOT NULL,
        week_number INTEGER NOT NULL,
        notes TEXT,
        created_at TIMESTAMP DEFAULT NOW()
    );
    CREATE TABLE IF NOT EXISTS sets (
        id SERIAL PRIMARY KEY,
        workout_id INTEGER NOT NULL REFERENCES workouts(id),
        muscle_group TEXT NOT NULL,
        exercise TEXT NOT NULL,
        set_number INTEGER NOT NULL,
        weight REAL,
        reps INTEGER,
        rpe REAL,
        pump INTEGER,
        soreness INTEGER,
        sfr INTEGER
    );
    CREATE TABLE IF NOT EXISTS session_feedback (
        id SERIAL PRIMARY KEY,
        workout_id INTEGER NOT NULL REFERENCES workouts(id),
        muscle_group TEXT NOT NULL,
        pump INTEGER,
        soreness INTEGER,
        performance INTEGER,
        notes TEXT
    );
    CREATE TABLE IF NOT EXISTS ten_rm (
        id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES users(id),
        exercise TEXT NOT NULL,
        weight REAL NOT NULL,
        updated_at TIMESTAMP DEFAULT NOW(),
        UNIQUE(user_id, exercise)
    );
    CREATE TABLE IF NOT EXISTS sessions (
        token TEXT PRIMARY KEY,
        user_id INTEGER NOT NULL REFERENCES users(id),
        created_at TIMESTAMP DEFAULT NOW()
    );
"""


def _migrate(conn):
    """Add columns / tables that were added after initial deploy."""
    c = conn.cursor()
    if _use_postgres():
        migrations = [
            "ALTER TABLE mesocycles ADD COLUMN IF NOT EXISTS user_id INTEGER REFERENCES users(id)",
            "ALTER TABLE ten_rm ADD COLUMN IF NOT EXISTS user_id INTEGER REFERENCES users(id)",
            "ALTER TABLE workouts ADD COLUMN IF NOT EXISTS day_name TEXT",
            "ALTER TABLE mesocycles ADD COLUMN IF NOT EXISTS current_week INTEGER DEFAULT 1",
            # Drop old unique constraint on exercise alone and replace with (user_id, exercise)
            # Safe to ignore errors if constraint doesn't exist
        ]
        for sql in migrations:
            try:
                c.execute(sql)
            except Exception:
                pass
        # Recreate unique constraint on ten_rm if needed
        try:
            c.execute("ALTER TABLE ten_rm DROP CONSTRAINT IF EXISTS ten_rm_exercise_key")
            c.execute("ALTER TABLE ten_rm ADD CONSTRAINT ten_rm_user_exercise UNIQUE (user_id, exercise)")
        except Exception:
            pass
        # sessions table
        try:
            c.execute("""CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id),
                created_at TIMESTAMP DEFAULT NOW()
            )""")
        except Exception:
            pass
    else:
        # SQLite: try adding columns, ignore if already exist
        for sql in [
            "ALTER TABLE mesocycles ADD COLUMN user_id INTEGER",
            "ALTER TABLE ten_rm ADD COLUMN user_id INTEGER",
            "ALTER TABLE workouts ADD COLUMN day_name TEXT",
            "ALTER TABLE mesocycles ADD COLUMN current_week INTEGER DEFAULT 1",
            """CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )""",
        ]:
            try:
                c.execute(sql)
            except Exception:
                pass
    conn.commit()


def init_db():
    conn = get_conn()
    c = conn.cursor()
    if _use_postgres():
        for stmt in _SCHEMA_POSTGRES.strip().split(";"):
            stmt = stmt.strip()
            if stmt:
                c.execute(stmt)
    else:
        conn.executescript(_SCHEMA_SQLITE)
    conn.commit()
    _migrate(conn)
    conn.close()


# ── Mesocycles ────────────────────────────────────────────────────────────────

def _decode_meso(d: dict) -> dict:
    d["muscle_groups"] = json.loads(d["muscle_groups"])
    d["split_days"] = json.loads(d["split_days"]) if d.get("split_days") else {}
    d["split_order"] = json.loads(d["split_order"]) if d.get("split_order") else []
    return d


def create_mesocycle(name, start_date, weeks, deload_week, muscle_groups,
                     split_template=None, split_days=None, split_order=None,
                     user_id=None):
    p = _placeholder()
    conn = get_conn()
    c = conn.cursor()
    if _use_postgres():
        c.execute(
            f"""INSERT INTO mesocycles
               (user_id, name, start_date, weeks, deload_week, muscle_groups,
                split_template, split_days, split_order)
               VALUES ({p},{p},{p},{p},{p},{p},{p},{p},{p}) RETURNING id""",
            (user_id, name, str(start_date), weeks, deload_week, json.dumps(muscle_groups),
             split_template, json.dumps(split_days) if split_days else None,
             json.dumps(split_order) if split_order else None)
        )
        meso_id = c.fetchone()[0]
    else:
        c.execute(
            f"""INSERT INTO mesocycles
               (user_id, name, start_date, weeks, deload_week, muscle_groups,
                split_template, split_days, split_order)
               VALUES ({p},{p},{p},{p},{p},{p},{p},{p},{p})""",
            (user_id, name, str(start_date), weeks, deload_week, json.dumps(muscle_groups),
             split_template, json.dumps(split_days) if split_days else None,
             json.dumps(split_order) if split_order else None)
        )
        meso_id = c.lastrowid
    conn.commit()
    conn.close()
    return meso_id


def get_mesocycles(user_id=None):
    p = _placeholder()
    conn = get_conn()
    c = conn.cursor()
    if user_id:
        c.execute(f"SELECT * FROM mesocycles WHERE user_id={p} ORDER BY created_at DESC", (user_id,))
    else:
        c.execute("SELECT * FROM mesocycles ORDER BY created_at DESC")
    rows = _fetchall_as_dicts(c)
    conn.close()
    return [_decode_meso(r) for r in rows]


def get_mesocycle(meso_id):
    p = _placeholder()
    conn = get_conn()
    c = conn.cursor()
    c.execute(f"SELECT * FROM mesocycles WHERE id={p}", (meso_id,))
    row = _fetchone_as_dict(c)
    conn.close()
    return _decode_meso(row) if row else None


def update_mesocycle_status(meso_id, status):
    p = _placeholder()
    conn = get_conn()
    conn.cursor().execute(f"UPDATE mesocycles SET status={p} WHERE id={p}", (status, meso_id))
    conn.commit()
    conn.close()


def advance_mesocycle_week(meso_id: int, total_weeks: int) -> str:
    """
    Increments current_week by 1.
    - If new week > total_weeks: sets status='deload', returns 'deload'
    - If status was 'deload': sets status='completed', returns 'completed'
    - Otherwise returns 'advanced'
    """
    p = _placeholder()
    conn = get_conn()
    c = conn.cursor()
    c.execute(f"SELECT current_week, status FROM mesocycles WHERE id={p}", (meso_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        return "not_found"
    cw = row[0] or 1
    status = row[1]
    if status == "deload":
        c.execute(f"UPDATE mesocycles SET status='completed' WHERE id={p}", (meso_id,))
        conn.commit()
        conn.close()
        return "completed"
    new_week = cw + 1
    if new_week > total_weeks:
        c.execute(f"UPDATE mesocycles SET current_week={p}, status='deload' WHERE id={p}",
                  (new_week, meso_id))
        conn.commit()
        conn.close()
        return "deload"
    c.execute(f"UPDATE mesocycles SET current_week={p} WHERE id={p}", (new_week, meso_id))
    conn.commit()
    conn.close()
    return "advanced"


def delete_mesocycle(meso_id):
    p = _placeholder()
    conn = get_conn()
    c = conn.cursor()
    c.execute(f"SELECT id FROM workouts WHERE meso_id={p}", (meso_id,))
    wids = [r[0] for r in c.fetchall()]
    for wid in wids:
        c.execute(f"DELETE FROM sets WHERE workout_id={p}", (wid,))
        c.execute(f"DELETE FROM session_feedback WHERE workout_id={p}", (wid,))
    c.execute(f"DELETE FROM workouts WHERE meso_id={p}", (meso_id,))
    c.execute(f"DELETE FROM meso_muscle_config WHERE meso_id={p}", (meso_id,))
    c.execute(f"DELETE FROM mesocycles WHERE id={p}", (meso_id,))
    conn.commit()
    conn.close()


# ── Muscle Config ─────────────────────────────────────────────────────────────

def save_muscle_config(meso_id, muscle_group, start_sets, exercises):
    p = _placeholder()
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        f"DELETE FROM meso_muscle_config WHERE meso_id={p} AND muscle_group={p}",
        (meso_id, muscle_group)
    )
    c.execute(
        f"INSERT INTO meso_muscle_config (meso_id, muscle_group, start_sets, exercises) VALUES ({p},{p},{p},{p})",
        (meso_id, muscle_group, start_sets, json.dumps(exercises))
    )
    conn.commit()
    conn.close()


def get_muscle_configs(meso_id):
    p = _placeholder()
    conn = get_conn()
    c = conn.cursor()
    c.execute(f"SELECT * FROM meso_muscle_config WHERE meso_id={p}", (meso_id,))
    rows = _fetchall_as_dicts(c)
    conn.close()
    result = {}
    for r in rows:
        r["exercises"] = json.loads(r["exercises"])
        result[r["muscle_group"]] = r
    return result


# ── Workouts ──────────────────────────────────────────────────────────────────

def create_workout(meso_id, workout_date, week_number, notes="", day_name=None):
    p = _placeholder()
    conn = get_conn()
    c = conn.cursor()
    if _use_postgres():
        c.execute(
            f"INSERT INTO workouts (meso_id, date, week_number, notes, day_name) VALUES ({p},{p},{p},{p},{p}) RETURNING id",
            (meso_id, str(workout_date), week_number, notes, day_name)
        )
        wid = c.fetchone()[0]
    else:
        c.execute(
            f"INSERT INTO workouts (meso_id, date, week_number, notes, day_name) VALUES ({p},{p},{p},{p},{p})",
            (meso_id, str(workout_date), week_number, notes, day_name)
        )
        wid = c.lastrowid
    conn.commit()
    conn.close()
    return wid


def get_last_workout_per_day(meso_id: int) -> dict[str, str]:
    """Returns {day_name: last_date_string} for all days trained in this meso."""
    p = _placeholder()
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        f"SELECT day_name, MAX(date) as last_date FROM workouts "
        f"WHERE meso_id={p} AND day_name IS NOT NULL GROUP BY day_name",
        (meso_id,)
    )
    rows = _fetchall_as_dicts(c)
    conn.close()
    return {r["day_name"]: r["last_date"] for r in rows}


def get_workouts(meso_id=None):
    p = _placeholder()
    conn = get_conn()
    c = conn.cursor()
    if meso_id:
        c.execute(f"SELECT * FROM workouts WHERE meso_id={p} ORDER BY date DESC", (meso_id,))
    else:
        c.execute("SELECT * FROM workouts ORDER BY date DESC")
    rows = _fetchall_as_dicts(c)
    conn.close()
    return rows


def get_workout(workout_id):
    p = _placeholder()
    conn = get_conn()
    c = conn.cursor()
    c.execute(f"SELECT * FROM workouts WHERE id={p}", (workout_id,))
    row = _fetchone_as_dict(c)
    conn.close()
    return row


# ── Sets ──────────────────────────────────────────────────────────────────────

def save_set(workout_id, muscle_group, exercise, set_number, weight, reps, rpe,
             pump=None, soreness=None, sfr=None):
    p = _placeholder()
    conn = get_conn()
    conn.cursor().execute(
        f"""INSERT INTO sets
           (workout_id, muscle_group, exercise, set_number, weight, reps, rpe, pump, soreness, sfr)
           VALUES ({p},{p},{p},{p},{p},{p},{p},{p},{p},{p})""",
        (workout_id, muscle_group, exercise, set_number, weight, reps, rpe, pump, soreness, sfr)
    )
    conn.commit()
    conn.close()


def get_sets(workout_id):
    p = _placeholder()
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        f"SELECT * FROM sets WHERE workout_id={p} ORDER BY muscle_group, set_number", (workout_id,)
    )
    rows = _fetchall_as_dicts(c)
    conn.close()
    return rows


def get_all_sets_for_exercise(exercise_name):
    p = _placeholder()
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        f"""SELECT s.*, w.date, w.week_number FROM sets s
           JOIN workouts w ON s.workout_id = w.id
           WHERE s.exercise={p} ORDER BY w.date""",
        (exercise_name,)
    )
    rows = _fetchall_as_dicts(c)
    conn.close()
    return rows


def get_sets_per_muscle_per_week(meso_id):
    p = _placeholder()
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        f"""SELECT s.muscle_group, w.week_number, COUNT(*) as set_count
           FROM sets s JOIN workouts w ON s.workout_id = w.id
           WHERE w.meso_id={p}
           GROUP BY s.muscle_group, w.week_number
           ORDER BY w.week_number""",
        (meso_id,)
    )
    rows = _fetchall_as_dicts(c)
    conn.close()
    return rows


# ── Session Feedback ──────────────────────────────────────────────────────────

def save_feedback(workout_id, muscle_group, pump, soreness, performance, notes=""):
    p = _placeholder()
    conn = get_conn()
    c = conn.cursor()
    if _use_postgres():
        c.execute(
            f"""INSERT INTO session_feedback (workout_id, muscle_group, pump, soreness, performance, notes)
               VALUES ({p},{p},{p},{p},{p},{p})
               ON CONFLICT DO NOTHING""",
            (workout_id, muscle_group, pump, soreness, performance, notes)
        )
    else:
        c.execute(
            f"""INSERT OR IGNORE INTO session_feedback
               (workout_id, muscle_group, pump, soreness, performance, notes)
               VALUES ({p},{p},{p},{p},{p},{p})""",
            (workout_id, muscle_group, pump, soreness, performance, notes)
        )
    conn.commit()
    conn.close()


def get_feedback(workout_id):
    p = _placeholder()
    conn = get_conn()
    c = conn.cursor()
    c.execute(f"SELECT * FROM session_feedback WHERE workout_id={p}", (workout_id,))
    rows = _fetchall_as_dicts(c)
    conn.close()
    return rows


def get_all_feedback_for_meso(meso_id):
    p = _placeholder()
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        f"""SELECT f.*, w.date, w.week_number FROM session_feedback f
           JOIN workouts w ON f.workout_id = w.id
           WHERE w.meso_id={p} ORDER BY w.date""",
        (meso_id,)
    )
    rows = _fetchall_as_dicts(c)
    conn.close()
    return rows


# ── 10RM ─────────────────────────────────────────────────────────────────────

def save_ten_rm(exercise: str, weight: float, user_id=None):
    p = _placeholder()
    conn = get_conn()
    c = conn.cursor()
    # Use manual upsert — avoids dependency on UNIQUE constraint existing
    if user_id is not None:
        c.execute(f"SELECT id FROM ten_rm WHERE exercise={p} AND user_id={p}", (exercise, user_id))
    else:
        c.execute(f"SELECT id FROM ten_rm WHERE exercise={p} AND user_id IS NULL", (exercise,))
    row = c.fetchone()
    if row:
        c.execute(f"UPDATE ten_rm SET weight={p} WHERE id={p}", (weight, row[0]))
    else:
        c.execute(f"INSERT INTO ten_rm (user_id, exercise, weight) VALUES ({p},{p},{p})",
                  (user_id, exercise, weight))
    conn.commit()
    conn.close()


def get_ten_rm(exercise: str, user_id=None) -> float | None:
    p = _placeholder()
    conn = get_conn()
    c = conn.cursor()
    c.execute(f"SELECT weight FROM ten_rm WHERE exercise={p} AND user_id={p}", (exercise, user_id))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None


def get_last_sets_for_muscle(meso_id: int, muscle_group: str, day_name: str | None = None) -> list:
    """Returns sets from the most recent workout that trained this muscle group (same day if given)."""
    p = _placeholder()
    conn = get_conn()
    c = conn.cursor()
    if day_name:
        c.execute(
            f"""SELECT w.date, w.week_number, s.exercise, s.weight, s.reps, s.rpe
               FROM sets s JOIN workouts w ON s.workout_id = w.id
               WHERE w.meso_id={p} AND s.muscle_group={p} AND w.day_name={p}
               ORDER BY w.date DESC, w.id DESC LIMIT 20""",
            (meso_id, muscle_group, day_name)
        )
    else:
        c.execute(
            f"""SELECT w.date, w.week_number, s.exercise, s.weight, s.reps, s.rpe
               FROM sets s JOIN workouts w ON s.workout_id = w.id
               WHERE w.meso_id={p} AND s.muscle_group={p}
               ORDER BY w.date DESC, w.id DESC LIMIT 20""",
            (meso_id, muscle_group)
        )
    rows = _fetchall_as_dicts(c)
    conn.close()
    # Only keep sets from the single most recent workout date
    if not rows:
        return []
    latest_date = rows[0]["date"]
    return [r for r in rows if r["date"] == latest_date]


def get_last_feedback_per_muscle(meso_id: int) -> dict:
    """Returns the most recent feedback entry per muscle group for a mesocycle."""
    p = _placeholder()
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        f"""SELECT f.muscle_group, f.pump, f.soreness, f.performance, w.date, w.week_number
           FROM session_feedback f
           JOIN workouts w ON f.workout_id = w.id
           WHERE w.meso_id={p}
           ORDER BY w.date DESC, w.id DESC""",
        (meso_id,)
    )
    rows = _fetchall_as_dicts(c)
    conn.close()
    seen = {}
    for r in rows:
        mg = r["muscle_group"]
        if mg not in seen:
            seen[mg] = r
    return seen


def get_all_ten_rms(user_id=None) -> dict[str, float]:
    p = _placeholder()
    conn = get_conn()
    c = conn.cursor()
    if user_id:
        c.execute(f"SELECT exercise, weight FROM ten_rm WHERE user_id={p}", (user_id,))
    else:
        c.execute("SELECT exercise, weight FROM ten_rm")
    rows = c.fetchall()
    conn.close()
    return {r[0]: r[1] for r in rows}


def create_session(user_id: int, token: str):
    p = _placeholder()
    conn = get_conn()
    c = conn.cursor()
    c.execute(f"INSERT INTO sessions (token, user_id) VALUES ({p},{p})", (token, user_id))
    conn.commit()
    conn.close()


def get_user_by_token(token: str) -> dict | None:
    p = _placeholder()
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        f"SELECT u.id, u.username FROM users u JOIN sessions s ON u.id=s.user_id WHERE s.token={p}",
        (token,)
    )
    row = _fetchone_as_dict(c)
    conn.close()
    return row


def delete_session(token: str):
    p = _placeholder()
    conn = get_conn()
    c = conn.cursor()
    c.execute(f"DELETE FROM sessions WHERE token={p}", (token,))
    conn.commit()
    conn.close()


init_db()
