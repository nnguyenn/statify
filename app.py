import os
from flask import Flask, render_template, request, g, abort
from dotenv import load_dotenv
from supabase import create_client, Client
from functools import wraps
from auth_helpers import verify_with_supabase

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_DB")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

try:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

        # Example: Attempt to fetch data from a table to verify the connection
        # Replace 'your_table_name' with an actual table in your Supabase project
        # and 'id' with a suitable column for filtering if needed.
        response = supabase.table('players').select('*').limit(1).execute()

        if response.data:
            print("Successfully connected to Supabase and fetched data.")
            print("Example data:", response.data)
        else:
            print("Successfully connected to Supabase, but no data found in the specified table.")
            print("Response data:", response.data)

except Exception as e:
        print(f"Error connecting to Supabase: {e}")


app = Flask(__name__)


def extract_access_token(token):
    auth = request.header.get("Authorization", "")
    if auth.lower().startswith("bearer "):
        return auth.split(" ", 1)[1].strip()
    token = request.cookies.get("sb-access-token")
    if token:
        return token

    return None
    
     
def login_required(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        token = extract_access_token()
        if not token:
            abort(401)
        try:
            user = verify_with_supabase(token)
        except Exception:
            abort(401)

        g.user = {"id": user["id"], "email": user.get("email")}
        return function(*args, **kwargs)
    return wrapper


@app.route("/")
def index():
  return render_template("index.html")

@app.route("/login")
def login():
     pass

@app.route("/logout")
def logout():
     pass

@app.route("/callback")
def callback():
     pass


@app.route("/protected_area")
@login_required
def protected_area():
     return "Protected!"