"""
NITRAGEN backend — Flask + Supabase (Fixed v2)
"""

import os
import jwt
from functools import wraps
from flask import Flask, request, jsonify
from flask_cors import CORS
from supabase import create_client, Client

# Config
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_ROLE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
SUPABASE_JWT_SECRET = os.environ.get("SUPABASE_JWT_SECRET", "")
FRONTEND_ORIGIN = os.environ.get("FRONTEND_ORIGIN", "*")

app = Flask(__name__)
CORS(app, origins=[FRONTEND_ORIGIN] if FRONTEND_ORIGIN != "*" else "*", supports_credentials=True)

sb: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

def verify_token():
    """Supabase access token'ni tekshirish va user_id qaytarish"""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        print("❌ No Authorization header")
        return None
    
    token = auth_header.split(" ", 1)[1]
    print(f"✅ Token received: {token[:50]}...")
    
    # Token'ni decode qilish (algoritmdan qat'i nazar)
    try:
        # HS256 bilan tekshirish
        if SUPABASE_JWT_SECRET:
            decoded = jwt.decode(
                token,
                SUPABASE_JWT_SECRET,
                algorithms=["HS256"],
                options={"verify_aud": False}
            )
            print(f"✅ Decoded with HS256: sub={decoded.get('sub')}")
            return decoded
        
        # Agar secret yo'q bo'lsa, verify qilmasdan decode qilish
        decoded = jwt.decode(token, options={"verify_signature": False})
        print(f"✅ Decoded without verification: sub={decoded.get('sub')}")
        return decoded
        
    except Exception as e:
        print(f"❌ JWT decode error: {e}")
        return None

def get_profile(user_id):
    """User ID bo'yicha profilni olish"""
    try:
        print(f"🔍 Looking for profile: {user_id}")
        res = sb.table("profiles").select("*").eq("id", user_id).single().execute()
        print(f"📄 Profile result: {res.data}")
        return res.data
    except Exception as e:
        print(f"❌ get_profile error: {e}")
        return None

def require_auth(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        payload = verify_token()
        if not payload:
            print("❌ No valid token")
            return jsonify({"error": "Tizimga kirish talab qilinadi"}), 401
        
        # Token'dan user_id ni olish
        user_id = payload.get("sub") or payload.get("user_id")
        if not user_id:
            print(f"❌ Payload: {payload}")
            return jsonify({"error": "Token'da user_id topilmadi"}), 401
        
        request.user_id = user_id
        request.user_email = payload.get("email")
        print(f"✅ Authenticated user: {user_id} ({request.user_email})")
        return f(*args, **kwargs)
    return wrapper

def require_admin(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        payload = verify_token()
        if not payload:
            return jsonify({"error": "Tizimga kirish talab qilinadi"}), 401
        
        user_id = payload.get("sub") or payload.get("user_id")
        if not user_id:
            return jsonify({"error": "Token'da user_id topilmadi"}), 401
        
        request.user_id = user_id
        request.user_email = payload.get("email")
        
        profile = get_profile(user_id)
        if not profile or profile.get("role") != "admin":
            print(f"❌ Not admin: {profile}")
            return jsonify({"error": "Faqat admin uchun"}), 403
        
        print(f"✅ Admin access granted")
        return f(*args, **kwargs)
    return wrapper

# ME endpoint
@app.get("/api/me")
@require_auth
def me():
    try:
        print(f"\n{'='*50}")
        print(f"=== ME ENDPOINT ===")
        print(f"User ID: {request.user_id}")
        print(f"User Email: {request.user_email}")
        
        profile = get_profile(request.user_id)
        
        if not profile:
            print(f" Profile not found in database!")
            print(f"🔄 Creating new profile...")
            
            # Yangi profil yaratish
            try:
                new_profile = sb.table("profiles").insert({
                    "id": request.user_id,
                    "email": request.user_email or "unknown@email.com",
                    "name": "User",
                    "role": "user"
                }).execute()
                
                if new_profile.data:
                    print(f"✅ Profile created: {new_profile.data[0]}")
                    return jsonify(new_profile.data[0])
                else:
                    print(f"❌ Profile creation returned no data")
            except Exception as create_err:
                print(f"❌ Profile creation error: {create_err}")
            
            return jsonify({"error": "Profil yaratib bo'lmadi"}), 404
        
        print(f"✅ Profile found: role={profile.get('role')}")
        print(f"{'='*50}\n")
        return jsonify(profile)
        
    except Exception as e:
        print(f"❌ me endpoint error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": "Ichki xatolik"}), 500

# LISTINGS
@app.get("/api/listings")
def list_listings():
    try:
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
    except Exception as e:
        print(f"list_listings error: {e}")
        return jsonify([])

@app.get("/api/listings/<int:listing_id>")
def get_listing(listing_id):
    try:
        res = sb.table("listings").select(
            "*, profiles!listings_seller_id_fkey(name,email), listing_photos(photo_url,position)"
        ).eq("id", listing_id).single().execute()
        if not res.data:
            return jsonify({"error": "Topilmadi"}), 404
        return jsonify(res.data)
    except Exception as e:
        print(f"get_listing error: {e}")
        return jsonify({"error": "Topilmadi"}), 404

@app.post("/api/listings")
@require_auth
def create_listing():
    try:
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
    except Exception as e:
        print(f"create_listing error: {e}")
        return jsonify({"error": "E'lon yaratishda xatolik"}), 500

@app.get("/api/my-listings")
@require_auth
def my_listings():
    try:
        res = sb.table("listings").select(
            "*, listing_photos(photo_url,position), delete_requests(status)"
        ).eq("seller_id", request.user_id).order("id", desc=True).execute()
        return jsonify(res.data or [])
    except Exception as e:
        print(f"my_listings error: {e}")
        return jsonify([])

# SOTILGAN E'LONNI O'CHIRISH
@app.delete("/api/listings/<int:listing_id>")
@require_auth
def delete_listing(listing_id):
    try:
        listing = sb.table("listings").select("*").eq("id", listing_id).single().execute().data
        if not listing:
            return jsonify({"error": "Topilmadi"}), 404
        if listing["seller_id"] != request.user_id:
            return jsonify({"error": "Bu sizning e'loningiz emas"}), 403
        if listing["status"] != "sold":
            return jsonify({"error": "Faqat sotilgan e'lonlarni o'chirish mumkin"}), 400
        
        sb.table("listings").delete().eq("id", listing_id).execute()
        return jsonify({"ok": True, "message": "E'lon o'chirildi"})
    except Exception as e:
        print(f"delete_listing error: {e}")
        return jsonify({"error": "O'chirishda xatolik"}), 500

# SOTILDI SO'ROV
@app.post("/api/listings/<int:listing_id>/request-sold")
@require_auth
def request_sold(listing_id):
    try:
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
    except Exception as e:
        print(f"request_sold error: {e}")
        return jsonify({"error": "So'rov yuborishda xatolik"}), 500

@app.get("/api/admin/requests")
@require_admin
def admin_list_requests():
    try:
        res = sb.table("delete_requests").select(
            "*, listings(id,title,price)"
        ).eq("status", "pending").order("id").execute()
        return jsonify(res.data or [])
    except Exception as e:
        print(f"admin_list_requests error: {e}")
        return jsonify([])

@app.post("/api/admin/requests/<int:req_id>/approve")
@require_admin
def admin_approve(req_id):
    try:
        req = sb.table("delete_requests").select("*").eq("id", req_id).single().execute().data
        if not req:
            return jsonify({"error": "Topilmadi"}), 404
        sb.table("listings").update({"status": "sold"}).eq("id", req["listing_id"]).execute()
        sb.table("delete_requests").update({"status": "approved"}).eq("id", req_id).execute()
        return jsonify({"ok": True})
    except Exception as e:
        print(f"admin_approve error: {e}")
        return jsonify({"error": "Tasdiqlashda xatolik"}), 500

@app.post("/api/admin/requests/<int:req_id>/reject")
@require_admin
def admin_reject(req_id):
    try:
        req = sb.table("delete_requests").select("*").eq("id", req_id).single().execute().data
        if not req:
            return jsonify({"error": "Topilmadi"}), 404
        sb.table("listings").update({"status": "active"}).eq("id", req["listing_id"]).execute()
        sb.table("delete_requests").update({"status": "rejected"}).eq("id", req_id).execute()
        return jsonify({"ok": True})
    except Exception as e:
        print(f"admin_reject error: {e}")
        return jsonify({"error": "Bekor qilishda xatolik"}), 500

# CHATS
@app.post("/api/listings/<int:listing_id>/start-chat")
@require_auth
def start_chat(listing_id):
    try:
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
    except Exception as e:
        print(f"start_chat error: {e}")
        return jsonify({"error": "Chat yaratishda xatolik"}), 500

@app.get("/api/my-chats")
@require_auth
def my_chats():
    try:
        res = sb.table("chats").select(
            "*, listings(id,title), buyer:profiles!chats_buyer_id_fkey(name,email), seller:profiles!chats_seller_id_fkey(name,email)"
        ).or_(f"buyer_id.eq.{request.user_id},seller_id.eq.{request.user_id}").execute()
        return jsonify(res.data or [])
    except Exception as e:
        print(f"my_chats error: {e}")
        return jsonify([])

@app.get("/api/admin/chats")
@require_admin
def admin_chats():
    try:
        res = sb.table("chats").select(
            "*, listings(id,title), buyer:profiles!chats_buyer_id_fkey(name,email), seller:profiles!chats_seller_id_fkey(name,email)"
        ).order("id", desc=True).execute()
        return jsonify(res.data or [])
    except Exception as e:
        print(f"admin_chats error: {e}")
        return jsonify([])

# ADS
@app.get("/api/ads")
def get_ads():
    try:
        res = sb.table("ads").select("*").execute()
        return jsonify(res.data or [])
    except Exception as e:
        print(f"get_ads error: {e}")
        return jsonify([])

@app.post("/api/admin/ads/<slot>")
@require_admin
def save_ad(slot):
    try:
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
    except Exception as e:
        print(f"save_ad error: {e}")
        return jsonify({"error": "Reklama saqlashda xatolik"}), 500

@app.delete("/api/admin/ads/<slot>")
@require_admin
def clear_ad(slot):
    try:
        sb.table("ads").update({"title": None, "subtitle": None, "cta": None}).eq("slot", slot).execute()
        return jsonify({"ok": True})
    except Exception as e:
        print(f"clear_ad error: {e}")
        return jsonify({"error": "Reklama o'chirishda xatolik"}), 500

@app.get("/api/health")
def health():
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
