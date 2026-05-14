-- Golf scorecard schema (SQLite)
-- Foreign keys require PRAGMA foreign_keys = ON in the application.

CREATE TABLE IF NOT EXISTS rounds (
    id TEXT PRIMARY KEY,
    course_name TEXT NOT NULL,
    player_name TEXT NOT NULL,
    date TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS holes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    round_id TEXT NOT NULL,
    hole_number INTEGER NOT NULL,
    par INTEGER NOT NULL,
    score INTEGER NOT NULL,
    FOREIGN KEY (round_id) REFERENCES rounds(id) ON DELETE CASCADE
);
