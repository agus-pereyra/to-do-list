''' Initialize the Supabase client '''

import os
from pathlib import Path
from supabase import create_client, Client
from supabase_auth import AuthResponse
from dotenv import load_dotenv
from pydantic import BaseModel

class Credentials(BaseModel):
    email: str | None = None
    password: str | None = None

load_dotenv(Path(__file__).parent.parent / '.env')

url: str = os.environ["SUPABASE_URL"]
key: str = os.environ["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

def signup(email: str, password: str):
    response = supabase.auth.sign_up(
        {
            'email' : email,
            'password' : password
        }
    )
    return response.user
    

def login(email: str, password: str):
    response = supabase.auth.sign_in_with_password(
        {
            "email": email,
            "password": password,
        }
    )
    return response.session

    