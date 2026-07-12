"""
NITRAGEN backend — Flask + Supabase

Architecture:
- Google login happens on the FRONTEND via the Supabase JS client
  (supabase.auth.signInWithOAuth({ provider: 'google' })). Supabase handles
  the whole OAuth dance for you — you just flip a switch in the Supabase
  dashboard and paste your Google Client ID/Secret there. No OAuth code
  needed in Flask.
- The frontend then sends the Supabase access token on every request as:
      Authorization: Bearer <supabase_access_token>
  This Flask app verifies that token, figures out who's calling (and
  whether they're admin), and performs the actual business logic using
  the Supabase *service role* key (which bypasses Row Level Security),
  because approving/rejecting delete requests and posting ads are
  privileged admin-only actions best enforced in one place: here.
- Realtime chat messages are read/written directly from the frontend using
  the Supabase client + Realtime — Flask doesn't need to be involved in
  the live chat traffic at all. RLS policies (see supabase/schema.sql)
  make sure only the buyer, seller, and admin can see/write a given chat.
"""

import os
import jwt
from jwt import PyJWKClient
from functools import wraps
from flask import Flask, request, jsonify
from flask_cors import CORS
from supabase import create_client, Client

# ---------------------------------------------------------------------
# Config (all from environment variables — see .env.example)
# ---------------------------------------------------------------------
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_ROLE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
SUPABASE_JWT_SECRET = os.environ["SUPABASE_JWT_SECRET"]  # legacy fallback only
FRONTEND_ORIGIN = os.environ.get("FRONTEND_ORIGIN", "*")

app = Flask(__name__)
CORS(app, origins=[FRONTEND_ORIGIN] if FRONTEND_ORIGIN != "*" else "*", supports_credentials=True)

# service-role client: bypasses RLS, used ONLY for admin-verified actions below
sb: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

# Supabase's public key set — used to verify tokens signed with the project's
# current signing key (which may be ES256/RS256, not the old HS256 legacy secret).
_jwks_client = PyJWKClient(f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json")


# ---------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------
def verify_token():
    """Pull the Supabase access token from the Authorization header and verify it.
    Returns the decoded payload (contains 'sub' = user id, 'email', etc.) or None.

    Tries the modern JWKS-based verification first (works whatever algorithm
    the project currently signs with — ES256, RS256, etc.), then falls back
    to the legacy HS256 secret for older projects/tokens.
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    token = auth_header.split(" ", 1)[1]

    try:
        signing_key = _jwks_client.get_signing_key_from_jwt(token)
        return jwt.decode(
            token,
            signing_key.key,
            algorithms=["ES256", "RS256"],
            audience="authenticated",
        )
    except Exception:
        pass

    try:
        return jwt.decode(
            token,
            SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            audience="authenticated",
        )
    except Exception:
        return None


def get_profile(user_id):
    res = sb.table("profiles").select("*").eq("id", user_id).single().execute()
    return res.data


def require_auth(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        payload = verify_token()
        if not payload:
            return jsonify({"error": "Tizimga kirish talab qilinadi"}), 401
        request.user_id = payload["sub"]
        request.user_email = payload.get("email")
        return f(*args, **kwargs)
    return wrapper


def require_admin(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        payload = verify_token()
        if not payload:
            return jsonify({"error": "Tizimga kirish talab qilinadi"}), 401
        profile = get_profile(payload["sub"])
        if not profile or profile.get("role") != "admin":
            return jsonify({"error": "Faqat admin uchun"}), 403
        request.user_id = payload["sub"]
        return f(*args, **kwargs)
    return wrapper


# ---------------------------------------------------------------------
# ME (current user's profile — used by frontend to show name + admin button)
# ---------------------------------------------------------------------
@app.get("/api/me")
@require_auth
def me():
    profile = get_profile(request.user_id)
    if not profile:
        return jsonify({"error": "Profil topilmadi"}), 404
    return jsonify(profile)


# ---------------------------------------------------------------------
# LISTINGS
# ---------------------------------------------------------------------
@app.get("/api/listings")
def list_listings():
    """Public catalog — only active listings, optionally filtered by rank/hero search."""
    q = sb.table("listings").select(
        "*, profiles!listings_seller_id_fkey(name,email), listing_photos(photo_url,position)"
    ).eq("status", "active").order("id", desc=True)

    rank = request.args.get("rank")
    if rank and rank != "all":
        q = q.eq("rank", rank)

    res = q.execute()
    data = res.data or []

    search = (request.args.get("q") or "").strip().lower()
    if search:
        data = [
            l for l in data
            if search in l["title"].lower()
            or any(search in h.lower() for h in l.get("heroes", []))
        ]
    return jsonify(data)


@app.get("/api/listings/<int:listing_id>")
def get_listing(listing_id):
    res = sb.table("listings").select(
        "*, profiles!listings_seller_id_fkey(name,email), listing_photos(photo_url,position)"
    ).eq("id", listing_id).single().execute()
    if not res.data:
        return jsonify({"error": "Topilmadi"}), 404
    return jsonify(res.data)


@app.post("/api/listings")
@require_auth
def create_listing():
    """
    Body: { title, price, rank, heroes: [...], comment, main_photo_index,
            photo_urls: [...] }  (photo_urls come from uploading directly
    to the Supabase Storage 'listing-photos' bucket from the frontend first,
    then just passing the resulting public URLs here.)
    """
    body = request.get_json(force=True)
    listing = sb.table("listings").insert({
        "seller_id": request.user_id,
        "title": body.get("title", "Nomsiz e'lon")[:200],
        "price": int(body.get("price", 0)),
        "rank": body.get("rank", "master"),
        "heroes": body.get("heroes", []),
        "comment": body.get("comment", ""),
        "main_photo_index": int(body.get("main_photo_index", 0)),
    }).execute().data[0]

    photo_urls = body.get("photo_urls", [])
    if photo_urls:
        sb.table("listing_photos").insert([
            {"listing_id": listing["id"], "photo_url": url, "position": i}
            for i, url in enumerate(photo_urls)
        ]).execute()

    return jsonify(listing), 201


@app.get("/api/my-listings")
@require_auth
def my_listings():
    res = sb.table("listings").select(
        "*, listing_photos(photo_url,position), delete_requests(status)"
    ).eq("seller_id", request.user_id).order("id", desc=True).execute()
    return jsonify(res.data or [])


# ---------------------------------------------------------------------
# "SOTILDI" SO'ROV OQIMI
# ---------------------------------------------------------------------
@app.post("/api/listings/<int:listing_id>/request-sold")
@require_auth
def request_sold(listing_id):
    listing = sb.table("listings").select("*").eq("id", listing_id).single().execute().data
    if not listing or listing["seller_id"] != request.user_id:
        return jsonify({"error": "Bu sizning e'loningiz emas"}), 403

    existing = sb.table("delete_requests").select("*") \
        .eq("listing_id", listing_id).eq("status", "pending").execute().data
    if existing:
        return jsonify({"error": "So'rov allaqachon yuborilgan"}), 409

    req = sb.table("delete_requests").insert({
        "listing_id": listing_id,
        "requested_by": request.user_id,
    }).execute().data[0]
    sb.table("listings").update({"status": "pending_delete"}).eq("id", listing_id).execute()
    return jsonify(req), 201


@app.get("/api/admin/requests")
@require_admin
def admin_list_requests():
    res = sb.table("delete_requests").select(
        "*, listings(id,title,num:id,price)"
    ).eq("status", "pending").order("id").execute()
    return jsonify(res.data or [])


@app.post("/api/admin/requests/<int:req_id>/approve")
@require_admin
def admin_approve(req_id):
    req = sb.table("delete_requests").select("*").eq("id", req_id).single().execute().data
    if not req:
        return jsonify({"error": "Topilmadi"}), 404
    sb.table("listings").update({"status": "sold"}).eq("id", req["listing_id"]).execute()
    sb.table("delete_requests").update({"status": "approved"}).eq("id", req_id).execute()
    return jsonify({"ok": True})


@app.post("/api/admin/requests/<int:req_id>/reject")
@require_admin
def admin_reject(req_id):
    req = sb.table("delete_requests").select("*").eq("id", req_id).single().execute().data
    if not req:
        return jsonify({"error": "Topilmadi"}), 404
    sb.table("listings").update({"status": "active"}).eq("id", req["listing_id"]).execute()
    sb.table("delete_requests").update({"status": "rejected"}).eq("id", req_id).execute()
    return jsonify({"ok": True})


# ---------------------------------------------------------------------
# CHATS — Flask only creates the chat row (needs the RLS-safe combination
# of buyer/seller); actual messages are read/written by the frontend
# directly against Supabase using Realtime.
# ---------------------------------------------------------------------
@app.post("/api/listings/<int:listing_id>/start-chat")
@require_auth
def start_chat(listing_id):
    listing = sb.table("listings").select("*").eq("id", listing_id).single().execute().data
    if not listing:
        return jsonify({"error": "Topilmadi"}), 404
    if listing["seller_id"] == request.user_id:
        return jsonify({"error": "O'z e'loningizga xaridor sifatida kira olmaysiz"}), 400

    existing = sb.table("chats").select("*") \
        .eq("listing_id", listing_id).eq("buyer_id", request.user_id).execute().data
    if existing:
        return jsonify(existing[0])

    chat = sb.table("chats").insert({
        "listing_id": listing_id,
        "buyer_id": request.user_id,
        "seller_id": listing["seller_id"],
    }).execute().data[0]

    sb.table("chat_messages").insert({
        "chat_id": chat["id"],
        "sender_id": request.user_id,
        "sender_role": "admin",
        "content": "Admin chatga qo'shildi. Adminsiz olingan har bir akkauntga biz javob bermaymiz.",
    }).execute()

    return jsonify(chat), 201


@app.get("/api/my-chats")
@require_auth
def my_chats():
    res = sb.table("chats").select(
        "*, listings(id,title), buyer:profiles!chats_buyer_id_fkey(name,email), seller:profiles!chats_seller_id_fkey(name,email)"
    ).or_(f"buyer_id.eq.{request.user_id},seller_id.eq.{request.user_id}").execute()
    return jsonify(res.data or [])


@app.get("/api/admin/chats")
@require_admin
def admin_chats():
    res = sb.table("chats").select(
        "*, listings(id,title), buyer:profiles!chats_buyer_id_fkey(name,email), seller:profiles!chats_seller_id_fkey(name,email)"
    ).order("id", desc=True).execute()
    return jsonify(res.data or [])


# ---------------------------------------------------------------------
# ADS
# ---------------------------------------------------------------------
@app.get("/api/ads")
def get_ads():
    res = sb.table("ads").select("*").execute()
    return jsonify(res.data or [])


@app.post("/api/admin/ads/<slot>")
@require_admin
def save_ad(slot):
    if slot not in ("top", "bottom"):
        return jsonify({"error": "Noto'g'ri slot"}), 400
    body = request.get_json(force=True)
    sb.table("ads").update({
        "title": body.get("title", ""),
        "subtitle": body.get("subtitle", ""),
        "cta": body.get("cta", "Batafsil"),
        "color1": body.get("color1", "#241a3d"),
        "color2": body.get("color2", "#1a2b2a"),
    }).eq("slot", slot).execute()
    return jsonify({"ok": True})


@app.delete("/api/admin/ads/<slot>")
@require_admin
def clear_ad(slot):
    sb.table("ads").update({"title": None, "subtitle": None, "cta": None}).eq("slot", slot).execute()
    return jsonify({"ok": True})


# ---------------------------------------------------------------------
@app.get("/api/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
