import sqlite3
import json
from datetime import datetime
from config import DATABASE_PATH


def get_db():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS analyses (
            id TEXT PRIMARY KEY,
            filename TEXT NOT NULL,
            original_filename TEXT NOT NULL,
            file_size INTEGER,
            duration_seconds REAL,
            status TEXT DEFAULT 'processing',
            -- 6-dimension scores
            overall_score INTEGER,
            opening_hook_score INTEGER,
            script_structure_score INTEGER,
            emotional_curve_score INTEGER,
            interaction_guide_score INTEGER,
            data_prediction_score INTEGER,
            content_formula_score INTEGER,
            -- Full analysis result as JSON
            result_json TEXT,
            -- Metadata
            video_url_stepfile TEXT,
            transcript_text TEXT,
            viral_style TEXT,
            summary TEXT,
            error_message TEXT,
            created_at TEXT NOT NULL,
            completed_at TEXT,
            processing_time_seconds REAL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS comparison_groups (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            analysis_ids TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


def save_analysis(
    analysis_id: str,
    filename: str,
    original_filename: str,
    file_size: int,
    duration_seconds: float = 0,
):
    conn = get_db()
    conn.execute(
        """INSERT INTO analyses (id, filename, original_filename, file_size, duration_seconds, created_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (analysis_id, filename, original_filename, file_size, duration_seconds,
         datetime.now().isoformat())
    )
    conn.commit()
    conn.close()


def update_analysis_result(
    analysis_id: str,
    overall_score: int,
    opening_hook_score: int,
    script_structure_score: int,
    emotional_curve_score: int,
    interaction_guide_score: int,
    data_prediction_score: int,
    content_formula_score: int,
    result_json: dict,
    transcript_text: str,
    viral_style: str,
    summary: str,
    processing_time: float,
):
    conn = get_db()
    conn.execute(
        """UPDATE analyses SET
            status = 'completed',
            overall_score = ?,
            opening_hook_score = ?,
            script_structure_score = ?,
            emotional_curve_score = ?,
            interaction_guide_score = ?,
            data_prediction_score = ?,
            content_formula_score = ?,
            result_json = ?,
            transcript_text = ?,
            viral_style = ?,
            summary = ?,
            completed_at = ?,
            processing_time_seconds = ?
           WHERE id = ?""",
        (
            overall_score,
            opening_hook_score,
            script_structure_score,
            emotional_curve_score,
            interaction_guide_score,
            data_prediction_score,
            content_formula_score,
            json.dumps(result_json, ensure_ascii=False),
            transcript_text,
            viral_style,
            summary,
            datetime.now().isoformat(),
            processing_time,
            analysis_id,
        )
    )
    conn.commit()
    conn.close()


def update_analysis_error(analysis_id: str, error_message: str):
    conn = get_db()
    conn.execute(
        "UPDATE analyses SET status = 'error', error_message = ? WHERE id = ?",
        (error_message, analysis_id)
    )
    conn.commit()
    conn.close()


def update_analysis_status(analysis_id: str, status: str):
    conn = get_db()
    conn.execute(
        "UPDATE analyses SET status = ? WHERE id = ?",
        (status, analysis_id)
    )
    conn.commit()
    conn.close()


def update_video_stepfile(analysis_id: str, stepfile_url: str):
    conn = get_db()
    conn.execute(
        "UPDATE analyses SET video_url_stepfile = ? WHERE id = ?",
        (stepfile_url, analysis_id)
    )
    conn.commit()
    conn.close()


def get_analysis(analysis_id: str) -> dict:
    conn = get_db()
    row = conn.execute("SELECT * FROM analyses WHERE id = ?", (analysis_id,)).fetchone()
    conn.close()
    if row:
        d = dict(row)
        if d.get("result_json"):
            d["result_json"] = json.loads(d["result_json"])
        return d
    return None


def list_analyses(limit: int = 50, offset: int = 0) -> list:
    conn = get_db()
    rows = conn.execute(
        """SELECT id, original_filename, file_size, duration_seconds, status,
                  overall_score, viral_style, summary, created_at, completed_at,
                  processing_time_seconds
           FROM analyses
           ORDER BY created_at DESC
           LIMIT ? OFFSET ?""",
        (limit, offset)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_analysis(analysis_id: str):
    conn = get_db()
    conn.execute("DELETE FROM analyses WHERE id = ?", (analysis_id,))
    conn.commit()
    conn.close()


def get_completed_analyses() -> list:
    conn = get_db()
    rows = conn.execute(
        """SELECT id, original_filename, overall_score,
                  opening_hook_score, script_structure_score, emotional_curve_score,
                  interaction_guide_score, data_prediction_score, content_formula_score,
                  result_json, viral_style, created_at
           FROM analyses
           WHERE status = 'completed'
           ORDER BY created_at DESC"""
    ).fetchall()
    conn.close()
    results = []
    for row in rows:
        d = dict(row)
        if d.get("result_json"):
            d["result_json"] = json.loads(d["result_json"])
        results.append(d)
    return results


# Initialize database on import
init_db()
