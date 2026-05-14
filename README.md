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

## Porting to Go (Echo + SQLite)

The API and `public/` frontend can be recreated in Go while keeping **the same paths and JSON field names** (`courseName`, `holeNumber`, etc.) so the browser code stays as-is.

### What to do (high-level checklist)

1. **`go mod init`** and add dependencies, for example:
   - [Echo](https://echo.labstack.com/) — HTTP server and routing.
   - [`database/sql`](https://pkg.go.dev/database/sql) — database API (stdlib).
   - A SQLite driver (see [SQLite drivers](#sqlite-drivers) below).
2. **Copy `schema.sql`** (and optional seed logic) into your Go module; run `CREATE TABLE` on startup, same as `init_db()`.
3. **Open the DB once** at startup (`sql.Open`) and pass a `*sql.DB` into handlers (or a small repository type), using **only** `?` placeholders and `db.Query`, `QueryRow`, `Exec` — never `fmt.Sprintf` for user input in SQL.
4. **On every new connection** SQLite needs foreign keys: `_fk=1` in the DSN (see below) or `db.Exec("PRAGMA foreign_keys = ON")` after open (some drivers apply PRAGMA per-connection; verify with your driver docs).
5. **Echo routes** (order matters: static and fixed paths before `:id`):
   - `GET /` → serve `index.html` (e.g. `echo.WrapHandler` + `http.FileServer`, or `c.File` with path to `public/index.html`).
   - `GET /static/*` → `echo.Static("/static", "public")` (or `embed.FS` in production).
   - Mount `/api/...` JSON handlers to mirror this README’s [API routes](#api-routes).
6. **Structs** with `json:"courseName"` tags matching FastAPI/Pydantic; validate request bodies (e.g. 9 or 18 holes) in Go and return `400`/`422`-style errors as JSON if you want parity with FastAPI.
7. **Computed fields**: compute `totalPar`, `totalScore`, `relativeToPar` when building the response struct (same as Python).

### Echo tips

- Guide: [Echo — Quick start](https://echo.labstack.com/docs/quick-start) and [Static files](https://echo.labstack.com/docs/cookbook/static-files).
- **JSON**: `c.Bind(&body)` for incoming JSON; `return c.JSON(http.StatusOK, round)` for responses.
- **Path params**: `c.Param("id")` for round IDs; register `GET /api/rounds/:id` only after routes like `/api/rounds/page` and `/api/rounds/count` so literal segments are not swallowed by `:id`.
- **Middleware**: [Logger](https://echo.labstack.com/middleware/logger) and [Recover](https://echo.labstack.com/middleware/recover) are useful early; enable Gzip only if you understand buffering implications for streaming.

### SQLite drivers

| Driver | Notes |
|--------|--------|
| [`modernc.org/sqlite`](https://pkg.go.dev/modernc.org/sqlite) | Pure Go, **no CGO**; easy cross-compiles. DSN example: `file:golf_scorecard.db?_fk=1`. |
| [`github.com/mattn/go-sqlite3`](https://github.com/mattn/go-sqlite3) | CGO + system SQLite; common in older tutorials; requires a C toolchain on your machine. |

Docs: [Go database/sql tutorial](https://go.dev/doc/database/querying), [SQLite PRAGMA foreign_keys](https://sqlite.org/pragma.html#pragma_foreign_keys).

### Troubleshooting

- **`database is locked`**: Use a single shared `*sql.DB`, set [`db.SetMaxOpenConns(1)`](https://pkg.go.dev/database/sql#DB.SetMaxOpenConns) for SQLite, and avoid long-lived transactions in dev.
- **Foreign key deletes don’t cascade**: Confirm `_fk=1` or `PRAGMA foreign_keys=ON` on the **same** connection that runs deletes; SQLite ignores FKs if the pragma is off.
- **404 on `/static/...`**: Check `echo.Static` root matches your repo’s `public` folder and that paths in HTML are `/static/...` (leading slash).
- **Empty JSON or wrong field names**: Struct fields must be exported (capitalized) and tagged `json:"courseName"` to match the frontend.
- **CGO build fails** (`go-sqlite3`): Switch to `modernc.org/sqlite` or install Xcode CLI tools / gcc on Linux; see [Go CGO wiki](https://go.dev/wiki/cgo).
- **`embed.FS` paths**: Use forward slashes (e.g. `//go:embed public/*`) and open `index.html` as `public/index.html` inside the embed — see [`embed` package](https://pkg.go.dev/embed).

### Documentation sites

| Topic | Where to read |
|--------|----------------|
| Echo | [https://echo.labstack.com/docs](https://echo.labstack.com/docs) |
| Standard library (`database/sql`, `net/http`, `embed`) | [https://pkg.go.dev/std](https://pkg.go.dev/std) |
| Go modules & commands | [https://go.dev/doc/modules](https://go.dev/doc/modules) |
| Effective Go | [https://go.dev/doc/effective_go](https://go.dev/doc/effective_go) |
| SQLite language & pragmas | [https://sqlite.org/docs.html](https://sqlite.org/docs.html) |

The frontend can stay unchanged if you keep the same URLs and JSON shape.
