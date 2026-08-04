''' Initialize the Supabase client '''

import os
from pathlib import Path
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / '.env')

url: str = os.environ["SUPABASE_URL"]
key: str = os.environ["SUPABASE_KEY"]
supabase: Client = create_client(url, key)