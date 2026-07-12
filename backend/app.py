
Claude finished the response
nitragen-1.onrender.com/api/me:1          Failed to load resource: the server responded with a status of 401 ()
nitragen-1.onrender.com/api/me:1          Failed to load resource: the server responded with a status of 401 ()
nitragen-1.onrender.com/api/me:1          Failed to load resource: the server responded with a status of 401 ()
nitragen-1.onrender.com/api/my-listings:1          Failed to load resource: the server responded with a status of 401 ()
nitragen-1.onrender.com/api/my-chats:1          Failed to load resource: the server responded with a status of 401 ()
nitragen-1.onrender.com/api/me:1          Failed to load resource: the server responded with a status of 401 ()
nitragen-1.onrender.com/api/me:1          Failed to load resource: the server responded with a status of 401 ()

Show more

Diagnosed JWT verification mismatch and devised JWKS-based solution
Diagnosed JWT verification mismatch and devised JWKS-based solution
Ajoyib — bu xato bizga aniq nima bo'layotganini ko'rsatadi. Sabab topildi: sizning Supabase loyihangiz JWT tokenlarni yangi (ECC/ES256) kalit bilan imzolayapti, backend kodimiz esa faqat eski (HS256) legacy secret bilan tekshirishga mo'ljallangan edi — shuning uchun tekshiruv muvaffaqiyatsiz tugab, 401 chiqyapti.

Buni tuzatamiz — backend kodini Supabase'ning JWKS (ochiq kalitlar) orqali tekshiradigan qilib o'zgartiramiz, bu har qanday kalit turi (eski ham, yangi ham) bilan ishlaydi.

1. backend/requirements.txt faylini oching (GitHub'da) va shunga o'zgartiring:


Viewed a file, edited a file
Viewed a file, edited a file
Endi backend/app.py faylidagi token-tekshirish qismini yangilaymiz:


Viewed a file, edited a file, ran a command
Viewed a file, edited a file, ran a command
Endi bu ikkita faylni GitHub'da yangilaymiz:


Get full updated app.py content to share with user
Get full updated app.py content to share with user
Endi GitHub'da yangilash uchun aniq yo'riqnoma:

1. backend/app.py faylini oching, tahrirlash rejimiga o'ting (✏️ Edit), va faylning yuqori qismini (import va konfiguratsiya qismini) quyidagiga almashtiring:

Eski qismni (import os dan def get_profile gacha) topib, o'rniga shuni qo'ying:


Show the exact block to paste for GitHub edit
Show the exact block to paste for GitHub edit
Kodni boshqa joylasam boladimi ulani oʻchirib


Tasdiqladi kod oʻchirish va almashtirish usuli
Tasdiqladi kod oʻchirish va almashtirish usuli
Ha, aynan shunday qilinadi — bu to'g'ri usul.

GitHub tahrirlash oynasida:

Faylda 1-qatordan boshlab, def get_profile(user_id): qatorigacha bo'lgan qismni (ya'ni import os dan boshlab, eski verify_token funksiyasi tugagunga qadar) belgilang (bosib turib pastga suring, yoki qator raqamlariga bosib diapazon tanlang)
Belgilangan qismni o'chiring (Delete yoki Backspace)
O'sha bo'sh joyga, men yuqorida ko'rsatgan yangi kodni joylashtiring (paste):
python
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
Uning darhol pastida def get_profile(user_id): funksiyasi va qolgan barcha kod tegilmagan holda davom etishi kerak — faqat yuqori qismini almashtirdik, pastdagi barcha @app.get, @app.post funksiyalari joyida qoladi.
Pastga tushib "Commit changes" tugmasini bosing.
⚠️ Diqqat: requirements.txt faylini ham yangilashni unutmang — u yerga cryptography==43.0.1 qatorini qo'shishingiz kerak (jwt kutubxonasiga ES256 tekshiruvi uchun kerak). Hozircha shu faylni ham ochib tekshirib qo'yaylikmi?

1000000477.jpg
Yoq menga boshqa yozib ber huddi shu rasmdagidek 
Faqat pastida bosh sahifa qidiruv bolimi profil va chatlarim bolsin kegin xuddi telegramdagidek chatlarni aloxida qilsa boladimi yo qiyin bolib ketadimi


Architected bottom navigation redesign with tab-based messaging interface
Architected bottom navigation redesign with tab-based messaging interface
Bu chindan ham qilsa bo'ladigan narsa — Telegram uslubidagi alohida "Chatlarim" bo'limi unchalik qiyin emas, chunki backend'da buning uchun kerakli narsa (/api/my-chats) allaqachon bor. Saytni pastki menyu (Bosh sahifa, Qidiruv, Chatlarim, Profil) bilan qayta tuzib beraman.


Architekturasiini qayta tuzdi: pastki navigatsiya, sahifalar va chat integratsiyasi
Architekturasiini qayta tuzdi: pastki navigatsiya, sahifalar va chat integratsiyasi
Endi header'ni soddalashtiramiz va bosh sahifa/qidiruv/chatlarim/profil sahifalariga bo'lamiz:


Refactored UI layout by consolidating redundant profile sections
Refactored UI layout by consolidating redundant profile sections
Endi eski "Sotuvchi paneli" to'liq sahifali overlay'ni olib tashlaymiz (endi u Profil bo'limiga ko'chirildi):


Edited a file, ran a command
Edited a file, ran a command
Endi JS qismini yangilaymiz — loadMe(), openProfile/renderProfile, va yangi switchTab(), renderChatsList() funksiyalarini qo'shamiz:


Viewed a file, edited a file
Viewed a file, edited a file
Endi eski openProfile/renderProfile funksiyalarini yangi sahifa tuzilishiga moslashtiramiz:


Funktsiyalarni birlashtirish uchun kodni yangilash kerak edi
Funktsiyalarni birlashtirish uchun kodni yangilash kerak edi
Endi switchTab'ning "profile" bo'limini renderProfile()ni ham chaqiradigan qilib to'g'irlaymiz:


Edited a file, ran a command
Edited a file, ran a command
Toza, hech qanday eski havola qolmagan. Endi faylni sintaksis xatolarga tekshiramiz va yakuniy sozlamalarni bajaramiz:


Ran 2 commands
Ran 2 commands
Zo'r — barcha ID'lar noyob, ikkita marta takrorlanmagan. Endi to'liq faylni yakuniy tekshiramiz va foydalanuvchiga taqdim qilamiz:


Assembled configuration details while acknowledging missing authentication credentials
Assembled configuration details while acknowledging missing authentication credentials
Endi faylni tayyorlab, taqdim qilaman:


Ran a command, read a file
Ran a command, read a file
Ha, ishlaydi va qiyin emas — tayyorladim. Uch faylni bir vaqtda tuzatdim:

1. Yangi dizayn — pastki menyu (Uzum uslubida):

🏠 Bosh sahifa — geroy banner + katalog
🔍 Qidiruv — qidiruv maydoniga darhol tushiradi
💬 Chatlarim — Telegram uslubida, barcha suhbatlaringiz ro'yxati bitta joyda (xarid/sotuv sifatida belgilangan), bosilsa to'g'ridan-to'g'ri o'sha chat ochiladi
👤 Profil — endi alohida oyna emas, pastki menyudagi doimiy bo'lim: login holati, statistika, e'lonlaringiz, admin panel tugmasi (agar siz bo'lsangiz)
2. Backend tuzatildi — avvalgi 401 xatosi uchun (JWKS orqali tekshirish, ilgari aytganimizdek)

Endi GitHub'da almashtirish kerak bo'lgan fayllar:

frontend/index.html — butunlay almashtiring (nitragen-frontend-v2 fayli bilan). Faylni ochib, ichida faqat bitta joyni to'ldirishingiz kerak:
   const SUPABASE_ANON_KEY = "YOUR-PUBLIC-ANON-KEY";
— shu yerga o'zingizning anon key'ingizni qo'ying (URL va API_BASE allaqachon to'ldirilgan).

backend/app.py — butunlay almashtiring (app-fixed fayli bilan, 401 xatosi tuzatilgan)
backend/requirements.txt — butunlay almashtiring (requirements-fixed fayli bilan, cryptography kutubxonasi qo'shilgan)
GitHub'da har birini oching → ✏️ Edit → ichidagi hammasini o'chirib (Ctrl+A, Delete) → yangi faylning mazmunini joylashtiring → Commit changes. Uchalasini ham qilib bo'lgach, Render avtomatik qayta deploy qiladi (backend uchun bir necha daqiqa kutish kerak).


Nitragen frontend v2
Code · HTML 

App fixed
PY 

Requirements fixed
TXT 
Men xali xam xamma chatlarni kuzata olamana


Tekshirdi admin panelining chat kuzatish xususiyati saqlanganligini
Tekshirdi admin panelining chat kuzatish xususiyati saqlanganligini
Ha, albatta — bu funksiya yo'qolmagan, faqat joyi biroz o'zgargan. Tushuntirib beray:

Admin sifatida siz ikki joydan chatlarni kuzata olasiz:

Admin panel → "Chatlarni tekshirish" bo'limi — bu yerda barcha foydalanuvchilarning (hamma sotuvchi-xaridor juftliklarining) chatlari ro'yxati chiqadi, istalganini bosib kirib, kuzatib turishingiz va yozishingiz mumkin (bu — avvalgidek ishlaydi, o'zgarmagan)
Yangi "Chatlarim" bo'limi (pastki menyu) — bu esa faqat sizning shaxsiy ishtirokingizdagi chatlarni ko'rsatadi (agar siz o'zingiz xaridor yoki sotuvchi sifatida qatnashgan bo'lsangiz)
Ya'ni:

"Chatlarim" (pastki menyu) = sizning shaxsiy suhbatlaringiz
"Admin panel → Chatlarni tekshirish" = saytdagi hammaning suhbatlari, nazorat uchun
Ikkalasi ham ishlaydi va bir-biriga to'siq bo'lmaydi. Profil bo'limiga kirib, "🛡 Admin panelni ochish" tugmasini bossangiz, o'sha yerdan barcha chatlarni kuzatishda davom etaverasiz — bu funksiyaga hech narsa o'zgartirmadim, faqat "Chatlarim" degan yangi, qo'shimcha bo'limni qo'shdim.

xamma faylarni ochirib shu uchalasini qosha veraymi


Weighed selective file updates against complete deletion risks
Weighed selective file updates against complete deletion risks
Yo'q, hammasini o'chirmang! Faqat shu 3 ta faylni almashtirish kifoya, qolganlariga tegmang.

Aniq nima qilish kerak:

Repo'ingizda hozir bunday fayllar bor:

backend/
  app.py          ← ALMASHTIRING (app-fixed bilan)
  requirements.txt ← ALMASHTIRING (requirements-fixed bilan)
  Procfile         ← TEGMANG, o'zgarishsiz qoladi
  .env.example     ← TEGMANG
frontend/
  index.html       ← ALMASHTIRING (nitragen-frontend-v2 bilan)
supabase/
  schema.sql       ← TEGMANG
README.md          ← TEGMANG
.gitignore         ← TEGMANG
Har biri uchun:

GitHub'da o'sha faylni oching (masalan backend/app.py)
✏️ Edit tugmasini bosing
Ichidagi eski matnni butunlay belgilab (Ctrl+A) o'chiring
Yangi faylning to'liq matnini joylashtiring
Commit changes
Shuni faqat 3 marta (uchala fayl uchun alohida-alohida) qiling. Qolgan fayllarga (Procfile, .env.example, schema.sql, README.md, .gitignore) umuman tegmang — ular allaqachon to'g'ri va o'zgarishsiz qolishi kerak.

Yangi fayl qo'shish yoki "Upload files" orqali yuklash shart emas — mavjud fayllarni tahrirlash (Edit) orqali ichidagi matnni almashtirasiz, xolos.







Claude is AI and can make mistakes. Please double-check responses.
App fixed · PY
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
 
