import os
import httpx
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_DB")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

def verify_with_supabase(token):
    url = SUPABASE_URL.rstrip("/") + "/auth/v1/user"
    headers = {
        "Authorization": f"Bearer {token}",
        "apikey": SUPABASE_ANON_KEY,
    }
    with httpx.Client(timeout=5.0) as client:
        r = client.get(url, headers=headers)
    if r.status_code != 200:
        raise ValueError(f"auth_failed:{r.status_code}")
    data = r.json()
    return {
        "id": data["id"],
        "email": data.get("email"),
        "provider": (data.get("app_metadata") or {}).get("provider"),
        "raw": data, 
    }