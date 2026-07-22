from fastapi import FastAPI

app = FastAPI()

@app.get('/')
def get_root():
    return {'name': 'Task API', 'version': '1.0', 'endpoints': ['/tasks'] }

@app.get('/health')
def get_health():
    '''Check if the server is alive'''
    return {'status': 'ok'}


