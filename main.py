from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel

app = FastAPI()

# ========== TASKS ==============
class TaskForm(BaseModel):
    title: str
    done: bool = False

class Task(TaskForm):
    id: int

# in-memory task list
TASKS = [
    Task(id=0, title='Buy Milk', done=False), 
    Task(id=1, title='Make API', done=True), 
    Task(id=2, title='Task Example Nº3', done=False)
    ]

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
@app.get('/')
def get_root():
    '''API Description'''
    return {'name': 'To-Do List API', 'version': '1.0', 'endpoints': ['/tasks'] }

@app.get('/health')
def get_health():
    '''Check if the server is alive'''
    return {'status': 'ok'}

@app.get('/tasks')
def list_tasks():
    return TASKS

@app.get('/tasks/{id}')
def get_task(id: int):
    for task in TASKS:
        if task.id == id:
            return task
    raise HTTPException(status_code=404, detail=f"Task {id} not found") # Error 404

# ----------- POST --------------
@app.post('/tasks', status_code=201)
def create_task(task: TaskForm):
    id = max([t.id for t in TASKS]) + 1
    new_task = Task(id=id, title=task.title, done=task.done)
    TASKS.append(new_task)
    return new_task
