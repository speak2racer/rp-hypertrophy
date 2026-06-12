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
    CREATE TABLE IF NOT EXISTS mesocycles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
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
"""

_SCHEMA_POSTGRES = """
    CREATE TABLE IF NOT EXISTS mesocycles (
        id SERIAL PRIMARY KEY,
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
"""


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
    conn.close()


# ── Mesocycles ────────────────────────────────────────────────────────────────

def _decode_meso(d: dict) -> dict:
    d["muscle_groups"] = json.loads(d["muscle_groups"])
    d["split_days"] = json.loads(d["split_days"]) if d.get("split_days") else {}
    d["split_order"] = json.loads(d["split_order"]) if d.get("split_order") else []
    return d


def create_mesocycle(name, start_date, weeks, deload_week, muscle_groups,
                     split_template=None, split_days=None, split_order=None):
    p = _placeholder()
    conn = get_conn()
    c = conn.cursor()
    if _use_postgres():
        c.execute(
            f"""INSERT INTO mesocycles
               (name, start_date, weeks, deload_week, muscle_groups,
                split_template, split_days, split_order)
               VALUES ({p},{p},{p},{p},{p},{p},{p},{p}) RETURNING id""",
            (name, str(start_date), weeks, deload_week, json.dumps(muscle_groups),
             split_template, json.dumps(split_days) if split_days else None,
             json.dumps(split_order) if split_order else None)
        )
        meso_id = c.fetchone()[0]
    else:
        c.execute(
            f"""INSERT INTO mesocycles
               (name, start_date, weeks, deload_week, muscle_groups,
                split_template, split_days, split_order)
               VALUES ({p},{p},{p},{p},{p},{p},{p},{p})""",
            (name, str(start_date), weeks, deload_week, json.dumps(muscle_groups),
             split_template, json.dumps(split_days) if split_days else None,
             json.dumps(split_order) if split_order else None)
        )
        meso_id = c.lastrowid
    conn.commit()
    conn.close()
    return meso_id


def get_mesocycles():
    conn = get_conn()
    c = conn.cursor()
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

def create_workout(meso_id, workout_date, week_number, notes=""):
    p = _placeholder()
    conn = get_conn()
    c = conn.cursor()
    if _use_postgres():
        c.execute(
            f"INSERT INTO workouts (meso_id, date, week_number, notes) VALUES ({p},{p},{p},{p}) RETURNING id",
            (meso_id, str(workout_date), week_number, notes)
        )
        wid = c.fetchone()[0]
    else:
        c.execute(
            f"INSERT INTO workouts (meso_id, date, week_number, notes) VALUES ({p},{p},{p},{p})",
            (meso_id, str(workout_date), week_number, notes)
        )
        wid = c.lastrowid
    conn.commit()
    conn.close()
    return wid


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


init_db()
