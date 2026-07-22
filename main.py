from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel

app = FastAPI()

# ========== TASKS ==============
class TaskNew(BaseModel):
    title: str
    done: bool = False

class Task(TaskNew):
    id: int

class TaskUpdate(BaseModel):
    title: str | None = None
    done : bool | None = None

# in-memory task store
TASKS = {
    0: Task(id=0, title='Buy Milk', done=False),
    1: Task(id=1, title='Make API', done=True),
    2: Task(id=2, title='Task Example Nº3', done=False),
    }
next_id = 3 # next id to assign

# =========== API ================

# --------- HANDLERS -------------
@app.exception_handler(HTTPException)
def http_handler(request: Request, exc: HTTPException):
    '''Handler for HTTPException'''
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail}, # "error" instead of "detail"
    )

@app.exception_handler(RequestValidationError)
def validation_handler(request: Request, exc: RequestValidationError):
    '''Handler for "RequestValidationError"'''
    first = exc.errors()[0]
    field = '.'.join(str(x) for x in first['loc'] if x != 'body')
    return JSONResponse(
        status_code=400,
        content={"error": f"{field}: {first['msg']}"},
    )

# ----------- GET --------------
@app.get('/') # 200: OK (default)
def get_root():
    '''API Description'''
    return {'name': 'To-Do List API', 'version': '1.0', 'endpoints': ['/tasks'] }

@app.get('/health') # 200: OK (default)
def get_health():
    '''Check if the server is alive'''
    return {'status': 'ok'}

@app.get('/tasks')
def list_tasks():
    return list(TASKS.values())

@app.get('/tasks/{id}') # 200: OK (default)
def get_task(id: int):
    task = TASKS.get(id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task {id} not found") # Error 404
    return task

# ----------- POST --------------
@app.post('/tasks', status_code=201) # 201: Created
def create_task(form: TaskNew):
    global next_id
    new_task = Task(id=next_id, title=form.title, done=form.done)
    TASKS[next_id] = new_task
    next_id += 1
    return new_task

# ----------- PUT --------------
@app.put('/tasks/{id}')
def modify_task(id: int, form: TaskUpdate): # 200: OK (default)
    if form.title is None and form.done is None:
        raise HTTPException(status_code=400, detail='Empty or invalid body') # 400: Bad Request
    task = TASKS.get(id)
    if task is None:
        raise HTTPException(status_code=404, detail='Unknown task ID') # 404: Not Found
    if form.title is not None:
        task.title = form.title
    if form.done is not None:
        task.done = form.done
    return task

# ------- DELETE --------------
@app.delete('/tasks/{id}', status_code=204) # 204: No Content
def delete_task(id: int):
    if id not in TASKS:
        raise HTTPException(status_code=404, detail='Unknown task ID') # 404: Not Found
    TASKS.pop(id)
