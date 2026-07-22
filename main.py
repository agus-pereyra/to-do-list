from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

app = FastAPI()

class Task(BaseModel):
    id: int
    title: str
    done: bool

# in-memory task list
TASKS = [
    Task(id=0, title='Buy Milk', done=False), 
    Task(id=1, title='Make API', done=True), 
    Task(id=2, title='Task Example Nº3', done=False)
    ]

@app.exception_handler(HTTPException)
def http_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail}, # "error" instead of "detail"
    )

@app.get('/')
def get_root():
    return {'name': 'Task API', 'version': '1.0', 'endpoints': ['/tasks'] }

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
    raise HTTPException(status_code=404, detail=f"Task {id} not found")