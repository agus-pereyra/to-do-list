''' Initialize the Posgres Database '''

from pathlib import Path
import os
import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / '.env')
DATABASE_URL = os.environ['DATABASE_URL']

db = psycopg.connect(DATABASE_URL, row_factory=dict_row)

db.execute(
    '''
    CREATE TABLE IF NOT EXISTS tasks (
        id SERIAL PRIMARY KEY,
        title TEXT NOT NULL,
        done BOOLEAN NOT NULL DEFAULT FALSE
    )
    ''')

db.commit()