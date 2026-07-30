from pydantic import BaseModel, Field
from db import db

# --------- TASK CLASSES -------------
class TaskNew(BaseModel):
    title: str = Field(min_length=1)
    done: bool = False

class Task(TaskNew):
    id: int

class TaskUpdate(BaseModel):
    title: str | None = None
    done : bool | None = None

# --------- DB (init) -----------
EXAMPLES = [
    ('Buy Milk', False),
    ('Make API', True),
    ('Task Example Nº3', False),
]

def seed():
    '''Insert example tasks'''
    with db.cursor() as cur:
        cur.executemany('INSERT INTO tasks (title, done) VALUES (%s, %s)', EXAMPLES) # runs one per tuple ('title', 'done')
    db.commit()

def reset():
    '''Reset the store to the initial state (3 examples)'''
    db.execute("DELETE FROM tasks")
    seed()

def seed_if_empty():
    '''Insert example tasks if the db is empty'''
    count = db.execute('SELECT COUNT(*) FROM tasks').fetchone()['count']
    if count == 0:
        seed()

# --------- DB (read) -----------
def get_all(done: bool|None = None, search: str|None = None) -> list[Task]:
    '''
    Generates the query string to get the (filtered) rows of the db.
    "SELECT * FROM tasks WHERE done = %s AND title ILIKE %s"
    Returns the list of Task objects
    '''
    sql = 'SELECT * FROM tasks'
    clauses, params = [], []

    if done is not None:
        clauses.append('done = %s')
        params.append(done)
    if search is not None:
        clauses.append('title ILIKE %s') # ILIKE: Postgres' case-insensitive LIKE
        params.append(f'%{search}%') # contains "search" in title

    if clauses:
        sql += ' WHERE ' + ' AND '.join(clauses)

    rows = db.execute(sql, params).fetchall()
    return [Task(**dict(row)) for row in rows]

def get_one(id: int) -> Task:
    row = db.execute('SELECT * FROM tasks WHERE id = %s', (id,)).fetchone()
    return Task(**dict(row)) if row else None

def get_stats() -> dict[str | int]:
    total = db.execute('SELECT COUNT(*) from tasks').fetchone()['count']
    done = db.execute('SELECT COUNT(*) from tasks WHERE done = %s', (True,)).fetchone()['count']
    return {'total' : total, 'done' : done, 'open' : total - done}

# --------- DB (write) -----------
def insert(title: str, done: bool) -> Task:
    row = db.execute('INSERT INTO tasks (title, done) VALUES (%s, %s) RETURNING *', (title, done)).fetchone()
    db.commit()
    return Task(**dict(row))

def update(id: int, title: str|None = None, done: bool|None = None):
    fields, params = [], []
    if title is not None:
        fields.append('title = %s')
        params.append(title)
    if done is not None:
        fields.append('done = %s')
        params.append(done)
    if not fields:
        return get_one(id)

    params.append(id)
    cur = db.execute(f'UPDATE tasks SET {', '.join(fields)} WHERE id = %s', params)
    db.commit()
    return get_one(id) if cur.rowcount else None

def delete(id: int):
    cur = db.execute('DELETE from tasks WHERE id = %s', (id,))
    db.commit()
    return cur.rowcount != 0
