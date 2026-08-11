# To-Do List CRUD API

A simple To-Do List REST API built with **Python + FastAPI**, backed by a **PostgreSQL** database running in **Docker**, with user authentication handled by **Supabase Auth**. It supports creating, reading, updating and deleting tasks, plus filtering, search, computed statistics and a reset endpoint for testing — and now sign up, log in, log out, and routes that only answer to authenticated users.

The whole stack — the API and its database — starts with a single command. Tasks are stored in Postgres, so **data survives a server restart, a container restart, or the whole stack being torn down and brought back up.**

This is the third storage engine this same repo has used: an in-memory list, then a SQLite file, now a containerized Postgres server. The API on top never changed.

## Requirements

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (or Podman) — no Python, no `uv`, no Postgres install needed to just run it.
- A free [Supabase](https://supabase.com) project, for authentication. No credit card required.

(To run the app outside Docker for local development, see [Running without Docker](#running-without-docker) below — that path does need Python 3.13+ and `uv`.)

## Run everything with one command

```bash
git clone <this-repo-url>
cd to-do-list
cp .env.example .env     # then fill in your Supabase URL and anon key
docker compose up
```

That's it — Docker builds the API image, pulls Postgres, starts both, creates the `tasks` table on first boot, and seeds three example tasks. The API is available at `http://localhost:8000`.

- Interactive docs (Swagger UI): http://localhost:8000/docs
- Alternative docs (ReDoc): http://localhost:8000/redoc

Stop everything with `docker compose down` (add `-v` if you also want to wipe the database volume and start completely fresh).

Note that `docker compose up` reuses the existing image. After changing the code, rebuild with `docker compose up --build`.

## Configuration

The app reads its configuration from environment variables, provided via `.env` (git-ignored — never commit real secrets):

| Variable | Meaning | Example |
|---|---|---|
| `DATABASE_URL` | Postgres connection string: `postgres://user:password@host:port/dbname` | `postgres://postgres:dev@db:5432/tasks` |
| `SUPABASE_URL` | Your Supabase project URL — the project id wrapped in a domain | `https://<project-id>.supabase.co` |
| `SUPABASE_KEY` | The project's **anon** (public) key | `eyJhbGciOi...` |
| `PORT` | Port the API listens on | `8000` |

Copy `.env.example` to `.env` to get a working default for the database — the password there (`dev`) is a throwaway local development credential, not a real secret. The two Supabase values you fill in yourself, from your dashboard under **Project Settings → API**.

**Never use the `service_role` key here.** It bypasses every security rule in the project. The `anon` key is the one meant to be used by clients, and it's all this API needs.

Note the database host differs depending on how you run things: inside `docker compose`, the API reaches Postgres by the **service name** `db` (Docker Compose's internal DNS); if you run the API directly on your machine against a hand-started container, it's `localhost` instead (see below).

## Authentication

Authentication is delegated to **Supabase Auth** as the Identity Provider. This API never stores a password and never hashes anything itself — Supabase holds the accounts, hashes the credentials, and signs the tokens. This API's job is the part that matters for a backend: receiving a token, verifying it, and opening or refusing the door.

The flow is a trust triangle between three parties:

| Step | Who does it | What happens |
|---|---|---|
| 1. Sign up / Log in | client → Supabase | The client sends credentials; this API forwards them |
| 2. The token | Supabase → client | Supabase validates them and returns a **JWT** (the access token) |
| 3. The request | client → this API | The client calls a protected route with `Authorization: Bearer <token>` |
| 4. Verification | this API → Supabase | The API asks Supabase whether the token is genuine. If yes, the door opens |

### The guard

Token checking lives in a single reusable **dependency**, `get_current_user` in `app/main.py`, rather than being copy-pasted into each protected route:

```python
security = HTTPBearer()

def get_current_user(cred: HTTPAuthorizationCredentials = Depends(security)) -> User:
    try:
        user = auth.verify_token(cred.credentials)
    except AuthApiError:
        raise HTTPException(status_code=401, detail='Invalid or expired token')
    if user is None:
        raise HTTPException(status_code=401, detail='Invalid or expired token')
    return user
```

Any route that wants protection declares it as a parameter:

```python
@app.get('/protected/dashboard')
def dashboard(user: User = Depends(get_current_user)):
    return {'message': f'Welcome back, {user.email}'}
```

Two things follow from that. The route body **only runs if the guard passed** — a failed check raises before the endpoint is ever entered, so a protected route cannot accidentally skip verification. And the guard doesn't just approve: it *injects* the resolved Supabase `User`, so the endpoint already knows who is calling.

`HTTPBearer` also gives Swagger UI its **Authorize** padlock, which is what makes the protected routes testable from the browser.

### Verification is a real network call

`supabase.auth.get_user(token)` asks Supabase directly rather than decoding the JWT locally, so the answer accounts for tokens that were revoked or expired since they were issued. Change a single character of a valid token and the request is rejected with `401`.

### Logging out revokes the refresh token

`/auth/logout` is itself a protected route, and it signs out **the caller** specifically:

```python
def logout(token: str):
    supabase.auth.admin.sign_out(token)
```

Passing the caller's own JWT matters because the Supabase client is a single instance shared by every request. A bare `sign_out()` would end whichever session the server-side client happened to hold last, not the one belonging to the user who asked.

What this revokes is the **refresh token**: once logged out, the session can no longer be renewed. The access token itself stays cryptographically valid until it expires, which is inherent to JWTs — not consulting a database on every request is exactly what makes them impossible to cancel mid-flight. Production systems mitigate this with a short token lifetime.

## Database

### Why Postgres in Docker

- **A real database server**, not a file. PostgreSQL runs as its own program, the same engine behind a large share of real backends (FlyRank included) — the right choice once more than one process or user needs to read/write concurrently, unlike the SQLite file used in the previous version of this repo.
- **No local install.** You never install Postgres on your machine — Docker runs the official `postgres` image, an isolated, throwaway, disposable copy of it.
- **A volume, not the container, keeps the data.** The named volume `taskdata` is mounted at Postgres's data directory. The container itself can be deleted and recreated at will; the rows live in the volume and survive that.

Note that this Postgres and Supabase's are two separate databases: tasks live here, user accounts live in Supabase.

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

### Authentication

| Method | Path | Description | Auth header | Success | Errors |
|--------|------|-------------|-------------|---------|--------|
| POST | `/auth/signup` | Create an account. Body: `{"email": "...", "password": "..."}` | none | 201 (user object) | 400 (missing field, invalid email, weak password) |
| POST | `/auth/login` | Authenticate. Body: `{"email": "...", "password": "..."}` | none | 200 (`access_token`, `refresh_token`) | 400 (missing field), 401 (bad credentials) |
| POST | `/auth/logout` | End the session | `Bearer <token>` | 204 (no body) | 401 |

### Public and protected

| Method | Path | Description | Auth header | Success | Errors |
|--------|------|-------------|-------------|---------|--------|
| GET | `/public/info` | Open data, no auth | none | 200 | — |
| GET | `/protected/profile` | The caller's own `id`, `email` and `created_at` | `Bearer <token>` | 200 | 401 |
| GET | `/protected/dashboard` | A second protected route, guarded by the same dependency | `Bearer <token>` | 200 | 401 |

### Tasks

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

All errors are returned as JSON with the shape `{"error": "<message>"}`. The task endpoints, their request/response shapes and status codes are unchanged from the in-memory (A1) and SQLite (A2) versions of this API — only the storage engine underneath, and the authentication layer alongside, were added.

## Examples

### Sign up → 201

```bash
curl -i -X POST http://localhost:8000/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}'
```

```
HTTP/1.1 201 Created
content-type: application/json

{"id":"2f239dec-28f0-4525-9c93-8060569f11bb","email":"test@example.com","created_at":"2026-08-07T18:47:23.479952Z", ...}
```

### Missing field → 400

```bash
curl -i -X POST http://localhost:8000/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com"}'
```

```
HTTP/1.1 400 Bad Request
content-type: application/json

{"error":"Password missing"}
```

### Log in → 200 with a token

```bash
curl -i -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}'
```

```
HTTP/1.1 200 OK
content-type: application/json

{"access_token":"eyJhbGciOiJFUzI1NiIsImtpZCI6...","refresh_token":"7xk2..."}
```

### Bad credentials → 401

```bash
curl -i -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"wrongpass"}'
```

```
HTTP/1.1 401 Unauthorized
content-type: application/json

{"error":"Invalid login credentials"}
```

### Reaching a protected route

Save the token first, then send it in the `Authorization` header:

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}' | jq -r .access_token)

curl -i http://localhost:8000/protected/profile -H "Authorization: Bearer $TOKEN"
```

```
HTTP/1.1 200 OK
content-type: application/json

{"id":"2f239dec-28f0-4525-9c93-8060569f11bb","email":"test@example.com","created_at":"2026-08-07T18:47:23.479952Z"}
```

The same token reaches `/protected/dashboard` too, guarded by the same dependency with no auth code of its own.

### A forged or missing token → 401

```bash
curl -i http://localhost:8000/protected/profile -H "Authorization: Bearer ${TOKEN}X"
curl -i http://localhost:8000/protected/profile
```

```
HTTP/1.1 401 Unauthorized
content-type: application/json

{"error":"Invalid or expired token"}
```

### Log out → 204

```bash
curl -i -X POST http://localhost:8000/auth/logout -H "Authorization: Bearer $TOKEN"
```

```
HTTP/1.1 204 No Content
```

### Create a task → 201

```bash
curl -i -X POST http://localhost:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{"title":"Buy milk"}'
```

```
HTTP/1.1 201 Created
content-type: application/json

{"title":"Buy milk","done":false,"id":4}
```

### Task not found → 404

```bash
curl -i http://localhost:8000/tasks/999
```

```
HTTP/1.1 404 Not Found
content-type: application/json

{"error":"Task 999 not found"}
```

### Filter and search

```bash
curl -i "http://localhost:8000/tasks?done=false&search=milk"
```

```
HTTP/1.1 200 OK
content-type: application/json

[{"title":"Buy Milk","done":false,"id":1}]
```

### Persistence across the whole stack

The point of moving to a containerized database, in three commands:

```bash
curl -X POST http://localhost:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{"title":"Survives a restart"}'
docker compose down
docker compose up -d
curl -i http://localhost:8000/tasks
```

The task is still there after the entire stack — API and database — was torn down and started again. That's the volume, not the container, keeping the data alive: `docker compose down` removes the containers, but `taskdata` is untouched. (Only `docker compose down -v` would also delete the volume, and with it, the data.)

## Running without Docker

For local development without containers, you still need a Postgres server reachable somewhere. The simplest option is running just the database in a container and the API directly on your machine:

```bash
docker run --name taskdb -e POSTGRES_PASSWORD=dev -e POSTGRES_DB=tasks -p 5432:5432 -v taskdata:/var/lib/postgresql/data -d postgres:16

uv sync                              # creates .venv and installs all dependencies from uv.lock
uv run fastapi dev app/main.py       # DATABASE_URL in .env should point at localhost:5432 in this mode
```

## Swagger UI

FastAPI automatically generates interactive documentation at `/docs`, where every endpoint can be tried from the browser. The **Authorize** padlock takes an access token once and applies it to every protected route:

![Swagger UI](docs/swagger2.png)

## The database in Postgres

Confirming the seeded rows live in Postgres itself, via `psql` inside the `db` container:

```bash
docker compose exec db psql -U postgres -d tasks -c "SELECT * FROM tasks;"
```

![tasks table in Postgres](docs/postgres-data.png)
