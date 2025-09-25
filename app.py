import os
from datetime import date
import httpx
from typing import Optional
from urllib.parse import urlencode
from flask import Flask, render_template, request, g, abort, redirect, url_for, render_template_string, make_response, flash
from dotenv import load_dotenv
from supabase import create_client, Client
from functools import wraps
from auth_helpers import verify_with_supabase
from xp_helper import cumulative_xp_to_level, xp_needed_for_level, xp_progress
import re

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
<!doctype html>
<meta charset="utf-8" />
<title>Opening Gate…</title>
<style>
  :root{
    --blue:#39e0ff; --blue2:#1fcaff; --text:#e8ecff; --scanline:rgba(0,0,0,.14);
    --size:min(120px, 22vmin);  /* small spiral size */
  }
  *{box-sizing:border-box}
  html,body{height:100%}
  body{margin:0; background:#05070f; color:var(--text); overflow:hidden; font:16px/1.4 system-ui, -apple-system, Segoe UI, Roboto, sans-serif}

  /* Background (your image) */
  .bg{position:fixed; inset:0; z-index:0; pointer-events:none}
  .bg::before{
    content:""; position:absolute; inset:0;
    background:url("{{ url_for('static', filename='statify_home.png') }}") center/cover no-repeat;
    image-rendering:pixelated; filter:contrast(108%) saturate(110%) brightness(.92);
  }
  .bg::after{
    content:""; position:absolute; inset:0;
    background:
      radial-gradient(600px 320px at 50% 30%, rgba(57,224,255,.12), rgba(0,0,0,0) 55%),
      linear-gradient(to bottom, rgba(0,0,0,.08), rgba(0,0,0,.55));
  }
  .scan{position:fixed; inset:0; z-index:1; pointer-events:none; opacity:.3; mix-blend-mode:multiply;
    background:
      repeating-linear-gradient(45deg, rgba(255,255,255,.04) 0 2px, rgba(0,0,0,.04) 2px 4px),
      repeating-linear-gradient(to bottom, transparent 0px, transparent 2px, var(--scanline) 3px, var(--scanline) 4px);
  }

  /* Centered, small arcane spiral */
  .wrap{position:relative; z-index:2; display:grid; place-items:center; height:100vh}
  .sigil{position:relative; width:var(--size); height:var(--size); filter:drop-shadow(0 0 10px rgba(57,224,255,.55))}

  /* Thin rotating arcs (blue flame vibe) */
  .ring{
    position:absolute; inset:0; border-radius:50%;
    /* carve a thin ring */
    mask: radial-gradient(closest-side, transparent calc(100% - 6px), #000 calc(100% - 6px));
    /* a few bright arcs with gaps */
    background:
      conic-gradient(from 0deg,
        transparent 0 70deg, rgba(63,205,255,.95) 70deg 105deg, transparent 105deg 180deg,
        rgba(63,205,255,.75) 180deg 200deg, transparent 200deg 360deg);
    animation:spin 2.4s linear infinite;
    box-shadow: inset 0 0 18px rgba(63,205,255,.35);
  }
  .r2{ inset:10%; opacity:.85; filter:blur(.2px) brightness(1.1) hue-rotate(5deg); animation-duration: 3.2s; animation-direction: reverse; }
  .r3{ inset:20%; opacity:.75; filter:blur(.3px) brightness(1.15) hue-rotate(-8deg); animation-duration: 4.1s; }

  /* Tiny core flame */
  .core{
    position:absolute; left:50%; top:50%; transform:translate(-50%,-50%);
    width:calc(var(--size) * .22); height:calc(var(--size) * .22); border-radius:50%;
    background: radial-gradient(circle at 50% 48%, rgba(63,205,255,.95), rgba(31,202,255,.75) 55%, rgba(0,0,0,0) 65%);
    box-shadow:
      0 0 14px rgba(63,205,255,.85),
      0 0 26px rgba(63,205,255,.45),
      0 0 46px rgba(31,202,255,.35);
    animation:flame 1.5s ease-in-out infinite;
  }

  @keyframes spin { to { transform: rotate(360deg); } }
  @keyframes flame {
    0%, 100% { transform:translate(-50%,-50%) scale(1);   filter:brightness(1); }
    50%      { transform:translate(-50%,-50%) scale(1.08); filter:brightness(1.15); }
  }

  .sr-only{
    position:absolute; width:1px; height:1px; padding:0; margin:-1px; overflow:hidden; clip:rect(0,0,0,0); white-space:nowrap; border:0;
  }
</style>

<div class="bg" aria-hidden="true"></div>
<div class="scan" aria-hidden="true"></div>

<div class="wrap" role="status" aria-live="polite">
  <div class="sigil" aria-hidden="true">
    <div class="ring r1"></div>
    <div class="ring r2"></div>
    <div class="ring r3"></div>
    <div class="core"></div>
  </div>
  <span class="sr-only">Signing you in…</span>
</div>

<script>
  // Extract tokens from URL fragment and post to your server
  const h = new URLSearchParams(location.hash.slice(1));
  const access_token  = h.get("access_token");
  const refresh_token = h.get("refresh_token");
  const expires_in    = Number(h.get("expires_in")||"3600");

  async function postSession() {
    if (!access_token) { location.replace("/login"); return; }
    try{
      const res = await fetch("/session", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ access_token, refresh_token, expires_in })
      });
      if (res.redirected) { location.replace(res.url); return; }
      if (res.ok) { location.replace("/"); } else { location.replace("/login"); }
    } catch { location.replace("/login"); }
  }
  // Small delay so the mini spiral is visible
  setTimeout(postSession, 250);
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


@app.get("/home")
@login_required
def home():
    token = request.cookies.get("sb-access-token")
    supabase.postgrest.auth(token)
    uid = g.user["id"]

    # Player snapshot
    player = (
        supabase.table("players")
        .select("id, username, level, xp, unspent_points, strength, dexterity, wisdom, vitality, charisma, endurance")
        .eq("id", uid).single().execute().data
        or {}
    )

    # Ensure today's boss instance exists (RPC from the SQL you ran)
    boss = supabase.rpc("ensure_boss_today", {"p_player_id": uid}).execute().data or {}

    # Pull template info for display
    boss_tmpl = {}
    if boss and boss.get("template_id"):
        boss_tmpl = (
            supabase.table("boss_templates")
            .select("id, name, tier, reward_gold")
            .eq("id", boss["template_id"]).single().execute().data
            or {}
        )

    # Today’s damage sum (optional; safe fallback)
    today_dmg = 0
    if boss and boss.get("id"):
        evts = (
            supabase.table("damage_events")
            .select("damage")
            .eq("boss_instance_id", boss["id"])
            .order("created_at", desc=True)
            .limit(200)  # plenty for a day
            .execute().data
            or []
        )
        today_dmg = sum(e.get("damage", 0) for e in evts)

    # Active tasks count (for the Daily Quests blurb)
    tasks_cnt = len(
        supabase.table("tasks")
        .select("id")
        .eq("owner_id", uid).eq("is_active", True)
        .execute().data or []
    )

    # Shop preview: a few items + wallet balance (sum of tx)
    items = (
        supabase.table("items")
        .select("id, name, slot, price_gold, rarity")
        .order("price_gold", desc=False).limit(3)
        .execute().data or []
    )
    gold_rows = (
        supabase.table("wallet_tx")
        .select("delta_gold")
        .eq("player_id", uid)
        .execute().data or []
    )
    gold = sum(r.get("delta_gold", 0) for r in gold_rows)

    # Boss HP % (avoid divide-by-zero)
    max_hp = boss.get("max_hp") or 1
    cur_hp = boss.get("current_hp") or 0
    hp_pct = max(0, min(100, int(round(cur_hp / max_hp * 100))))

    level = (player.get("level") or 1)
    xp_val = (player.get("xp") or 0)

    # Set this to True if `players.xp` stores lifetime XP across all levels.
    XP_IS_TOTAL = False

    xp = xp_progress(level, xp_val, xp_is_total=XP_IS_TOTAL)
    xp_pct  = xp["pct"]
    xp_text = xp["text"]
    recent_clears = supabase.table("tasks_completions")\
      .select("completed_at, task:tasks(title, reward_xp)")\
      .eq("player_id", uid).order("completed_at", desc=True).limit(5).execute().data
    recent_clears = [
        {"title": (row["task"] or {}).get("title"), "reward_xp": (row["task"] or {}).get("reward_xp"), "completed_at": row.get("completed_at")}
        for row in (recent_clears or [])
    ]

    recent_notes = supabase.table("journals")\
      .select("title, created_at").eq("owner_id", uid).order("created_at", desc=True).limit(5).execute().data


    return render_template(
        "home.html",
        player=player,
        boss=boss,
        boss_tmpl=boss_tmpl,
        today_dmg=today_dmg,
        tasks_cnt=tasks_cnt,
        hp_pct=hp_pct,
        items=items, gold=gold,
        xp_pct=xp_pct, xp_text=xp_text,
        recent_clears=recent_clears, 
        recent_notes=recent_notes
    )


# CHARACTER STUFF
@app.get("/character")
@login_required
def character():
    token = request.cookies.get("sb-access-token")
    supabase.postgrest.auth(token)
    uid = g.user["id"]

    # Player snapshot (add 'bio' column to your players table if you haven't: ALTER TABLE public.players ADD COLUMN bio text;)
    player = (
        supabase.table("players")
        .select("id, username, bio, level, xp, unspent_points, strength, dexterity, wisdom, vitality, charisma, endurance")
        .eq("id", uid).single().execute().data
        or {}
    )

    # Wallet (gold)
    gold_rows = (
        supabase.table("wallet_tx")
        .select("delta_gold")
        .eq("player_id", uid)
        .execute().data or []
    )
    gold = sum(r.get("delta_gold", 0) for r in gold_rows)

    # Equipment: get IDs then look up item records
    res = (
    supabase.table("equipment")
    .select("weapon_id, armor_id, charm_id")
    .eq("player_id", uid)
    .limit(1)
    .execute()
)
    equip = res.data[0] if res.data else {}
    item_ids = [i for i in [equip.get("weapon_id"), equip.get("armor_id"), equip.get("charm_id")] if i]
    items_map = {}
    if item_ids:
        it = supabase.table("items").select("id, name, slot, power, rarity").in_("id", item_ids).execute().data or []
        items_map = {row["id"]: row for row in it}

    weapon = items_map.get(equip.get("weapon_id"))
    armor  = items_map.get(equip.get("armor_id"))
    charm  = items_map.get(equip.get("charm_id"))

    # Titles (last 6, mark active)
    titles = (
        supabase.table("player_titles")
        .select("id, active, earned_at, title_id, title:titles(name, description)")
        .eq("player_id", uid)
        .order("earned_at", desc=True)
        .limit(6)
        .execute().data or []
    )

    # Inventory (first 20)
    inv_rows = (
        supabase.table("inventory")
        .select("item_id, qty, item:items(name, slot, rarity, power)")
        .eq("player_id", uid)
        .order("acquired_at", desc=True)
        .limit(20)
        .execute().data or []
    )
    editing = request.args.get("edit") == "1"
    return render_template(
        "character.html",
        player=player,
        gold=gold,
        weapon=weapon, armor=armor, charm=charm,
        titles=titles,
        inventory=inv_rows,
        editing=editing,  
    )

def load_character_context(uid, token):
    supabase.postgrest.auth(token)
    player = (supabase.table("players")
              .select("id, username, bio, level, xp, unspent_points, strength, dexterity, wisdom, vitality, charisma, endurance")
              .eq("id", uid).single().execute().data or {})
    # equipment (safe 0-row)
    eq = supabase.table("equipment").select("weapon_id, armor_id, charm_id").eq("player_id", uid).limit(1).execute().data
    equip = eq[0] if eq else {}
    item_ids = [i for i in [equip.get("weapon_id"), equip.get("armor_id"), equip.get("charm_id")] if i]
    items_map = {}
    if item_ids:
        it = supabase.table("items").select("id, name, slot, power, rarity").in_("id", item_ids).execute().data or []
        items_map = {r["id"]: r for r in it}
    titles = (supabase.table("player_titles")
              .select("id, active, earned_at, title_id, title:titles(name, description)")
              .eq("player_id", uid).order("earned_at", desc=True).limit(6).execute().data or [])
    inv = (supabase.table("inventory")
           .select("item_id, qty, item:items(name, slot, rarity, power)")
           .eq("player_id", uid).order("acquired_at", desc=True).limit(20).execute().data or [])
    gold = sum((r.get("delta_gold", 0) for r in
               (supabase.table("wallet_tx").select("delta_gold").eq("player_id", uid).execute().data or [])))
    return {
        "player": player,
        "weapon": items_map.get(equip.get("weapon_id")),
        "armor":  items_map.get(equip.get("armor_id")),
        "charm":  items_map.get(equip.get("charm_id")),
        "titles": titles,
        "inventory": inv,
        "gold": gold,
    }

# ---------- CHARACTER: UPDATE PROFILE (username + bio) ----------
@app.post("/character/profile")
@login_required
def update_character_profile():
    token = request.cookies.get("sb-access-token")
    uid = g.user["id"]
    supabase.postgrest.auth(token)

    username = (request.form.get("username") or "").strip()
    bio      = (request.form.get("bio") or "").strip()

    # Basic validation
    if username and (len(username) < 3 or len(username) > 24 or not re.match(r"^[A-Za-z0-9_]+$", username)):
        ctx = load_character_context(uid, token)
        return render_template("character.html", editing=True, error="Username must be 3–24 chars using letters, numbers, or underscore.", **ctx)

    # Uniqueness check (server-side)
    if username:
        exists = (supabase.table("players").select("id")
                  .eq("username", username).neq("id", uid).limit(1).execute().data)
        if exists:
            ctx = load_character_context(uid, token)
            return render_template("character.html", editing=True, error="That username is already taken.", **ctx)

    # Apply update
    payload = {"bio": bio}
    if username:
        payload["username"] = username
    supabase.table("players").update(payload).eq("id", uid).execute()

    return redirect(url_for("character"))

@app.get("/u/<username>", endpoint="profile_by_username")
@login_required
def profile_by_username(username):
    token = request.cookies.get("sb-access-token")
    supabase.postgrest.auth(token)
    row = supabase.rpc("get_profile_by_username", {"p_username": username}).execute().data
    if not row:
        abort(404)
    profile = row[0] if isinstance(row, list) else row
    return render_template("profile_public.html", profile=profile, me=g.user["id"])

# Search handler (GET /u?q=name -> redirect to /u/name)
@app.get("/u")
@login_required
def profile_search_redirect():
    q = (request.args.get("q") or "").strip()
    if not q:
        return redirect(url_for("home"))
    return redirect(url_for("profile_by_username", username=q))