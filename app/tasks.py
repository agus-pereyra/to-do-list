from pydantic import BaseModel
from db import db

# --------- TASK CLASSES -------------
class TaskNew(BaseModel):
    title: str
    done: bool = False

class Task(TaskNew):
    id: int

class TaskUpdate(BaseModel):
    title: str | None = None
    done : bool | None = None


# --------- DB -------------

EXAMPLES = [
    ('Buy Milk', False),
    ('Make API', True),
    ('Task Example Nº3', False),
]

def seed():
    '''Insert example tasks'''
    db.executemany("INSERT INTO tasks (title, done) VALUES (?, ?)", EXAMPLES) # runs one per tuple ('title', 'done')
    db.commit()

def reset():
    '''Reset the store to the initial state (3 examples)'''
    db.execute("DELETE FROM tasks")
    seed()

def seed_if_empty():
    count = db.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
    if count == 0:
        seed()