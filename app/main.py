from fastapi import FastAPI, HTTPException, Request, Header, Depends
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import psycopg
import tasks
from tasks import TaskNew, TaskUpdate
from contextlib import asynccontextmanager
import auth
from auth import AuthApiError, User
import logging

log = logging.getLogger('uvicorn')

@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info('Server running and connected to Supabase')
    yield
    log.info('Server stopping...')

app = FastAPI(lifespan=lifespan)

# --------- BEARER -------------
security = HTTPBearer()
def get_current_user(cred: HTTPAuthorizationCredentials = Depends(security)) -> User:
    try:
        user = auth.verify_token(cred.credentials)
    except AuthApiError:
        raise HTTPException(status_code=401, detail='Invalid or expired token')
    if user is None:
        raise HTTPException(status_code=401, detail='Invalid or expired token')
    return user

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

@app.exception_handler(AuthApiError)
def supabase_auth_handler(request: Request, exc: AuthApiError):
    '''Handler for Supabase Auth error'''
    return JSONResponse(
        status_code=exc.status or 401,
        content={'error': exc.message},
    )

# ----------- AUTH ---------------
@app.post('/auth/signup', status_code=201)
def signup(form: auth.Credentials):
    email, password = form.email, form.password
    if email is None and password is None:
        raise HTTPException(status_code=400, detail=f'Email and password missing')
    elif email is None:
        raise HTTPException(status_code=400, detail=f'Email missing')
    elif password is None:
        raise HTTPException(status_code=400, detail=f'Password missing')

    return auth.signup(email, password)
    
@app.post('/auth/login', status_code=200)
def login(form: auth.Credentials):
    email, password = form.email, form.password
    if email is None and password is None:
        raise HTTPException(status_code=400, detail=f'Email and password missing')
    elif email is None:
        raise HTTPException(status_code=400, detail=f'Email missing')
    elif password is None:
        raise HTTPException(status_code=400, detail=f'Password missing')
    try:
        session = auth.login(email, password)
    except AuthApiError:
        raise HTTPException(status_code=401, detail='Invalid login credentials')
    if session is None:
        raise HTTPException(status_code=401, detail='Invalid login credentials')
    return {
        'access_token' : session.access_token,
        'refresh_token' : session.refresh_token
    }

@app.post('/auth/logout', status_code=204)
def logout(cred: HTTPAuthorizationCredentials = Depends(security),
           user: User = Depends(get_current_user)):
    auth.logout(cred.credentials)

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

# ------- PUBLIC --------------
@app.get('/public/info')
def public_info():
    return {"message": "Welcome stranger! This info is public."}

# ------- PROTECTED --------------
@app.get('/protected/profile')
def profile(user: User = Depends(get_current_user)):
     return {'id': user.id, 'email': user.email, 'created_at': user.created_at}

@app.get('/protected/dashboard')
def dashboard(user: User = Depends(get_current_user)):
    return {'message': f'Welcome back, {user.email}'}