import os
import httpx
from typing import Optional
from urllib.parse import urlencode
from flask import Flask, render_template, request, g, abort, redirect, url_for, render_template_string, make_response
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


def extract_access_token() -> Optional[str]:
    auth = request.headers.get("Authorization", "")
    if isinstance(auth, str) and auth.lower().startswith("bearer "):
        return auth.split(" ", 1)[1].strip()

    token = request.cookies.get("sb-access-token")
    return token  
    
     

def login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        token = extract_access_token()
        if not token:
            return redirect(url_for("login"))

        try:
            user = verify_with_supabase(token)
        except Exception:
            resp = redirect(url_for("login"))
            resp.delete_cookie("sb-access-token", path="/")
            resp.delete_cookie("sb-refresh-token", path="/")
            return resp

        g.user = {"id": user["id"], "email": user.get("email")}
        return view(*args, **kwargs)
    return wrapper

def ensure_player_exists(user: dict, access_token: str) -> None:
    """
    Upsert a players row for this user using their JWT (RLS-friendly).
    """
    supabase.postgrest.auth(access_token)

    res = supabase.table("players").select("id").eq("id", user["id"]).limit(1).execute()
    if res.data:
        return

    payload = {
        "id": user["id"],                        # MUST equal auth.users.id
        "username": (user.get("email") or "").split("@")[0] or None,
    }
    supabase.table("players").insert(payload).execute()


@app.route("/")
def index():
  return render_template("index.html")

@app.route("/login")
def login():
    redirect_uri = url_for("auth_callback", _external=True)
    params = {
        "provider": "google",
        "redirect_to": redirect_uri,  # must be whitelisted in Supabase
    }
    return redirect(f"{SUPABASE_URL.rstrip('/')}/auth/v1/authorize?{urlencode(params)}")

CALLBACK_HTML = """
<!doctype html><meta charset="utf-8">
<title>Signing you in…</title>
<style>body{background:#0b0a12;color:#e8ecff;font:16px/1.4 system-ui;margin:0;display:grid;place-items:center;height:100vh}</style>
<div>Signing you in…</div>
<script>
  // Extract tokens from URL fragment: #access_token=...&refresh_token=...&expires_in=...
  const h = new URLSearchParams(location.hash.slice(1));
  const access_token  = h.get("access_token");
  const refresh_token = h.get("refresh_token");
  const expires_in    = Number(h.get("expires_in")||"3600");

  async function postSession() {
    if (!access_token) { location.replace("/login"); return; }
    const res = await fetch("/session", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ access_token, refresh_token, expires_in })
    });
    if (res.redirected) { location.replace(res.url); return; }
    if (res.ok) { location.replace("/"); } else { location.replace("/login"); }
  }
  postSession();
</script>
"""

@app.route("/logout")
def logout():
    resp = make_response(redirect(url_for("index")))
    resp.delete_cookie("sb-access-token", path="/")
    resp.delete_cookie("sb-refresh-token", path="/")
    return resp

@app.get("/auth/callback", endpoint="auth_callback")
def callback():
     return render_template_string(CALLBACK_HTML)

@app.post("/session")
def establish_session():
    data = request.get_json(silent=True) or {}
    access_token  = data.get("access_token")
    refresh_token = data.get("refresh_token")
    expires_in    = int(data.get("expires_in") or 3600)

    if not access_token:
        abort(400, description="Missing access_token")

    try:
        r = httpx.get(
            f"{SUPABASE_URL.rstrip('/')}/auth/v1/user",
            headers={"Authorization": f"Bearer {access_token}", "apikey": SUPABASE_ANON_KEY},
            timeout=5.0,
        )
        user = r.json()  # contains user.id, email, etc.
        ensure_player_exists(user, access_token)
        if r.status_code != 200:
            abort(401, description="Invalid/expired token")
    except Exception:
        app.logger.exception("ensure_player_exists failed: %s", e)
        abort(401, description="Auth verification failed")

    resp = make_response(redirect(url_for("home"))) 
    cookie_opts = dict(
        httponly=True,
        secure=False,     
        samesite="Lax",
        max_age=expires_in,
        path="/",
    )
    resp.set_cookie("sb-access-token", access_token, **cookie_opts)
    if refresh_token:
        resp.set_cookie("sb-refresh-token", refresh_token, **{**cookie_opts, "max_age": 60*60*24*30})

    return resp


@app.route("/home")
@login_required
def home():
     return "Protected!"

@app.get("/me")
@login_required
def me():
    # should return players row once it exists
    supabase.postgrest.auth(request.cookies.get("sb-access-token"))
    row = supabase.table("players").select("id, username, level, xp").eq("id", g.user["id"]).single().execute()
    return row.data or {}