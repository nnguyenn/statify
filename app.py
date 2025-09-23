import os
from flask import Flask
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_DB")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

try:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

        # Example: Attempt to fetch data from a table to verify the connection
        # Replace 'your_table_name' with an actual table in your Supabase project
        # and 'id' with a suitable column for filtering if needed.
        response = supabase.table('your_table_name').select('*').limit(1).execute()

        if response.data:
            print("Successfully connected to Supabase and fetched data.")
            print("Example data:", response.data)
        else:
            print("Successfully connected to Supabase, but no data found in the specified table.")
            print("Response data:", response.data)

except Exception as e:
        print(f"Error connecting to Supabase: {e}")





app = Flask(__name__)

#Base Page
@app.get("/")
def home():
  return "Hello, World!"