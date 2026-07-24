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
    db.executemany('INSERT INTO tasks (title, done) VALUES (?, ?)', EXAMPLES) # runs one per tuple ('title', 'done')
    db.commit()

def reset():
    '''Reset the store to the initial state (3 examples)'''
    db.execute("DELETE FROM tasks")
    seed()

def seed_if_empty():
    '''Insert example tasks if the db is empty'''
    count = db.execute('SELECT COUNT(*) FROM tasks').fetchone()[0]
    if count == 0:
        seed()

# --------- DB (read) -----------
def get_all(done: bool|None = None, search: str|None = None) -> list[Task]:
    '''
    Generates the query string to get the (filtered) rows of the db.
    "SELECT * FROM tasks WHERE done = ? AND title LIKE ?"
    Returns the list of Task objects
    '''
    sql = 'SELECT * FROM tasks'
    clauses, params = [], []

    if done is not None:
        clauses.append('done = ?')
        params.append(done)
    if search is not None:
        clauses.append('title LIKE ?')
        params.append(f'%{search}%') # contains "search" in title

    if clauses:
        sql += ' WHERE ' + ' AND '.join(clauses)

    rows = db.execute(sql, params).fetchall()
    return [Task(**dict(row)) for row in rows]

def get_one(id: int) -> Task:
    row = db.execute('SELECT * FROM tasks WHERE id = ?', (id,)).fetchone()
    return Task(**dict(row)) if row else None

# --------- DB (write) -----------
def insert(title: str, done: bool) -> Task:
    cur = db.execute('INSERT INTO tasks (title, done) VALUES (?, ?)', (title, done))
    db.commit()
    return Task(id=cur.lastrowid, title=title, done=done)

def update(id: int, title: str|None = None, done: bool|None = None):
    fields, params = [], []
    if title is not None:
        fields.append('title = ?')
        params.append(title)
    if done is not None:
        fields.append('done = ?')
        params.append(done)
    if not fields:
        return get_one(id)

    params.append(id)
    cur = db.execute(f'UPDATE tasks SET {', '.join(fields)} WHERE id = ?', params)
    db.commit()
    return get_one(id) if cur.rowcount else None

def delete(id: int):
    cur = db.execute('DELETE from tasks WHERE id = ?', (id,))
    db.commit()
    return cur.rowcount != 0
