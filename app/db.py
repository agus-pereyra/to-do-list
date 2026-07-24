''' Initialize the SQLite Database '''

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / 'tasks.db'

db = sqlite3.connect(DB_PATH, check_same_thread=False) # one unique connection for all requests (small db)
db.row_factory = sqlite3.Row # indexable by index and column name

db.execute(
    '''
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY,
        title TEXT NOT NULL,
        done BOOLEAN NOT NULL DEFAULT FALSE
    )
    ''')

db.commit()