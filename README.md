# To-Do List CRUD API

A simple To-Do List REST API built with **Python + FastAPI**, backed by a **PostgreSQL** database running in **Docker**. It supports creating, reading, updating and deleting tasks, plus filtering, search, computed statistics and a reset endpoint for testing.

The whole stack — the API and its database — starts with a single command. Tasks are stored in Postgres, so **data survives a server restart, a container restart, or the whole stack being torn down and brought back up.**

This is the third storage engine this same repo has used: an in-memory list, then a SQLite file, now a containerized Postgres server. The API on top never changed.

## Requirements

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (or Podman) — no Python, no `uv`, no Postgres install needed to just run it.

(To run the app outside Docker for local development, see [Running without Docker](#running-without-docker) below — that path does need Python 3.13+ and `uv`.)

## Run everything with one command

```powershell
git clone <this-repo-url>
cd to-do-list
cp .env.example .env
docker compose up
```

That's it — Docker builds the API image, pulls Postgres, starts both, creates the `tasks` table on first boot, and seeds three example tasks. The API is available at `http://localhost:8000`.

- Interactive docs (Swagger UI): http://localhost:8000/docs
- Alternative docs (ReDoc): http://localhost:8000/redoc

Stop everything with `docker compose down` (add `-v` if you also want to wipe the database volume and start completely fresh).

## Configuration

The app reads its database connection string from a single environment variable, provided via `.env` (git-ignored — never commit real secrets):

| Variable | Meaning | Example |
|---|---|---|
| `DATABASE_URL` | Postgres connection string: `postgres://user:password@host:port/dbname` | `postgres://postgres:dev@db:5432/tasks` |

Copy `.env.example` to `.env` to get a working default — the password here (`dev`) is a throwaway local development credential, not a real secret. `.env` is listed in `.gitignore` and is never committed.

Note the host differs depending on how you run things: inside `docker compose`, the API reaches Postgres by the **service name** `db` (Docker Compose's internal DNS); if you run the API directly on your machine against a hand-started container, it's `localhost` instead (see below).

## Database

### Why Postgres in Docker

- **A real database server**, not a file. PostgreSQL runs as its own program, the same engine behind a large share of real backends (FlyRank included) — the right choice once more than one process or user needs to read/write concurrently, unlike the SQLite file used in the previous version of this repo.
- **No local install.** You never install Postgres on your machine — Docker runs the official `postgres` image, an isolated, throwaway, disposable copy of it.
- **A volume, not the container, keeps the data.** The named volume `taskdata` is mounted at Postgres's data directory. The container itself can be deleted and recreated at will; the rows live in the volume and survive that.

### Where the database lives

| | |
|---|---|
| Engine | PostgreSQL 16, running in the `db` service (pinned to `postgres:16` — `postgres:latest` is now major version 18, which uses an incompatible data-directory layout for this same setup) |
| Data | Named Docker volume `taskdata`, mounted at `/var/lib/postgresql/data` inside the container |
| Created by | `app/db.py`, automatically on first connection |
| Tracked in git? | No — the volume lives in Docker's own storage, not the repo |

### Schema

One table, created with `CREATE TABLE IF NOT EXISTS` on startup:

```sql
CREATE TABLE tasks (
    id    SERIAL PRIMARY KEY,       -- auto-incrementing, assigned by Postgres
    title TEXT NOT NULL,
    done  BOOLEAN NOT NULL DEFAULT FALSE
)
```

On first run only, three example tasks are seeded. The check is a row count (`SELECT COUNT(*) FROM tasks`), not a file-existence check, so restarting the server (or the whole stack) never duplicates them.

### Queries

All SQL runs in `app/tasks.py`, and every user-supplied value is passed as a `%s` **parameterized query** placeholder rather than formatted into the query string:

```python
db.execute('SELECT * FROM tasks WHERE id = %s', (id,))
```

The value is bound separately from the query text by the `psycopg` driver, so user input can never be interpreted as SQL.

## Endpoints

| Method | Path | Description | Success | Errors |
|--------|------|-------------|---------|--------|
| GET | `/` | API description | 200 | — |
| GET | `/health` | Health check | 200 | — |
| GET | `/tasks` | List tasks. Optional query params: `done` (bool), `search` (substring in title, case-insensitive) | 200 | 400 (invalid query) |
| GET | `/tasks/{id}` | Get one task by id | 200 | 404 |
| GET | `/stats` | Computed statistics: `{"total", "done", "open"}` | 200 | — |
| POST | `/tasks` | Create a task. Body: `{"title": "...", "done": false}` (`done` optional) | 201 | 400 (invalid/empty body) |
| POST | `/reset` | Reset the store to its initial state (3 example tasks) | 204 (no body) | — |
| PUT | `/tasks/{id}` | Update `title` and/or `done` | 200 | 400, 404 |
| DELETE | `/tasks/{id}` | Delete a task | 204 (no body) | 404 |

All errors are returned as JSON with the shape `{"error": "<message>"}`. These endpoints, their request/response shapes and status codes are unchanged from the in-memory (A1) and SQLite (A2) versions of this API — only the storage engine underneath changed.

## Examples

### Create a task → 201

```powershell
curl.exe -i -X POST http://localhost:8000/tasks -H "Content-Type: application/json" --% -d "{\"title\":\"Buy milk\"}"
```

```
HTTP/1.1 201 Created
content-type: application/json

{"title":"Buy milk","done":false,"id":4}
```

### Task not found → 404

```powershell
curl.exe -i http://localhost:8000/tasks/999
```

```
HTTP/1.1 404 Not Found
content-type: application/json

{"error":"Task 999 not found"}
```

### Filter and search

```powershell
curl.exe -i "http://localhost:8000/tasks?done=false&search=milk"
```

```
HTTP/1.1 200 OK
content-type: application/json

[{"title":"Buy Milk","done":false,"id":1}]
```

### Persistence across the whole stack

The point of moving to a containerized database, in three commands:

```powershell
curl.exe -X POST http://localhost:8000/tasks -H "Content-Type: application/json" --% -d "{\"title\":\"Survives a restart\"}"
docker compose down
docker compose up -d
curl.exe -i http://localhost:8000/tasks
```

The task is still there after the entire stack — API and database — was torn down and started again. That's the volume, not the container, keeping the data alive: `docker compose down` removes the containers, but `taskdata` is untouched. (Only `docker compose down -v` would also delete the volume, and with it, the data.)

## Running without Docker

For local development without containers, you still need a Postgres server reachable somewhere. The simplest option is running just the database in a container and the API directly on your machine:

```powershell
docker run --name taskdb -e POSTGRES_PASSWORD=dev -e POSTGRES_DB=tasks -p 5432:5432 -v taskdata:/var/lib/postgresql/data -d postgres:16

uv sync                              # creates .venv and installs all dependencies from uv.lock
uv run fastapi dev app/main.py       # DATABASE_URL in .env should point at localhost:5432 in this mode
```

## Swagger UI

FastAPI automatically generates interactive documentation at `/docs`, where every endpoint can be tried from the browser:

![Swagger UI](docs/swagger.png)

## The database in Postgres

Confirming the seeded rows live in Postgres itself, via `psql` inside the `db` container:

```powershell
docker compose exec db psql -U postgres -d tasks -c "SELECT * FROM tasks;"
```

![tasks table in Postgres](docs/postgres-data.png)
