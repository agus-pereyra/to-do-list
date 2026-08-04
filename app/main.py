from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import psycopg
import tasks
from tasks import TaskNew, TaskUpdate
from contextlib import asynccontextmanager
import auth
import logging

log = logging.getLogger('uvicorn')

@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info('Server running and connected to Supabase')
    yield
    log.info('Server stopping...')

app = FastAPI(lifespan=lifespan)

tasks.seed_if_empty()

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

@app.exception_handler(psycopg.Error)
def db_handler(request: Request, exc: psycopg.Error):
    '''Handler for database errors'''
    return JSONResponse(status_code=500, content={"error": "Database error"})

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
    return tasks.get_all(done, search)

@app.get('/tasks/{id}') # 200: OK (default)
def get_task(id: int):
    task = tasks.get_one(id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task {id} not found") # Error 404
    return task

@app.get('/stats')
def get_stats():
    return tasks.get_stats()

# ----------- POST --------------
@app.post('/tasks', status_code=201) # 201: Created
def create_task(form: TaskNew):
    return tasks.insert(form.title, form.done)

@app.post('/reset', status_code=204) # 204: No Content
def reset_tasks():
    '''Reset the database to the initial state (3 examples)'''
    tasks.reset()

# ----------- PUT --------------
@app.put('/tasks/{id}')
def modify_task(id: int, form: TaskUpdate): # 200: OK (default)
    if form.title is None and form.done is None:
        raise HTTPException(status_code=400, detail='Empty or invalid body') # 400: Bad Request
    task = tasks.update(id, form.title, form.done)
    if task is None:
        raise HTTPException(status_code=404, detail='Unknown task ID') # 404: Not Found
    return task

# ------- DELETE --------------
@app.delete('/tasks/{id}', status_code=204) # 204: No Content
def delete_task(id: int):
    if not tasks.delete(id):
        raise HTTPException(status_code=404, detail='Unknown task ID') # 404: Not Found