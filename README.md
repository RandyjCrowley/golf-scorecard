# Golf Scorecard (Python + FastAPI + SQLite)

A small, beginner-friendly golf scorecard app: a FastAPI backend with SQLite storage and a plain HTML/CSS/JavaScript frontend (no React, no auth, no external database server).

## What it does

- Record 9- or 18-hole rounds with course name, player, date, par, and score per hole.
- List saved rounds with totals: total par, total score, and score relative to par.
- Edit or delete rounds from the browser.

## Setup

### 1. Create a virtual environment

From this project folder:

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the server

```bash
uvicorn main:app --reload
```

If `uvicorn` is not on your PATH (common with some Python installs), use:

```bash
python3 -m uvicorn main:app --reload
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000).

On first start, the app creates `golf_scorecard.db` and tables from `schema.sql` if they are missing. If the `rounds` table is empty, **ten sample rounds** are inserted automatically (see `seed_demo_data_if_empty()` in `database.py`) so you can try the UI and API immediately.

To load demo data again later, delete `golf_scorecard.db` and restart the server.

## API routes

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Serves the scorecard page (`public/index.html`). |
| `GET` | `/static/...` | Static assets (CSS, JS). |
| `GET` | `/api/rounds` | List all rounds (with holes and computed totals). |
| `POST` | `/api/rounds` | Create a round (server generates UUID `id`). |
| `GET` | `/api/rounds/{round_id}` | Get one round; `404` if not found. |
| `PUT` | `/api/rounds/{round_id}` | Replace round metadata and holes; `404` if not found. |
| `DELETE` | `/api/rounds/{round_id}` | Delete round and its holes; `404` if not found. |

## Example JSON request body (`POST /api/rounds` or `PUT /api/rounds/{id}`)

```json
{
  "courseName": "Municipal Nine",
  "playerName": "Alex",
  "date": "2026-05-14",
  "holes": [
    { "holeNumber": 1, "par": 4, "score": 5 },
    { "holeNumber": 2, "par": 3, "score": 3 },
    { "holeNumber": 3, "par": 5, "score": 6 }
  ]
}
```

Response rounds include: `id`, `courseName`, `playerName`, `date`, `holes`, `totalPar`, `totalScore`, `relativeToPar`.

## Project layout

- `main.py` — FastAPI app, static mount, routes, Pydantic models.
- `database.py` — SQLite connection, `init_db()`, and data access functions.
- `schema.sql` — `CREATE TABLE` definitions.
- `golf_scorecard.db` — SQLite database file (created/updated at runtime).
- `public/` — `index.html`, `style.css`, `script.js`.

## Notes for a future Go port

This project maps cleanly to a Go rewrite:

- **HTTP**: [`net/http`](https://pkg.go.dev/net/http) or [chi](https://github.com/go-chi/chi)/[Echo](https://echo.labstack.com/) for routing; static files via `http.FileServer` or embedded `embed.FS`.
- **Data**: [`database/sql`](https://pkg.go.dev/database/sql) with a modern SQLite driver (e.g. `modernc.org/sqlite` or `github.com/mattn/go-sqlite3`)—still parameterized queries, no string interpolation for SQL values.
- **JSON**: Struct tags `json:"courseName"` mirror the Pydantic field names; compute `totalPar`, `totalScore`, and `relativeToPar` in Go when assembling responses.
- **Schema**: The same SQL works in SQLite for Go; keep `PRAGMA foreign_keys = ON` per connection.

The frontend can stay unchanged if you keep the same URLs and JSON shape.
