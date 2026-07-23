from pydantic import BaseModel

# ========== MODELS ==============
class TaskNew(BaseModel):
    title: str
    done: bool = False

class Task(TaskNew):
    id: int

class TaskUpdate(BaseModel):
    title: str | None = None
    done : bool | None = None

# ========== IN-MEMORY STORE ==============
TASKS: dict[int, Task] = {}
next_id = 0 # next id to assign

def reset():
    '''Reset the store to the initial state (3 examples)'''
    global TASKS, next_id
    TASKS = {
        0: Task(id=0, title='Buy Milk', done=False),
        1: Task(id=1, title='Make API', done=True),
        2: Task(id=2, title='Task Example Nº3', done=False),
    }
    next_id = 3

reset() # initialize the store on import
