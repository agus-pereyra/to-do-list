from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

import tasks
from tasks import Task, TaskNew, TaskUpdate

app = FastAPI()

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
def list_tasks(done: bool|None = None, search: str|None = None):
    '''List tasks with optional query parameters (filter by task status and search by title)'''
    result = list(tasks.TASKS.values())
    if done is not None:
        result = [t for t in result if t.done == done]
    if search is not None:
        result = [t for t in result if search.lower() in t.title.lower()]
    return result

@app.get('/tasks/{id}') # 200: OK (default)
def get_task(id: int):
    task = tasks.TASKS.get(id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task {id} not found") # Error 404
    return task

@app.get('/stats')
def get_stats():
    total = len(tasks.TASKS)
    done = sum(1 for t in tasks.TASKS.values() if t.done)
    return {'total' : total, 'done' : done, 'open' : total - done}

# ----------- POST --------------
@app.post('/tasks', status_code=201) # 201: Created
def create_task(form: TaskNew):
    new_task = Task(id=tasks.next_id, title=form.title, done=form.done)
    tasks.TASKS[tasks.next_id] = new_task
    tasks.next_id += 1 # module attribute -> no "global" needed here
    return new_task

@app.post('/reset', status_code=204) # 204: No Content
def reset_tasks():
    '''Reset the TASKS store to the initial state (3 examples)'''
    tasks.reset()

# ----------- PUT --------------
@app.put('/tasks/{id}')
def modify_task(id: int, form: TaskUpdate): # 200: OK (default)
    if form.title is None and form.done is None:
        raise HTTPException(status_code=400, detail='Empty or invalid body') # 400: Bad Request
    task = tasks.TASKS.get(id)
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
    if id not in tasks.TASKS:
        raise HTTPException(status_code=404, detail='Unknown task ID') # 404: Not Found
    tasks.TASKS.pop(id)
