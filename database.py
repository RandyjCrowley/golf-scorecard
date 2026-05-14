"""SQLite helpers for the golf scorecard app."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Optional
from uuid import uuid4

BASE_DIR = Path(__file__).resolve().parent
DB_FILE = BASE_DIR / "golf_scorecard.db"
SCHEMA_FILE = BASE_DIR / "schema.sql"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def connection():
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    """Create tables from schema.sql if they do not exist."""
    sql = SCHEMA_FILE.read_text(encoding="utf-8")
    with connection() as conn:
        conn.executescript(sql)
    seed_demo_data_if_empty()


def _par_cycle(length: int) -> list[int]:
    """Repeating 3-4-5 pattern (same idea as the default scorecard UI)."""
    unit = (3, 4, 5)
    return [unit[i % 3] for i in range(length)]


def seed_demo_data_if_empty() -> None:
    """Insert sample rounds so a fresh clone has data to explore. Skips if any rows exist."""
    # (round_id, course_name, player_name, date, deltas vs par per hole; score = max(1, par + delta))
    demo: list[tuple[str, str, str, str, tuple[int, ...]]] = [
        (
            "11111111-1111-4111-8111-111111111101",
            "Sunrise Municipal",
            "Jamie Rivera",
            "2026-03-15",
            (
                1,
                0,
                0,
                -1,
                2,
                0,
                0,
                1,
                0,
                1,
                0,
                -1,
                0,
                0,
                1,
                0,
                0,
                1,
            ),
        ),
        (
            "22222222-2222-4222-8222-222222222202",
            "Lakeview Executive",
            "Sam Okonkwo",
            "2026-04-02",
            (0, 1, -1, 0, 2, 0, -1, 0, 1),
        ),
        (
            "33333333-3333-4333-8333-333333333303",
            "Harbor Links",
            "Jamie Rivera",
            "2026-05-01",
            (
                0,
                0,
                1,
                -1,
                0,
                2,
                -1,
                0,
                0,
                1,
                1,
                0,
                -1,
                0,
                0,
                1,
                -1,
                0,
            ),
        ),
        (
            "44444444-4444-4444-8444-444444444404",
            "Sunrise Municipal",
            "Morgan Chen",
            "2026-05-10",
            (1, 0, -1, 0, 0, 1, 2, -1, 0),
        ),
        (
            "55555555-5555-4555-8555-555555555505",
            "Cedar Ridge Golf Club",
            "Alex Kim",
            "2026-05-18",
            (
                0,
                1,
                -1,
                0,
                0,
                1,
                -1,
                0,
                1,
                0,
                0,
                -1,
                1,
                0,
                2,
                -1,
                0,
                0,
            ),
        ),
        (
            "66666666-6666-4666-8666-666666666606",
            "Oak Hill Par-3",
            "Taylor Brooks",
            "2026-05-22",
            (-1, 0, 1, 0, 0, -1, 0, 1, 0),
        ),
        (
            "77777777-7777-4777-8777-777777777707",
            "Harbor Links",
            "Sam Okonkwo",
            "2026-05-25",
            (
                1,
                1,
                0,
                -1,
                0,
                0,
                1,
                -1,
                0,
                2,
                0,
                -1,
                0,
                1,
                0,
                0,
                -1,
                1,
            ),
        ),
        (
            "88888888-8888-4888-8888-888888888808",
            "Lakeview Executive",
            "Morgan Chen",
            "2026-06-01",
            (0, -1, 0, 1, 0, 0, 1, -1, 2),
        ),
        (
            "99999999-9999-4999-8999-999999999909",
            "Pine Dunes",
            "Riley Patel",
            "2026-06-07",
            (
                -1,
                0,
                0,
                1,
                -1,
                2,
                0,
                0,
                1,
                0,
                -1,
                0,
                1,
                0,
                0,
                1,
                1,
                -1,
            ),
        ),
        (
            "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
            "Sunrise Municipal",
            "Taylor Brooks",
            "2026-06-12",
            (1, 0, 0, -1, 1, 0, 0, 1, -1),
        ),
    ]

    with connection() as conn:
        row = conn.execute("SELECT COUNT(*) AS n FROM rounds").fetchone()
        if row is not None and int(row["n"]) > 0:
            return

        for round_id, course_name, player_name, date, deltas in demo:
            pars = _par_cycle(len(deltas))
            conn.execute(
                """
                INSERT INTO rounds (id, course_name, player_name, date)
                VALUES (?, ?, ?, ?)
                """,
                (round_id, course_name, player_name, date),
            )
            for idx, par in enumerate(pars):
                delta = deltas[idx]
                score = max(1, par + delta)
                conn.execute(
                    """
                    INSERT INTO holes (round_id, hole_number, par, score)
                    VALUES (?, ?, ?, ?)
                    """,
                    (round_id, idx + 1, par, score),
                )


def _row_to_hole_dict(row: sqlite3.Row) -> dict:
    return {
        "holeNumber": row["hole_number"],
        "par": row["par"],
        "score": row["score"],
    }


def _compute_totals(holes: list[dict]) -> tuple[int, int, int]:
    total_par = sum(h["par"] for h in holes)
    total_score = sum(h["score"] for h in holes)
    return total_par, total_score, total_score - total_par


def _fetch_holes(conn: sqlite3.Connection, round_id: str) -> list[dict]:
    cur = conn.execute(
        """
        SELECT hole_number, par, score
        FROM holes
        WHERE round_id = ?
        ORDER BY hole_number
        """,
        (round_id,),
    )
    return [_row_to_hole_dict(row) for row in cur.fetchall()]


def _round_dict_from_id(
    conn: sqlite3.Connection,
    round_id: str,
) -> Optional[dict]:
    row = conn.execute(
        "SELECT id, course_name, player_name, date FROM rounds WHERE id = ?",
        (round_id,),
    ).fetchone()
    if row is None:
        return None
    holes = _fetch_holes(conn, round_id)
    total_par, total_score, rel = _compute_totals(holes)
    return {
        "id": row["id"],
        "courseName": row["course_name"],
        "playerName": row["player_name"],
        "date": row["date"],
        "holes": holes,
        "totalPar": total_par,
        "totalScore": total_score,
        "relativeToPar": rel,
    }


def create_round(
    course_name: str,
    player_name: str,
    date: str,
    holes: list[dict],
    round_id: Optional[str] = None,
) -> dict:
    rid = round_id or str(uuid4())
    with connection() as conn:
        conn.execute(
            """
            INSERT INTO rounds (id, course_name, player_name, date)
            VALUES (?, ?, ?, ?)
            """,
            (rid, course_name, player_name, date),
        )
        for h in holes:
            conn.execute(
                """
                INSERT INTO holes (round_id, hole_number, par, score)
                VALUES (?, ?, ?, ?)
                """,
                (rid, h["holeNumber"], h["par"], h["score"]),
            )
        result = _round_dict_from_id(conn, rid)
    assert result is not None
    return result


def _round_filters_sql(
    player_name: Optional[str],
    course_contains: Optional[str],
    date_from: Optional[str],
    date_to: Optional[str],
) -> tuple[str, list]:
    """Build WHERE clause fragment and parameters (parameterized only)."""
    parts: list[str] = []
    params: list = []
    if player_name:
        parts.append("LOWER(player_name) LIKE LOWER(?)")
        params.append(f"%{player_name}%")
    if course_contains:
        parts.append("LOWER(course_name) LIKE LOWER(?)")
        params.append(f"%{course_contains}%")
    if date_from:
        parts.append("date >= ?")
        params.append(date_from)
    if date_to:
        parts.append("date <= ?")
        params.append(date_to)
    if not parts:
        return "", []
    return " WHERE " + " AND ".join(parts), params


def count_rounds(
    player_name: Optional[str] = None,
    course_contains: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> int:
    where, params = _round_filters_sql(
        player_name, course_contains, date_from, date_to
    )
    with connection() as conn:
        row = conn.execute(
            f"SELECT COUNT(*) AS n FROM rounds{where}",
            params,
        ).fetchone()
        return int(row["n"]) if row else 0


def get_rounds(
    player_name: Optional[str] = None,
    course_contains: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: Optional[int] = None,
    offset: int = 0,
) -> list[dict]:
    where, params = _round_filters_sql(
        player_name, course_contains, date_from, date_to
    )
    query = f"SELECT id FROM rounds{where} ORDER BY date DESC, id DESC"
    qparams = list(params)
    if limit is not None:
        query += " LIMIT ? OFFSET ?"
        qparams.extend([limit, offset])
    elif offset:
        query += " LIMIT -1 OFFSET ?"
        qparams.append(offset)

    with connection() as conn:
        cur = conn.execute(query, qparams)
        ids = [row["id"] for row in cur.fetchall()]
        return [r for rid in ids if (r := _round_dict_from_id(conn, rid)) is not None]


def ping_db() -> bool:
    try:
        with connection() as conn:
            conn.execute("SELECT 1")
        return True
    except sqlite3.Error:
        return False


def get_stats_summary() -> dict:
    """Aggregates over completed rounds (one row per round in holes)."""
    with connection() as conn:
        round_count = int(
            conn.execute("SELECT COUNT(*) AS n FROM rounds").fetchone()["n"]
        )
        holes_row = conn.execute(
            "SELECT COUNT(*) AS n FROM holes",
        ).fetchone()
        total_holes = int(holes_row["n"]) if holes_row else 0

        avg_rel = conn.execute(
            """
            SELECT AVG(rel_to_par) AS avg_rel
            FROM (
                SELECT SUM(score) - SUM(par) AS rel_to_par
                FROM holes
                GROUP BY round_id
            )
            """
        ).fetchone()
        avg_score = conn.execute(
            """
            SELECT AVG(total_score) AS avg_score
            FROM (
                SELECT SUM(score) AS total_score
                FROM holes
                GROUP BY round_id
            )
            """
        ).fetchone()

    avg_rel_v = avg_rel["avg_rel"] if avg_rel else None
    avg_score_v = avg_score["avg_score"] if avg_score else None
    return {
        "roundCount": round_count,
        "averageRelativeToPar": float(avg_rel_v) if avg_rel_v is not None else None,
        "averageTotalScore": float(avg_score_v) if avg_score_v is not None else None,
        "totalHolesPlayed": total_holes,
    }


def get_player_leaderboard() -> list[dict]:
    with connection() as conn:
        cur = conn.execute(
            """
            SELECT
                r.player_name AS player_name,
                COUNT(DISTINCT r.id) AS rounds_played,
                AVG(rs.rel_to_par) AS avg_relative_to_par,
                MIN(r.date) AS first_round_date,
                MAX(r.date) AS last_round_date
            FROM rounds r
            JOIN (
                SELECT round_id, SUM(score) - SUM(par) AS rel_to_par
                FROM holes
                GROUP BY round_id
            ) AS rs ON rs.round_id = r.id
            GROUP BY r.player_name
            ORDER BY avg_relative_to_par ASC, rounds_played DESC
            """
        )
        rows = cur.fetchall()
    out: list[dict] = []
    for row in rows:
        avg = row["avg_relative_to_par"]
        out.append(
            {
                "playerName": row["player_name"],
                "roundsPlayed": int(row["rounds_played"]),
                "averageRelativeToPar": float(avg) if avg is not None else None,
                "firstRoundDate": row["first_round_date"],
                "lastRoundDate": row["last_round_date"],
            }
        )
    return out


def get_round_by_id(round_id: str) -> Optional[dict]:
    with connection() as conn:
        return _round_dict_from_id(conn, round_id)


def update_round(
    round_id: str,
    course_name: str,
    player_name: str,
    date: str,
    holes: list[dict],
) -> Optional[dict]:
    with connection() as conn:
        row = conn.execute(
            "SELECT id FROM rounds WHERE id = ?",
            (round_id,),
        ).fetchone()
        if row is None:
            return None
        conn.execute(
            """
            UPDATE rounds
            SET course_name = ?, player_name = ?, date = ?
            WHERE id = ?
            """,
            (course_name, player_name, date, round_id),
        )
        conn.execute("DELETE FROM holes WHERE round_id = ?", (round_id,))
        for h in holes:
            conn.execute(
                """
                INSERT INTO holes (round_id, hole_number, par, score)
                VALUES (?, ?, ?, ?)
                """,
                (round_id, h["holeNumber"], h["par"], h["score"]),
            )
        return _round_dict_from_id(conn, round_id)


def delete_round(round_id: str) -> bool:
    with connection() as conn:
        cur = conn.execute("DELETE FROM rounds WHERE id = ?", (round_id,))
        return cur.rowcount > 0
