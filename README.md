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

## Porting to Go (Echo + SQLite) — if you’re new to Go

Go (often called **Golang**) is a **compiled** language: you write `.go` files, run `go build` or `go run`, and get a single binary (like a `.exe` on Windows). There is no separate interpreter like CPython.

You can rebuild **this same app** in Go: keep `public/` and the **URLs + JSON shapes** the same, and the browser will not care that the server is Go instead of Python.

### Install Go and sanity-check

1. Download and install from the official guide: [https://go.dev/doc/install](https://go.dev/doc/install).
2. Open a terminal and run:

```bash
go version
```

You should see a version line (for example `go1.22` or newer). If the command is not found, fix your `PATH` using the instructions for your OS on that same page.

### Mindset: Python vs Go (very short)

| Idea | Python (this project) | Go |
|------|------------------------|-----|
| Project metadata | `requirements.txt` | `go.mod` (created with `go mod init`) |
| Entry point | `uvicorn main:app` | `package main` + `func main()` in a file like `main.go`; run with `go run .` |
| HTTP framework | FastAPI | [Echo](https://echo.labstack.com/) (or others; here we assume Echo) |
| Request/response shapes | Pydantic models | `struct` types with struct tags such as `` `json:"courseName"` `` on fields |
| Add a dependency | `pip install …` | `go get example.com/module@version` (writes into `go.mod`) |
| Database | `sqlite3` module | `database/sql` + a SQLite **driver** package |

**Exported names:** In Go, a type or field that must be visible outside its package must **start with a capital letter** (`CourseName`, `Round`). The JSON field name sent on the wire can still be camelCase using a struct tag:

```go
CourseName string `json:"courseName"`
```

### Vocabulary you’ll see in tutorials

- **Package:** A folder of `.go` files that belong together. `package main` means “build a program.”
- **Module:** Your whole project + its dependency list (`go.mod`).
- **Standard library:** Built-in packages like `database/sql`, `net/http`, `embed` — no install step.

### What you will actually build (order that works well)

1. **Start a module** in a new folder (keep your `public/` and `schema.sql` next to your Go files or copy them in):

```bash
mkdir golf-scorecard-go && cd golf-scorecard-go
go mod init example.com/golf-scorecard
```

(Replace `example.com/golf-scorecard` with any module path you like; it only needs to be unique-ish on your machine.)

2. **Add Echo and SQLite support** (exact commands may vary slightly by version):

```bash
go get github.com/labstack/echo/v4
go get modernc.org/sqlite
```

`modernc.org/sqlite` is **pure Go** (no C compiler). That keeps “first project” setups simple. You can read *why* that matters in [SQLite drivers](#sqlite-drivers-new-to-go) below.

3. **Apply `schema.sql` on startup** the same way `database.init_db()` does: read the file, `db.Exec` each statement (or use `Execute` in a transaction). Optionally port `seed_demo_data_if_empty()` so an empty DB gets the ten demo rounds.

4. **Open the database once** when the program starts (`sql.Open`), put the `*sql.DB` in a variable, and reuse it in your HTTP handlers (similar to a single connection pool in other stacks). **Never** build SQL by gluing strings with user input — always use `?` placeholders and arguments, like Python’s parameterized queries.

5. **Turn on foreign keys for SQLite.** Easiest with modernc: use a DSN like `file:golf_scorecard.db?_fk=1`. If foreign deletes “don’t work,” this is usually the reason.

6. **Wire Echo routes** so they match this README’s HTTP API. **Important:** register **fixed paths** like `/api/rounds/page` and `/api/rounds/count` **before** `/api/rounds/:id`. If `:id` comes first, Echo may treat the word `page` as an id.

7. **Serve the static UI:** `GET /` → `public/index.html`; `/static/*` → files under `public/`. Echo’s docs show `Static` and serving a single file — see [Echo — Static content](https://echo.labstack.com/docs/cookbook/static-files).

8. **JSON:** For a request body, define a struct with tags and use `c.Bind(&body)`. For responses, `return c.JSON(http.StatusOK, value)`. Compute `totalPar`, `totalScore`, `relativeToPar` in code like you do in Python.

### Echo tips (still beginner-level)

- Echo is an **HTTP router + helpers**: it listens on a port, matches paths, runs your functions, and helps with JSON.
- Official starting point: [Echo — Quick start](https://echo.labstack.com/docs/quick-start).
- Useful middleware: [Logger](https://echo.labstack.com/middleware/logger) (see each request) and [Recover](https://echo.labstack.com/middleware/recover) (avoid crashing the whole server on a panic).

### SQLite drivers (new to Go)

Go’s `database/sql` does not speak SQLite by itself — you import **a driver** and usually register it with a blank import:

```go
import (
  "database/sql"
  _ "modernc.org/sqlite"
)
```

Then open with a driver name such as `sqlite` (check the driver’s README for the exact string).

| Driver | Plain-English description |
|--------|----------------------------|
| [`modernc.org/sqlite`](https://pkg.go.dev/modernc.org/sqlite) | Pure Go — **recommended for beginners.** No Xcode/gcc “CGO” setup. DSN example: `file:golf_scorecard.db?_fk=1`. |
| [`github.com/mattn/go-sqlite3`](https://github.com/mattn/go-sqlite3) | Uses C code under the hood (**CGO**). Very common in older examples, but your first build can fail if no C toolchain is installed. |

More background: [Go — Accessing databases](https://go.dev/doc/database/querying), [SQLite — foreign_keys pragma](https://sqlite.org/pragma.html#pragma_foreign_keys).

### Troubleshooting (what the message usually means)

- **`go: command not found`:** Go is not installed or not on your `PATH`. Revisit [https://go.dev/doc/install](https://go.dev/doc/install).
- **`cannot find package` / tidy errors:** Run `go mod tidy` from the folder that contains `go.mod`.
- **`database is locked` (SQLite):** Often “too many writers” or open transactions. For small apps, try [`db.SetMaxOpenConns(1)`](https://pkg.go.dev/database/sql#DB.SetMaxOpenConns) and one shared `*sql.DB`.
- **Deletes don’t remove child holes:** Foreign keys are off. Fix the DSN (`_fk=1`) or run `PRAGMA foreign_keys = ON` per connection (driver-dependent).
- **404 on CSS/JS:** Wrong folder in `echo.Static`, or HTML paths missing the leading `/static/`.
- **JSON fields missing or always empty:** Struct fields used for JSON must be **exported** (capitalized) **and** usually have `` `json:"courseName"` `` tags matching the frontend.
- **Build errors mentioning `cgo`:** You’re on `go-sqlite3` without a C compiler — switch to `modernc.org/sqlite` or install a toolchain; see [Go — CGO](https://go.dev/wiki/cgo).
- **`embed` / “file not found” in binary:** Paths in `//go:embed` use forward slashes; read [embed](https://pkg.go.dev/embed) slowly once — it trips up many newcomers.

### Where to learn Go before you port the whole app

Do these in order; they assume **no prior Go**:

1. [A Tour of Go](https://go.dev/tour/welcome/1) — interactive basics (syntax, types, loops, pointers).
2. [Go basics (Go.dev)](https://go.dev/learn/) — curated links.
3. [Effective Go](https://go.dev/doc/effective_go) — style and idioms (read in small chunks).
4. [Echo documentation](https://echo.labstack.com/docs) — your HTTP layer.
5. [Package documentation (`pkg.go.dev/std`)](https://pkg.go.dev/std) — look up `database/sql`, `embed`, `net/http`.

Reference: [SQLite documentation](https://sqlite.org/docs.html).

If you keep routes and JSON identical to this Python app, you can port the **server** line by line in spirit: **schema → DB open → HTTP routes → JSON structs**. The `public/` folder can stay the same.

