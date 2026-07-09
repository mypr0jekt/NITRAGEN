# NITRAGEN — Oyin akkauntlari bozori

MLBB va boshqa oyin akkauntlarini xavfsiz sotish/sotib olish uchun bozor.
Har bir savdo admin ishtirokidagi 3-kishilik maxfiy chatda amalga oshadi.

**Stack:** Flask (backend/API) + Supabase (Postgres DB, Storage, Realtime chat, Google OAuth) + oddiy HTML/JS frontend.

---

## 1. Supabase loyihasini sozlash (10 daqiqa)

1. [supabase.com](https://supabase.com) → **New project** yarating.
2. Chap menyudan **SQL Editor** → yangi query oching → `supabase/schema.sql` faylining
   **butun mazmunini** joylashtirib **Run** bosing. Bu barcha jadvallarni, xavfsizlik
   qoidalarini (RLS) va `listing-photos` storage bucket'ini yaratadi.
3. **Authentication → Providers → Google**'ni yoqing:
   - Avval [Google Cloud Console](https://console.cloud.google.com/) da OAuth 2.0
     Client ID yarating (Web application), **Authorized redirect URI** sifatida
     Supabase bergan callback URL'ni qo'shing (Supabase shu sahifada ko'rsatadi,
     odatda `https://<project-ref>.supabase.co/auth/v1/callback`).
   - Google'dan olingan **Client ID** va **Client Secret**'ni Supabase'ning
     Google provider sozlamalariga joylashtirib **Save** bosing.
4. **Settings → API** bo'limidan quyidagilarni nusxa oling — ular keyingi
   qadamlarda kerak bo'ladi:
   - `Project URL`
   - `anon public` key
   - `service_role` key (👁‍🗨 **maxfiy**, hech qachon frontendga qo'ymang)
   - `JWT Secret` (**Settings → API → JWT Settings**)
5. Ro'yxatdan bir marta Google orqali o'zingiz kirib chiqing (frontendni ishga
   tushirgach), keyin **SQL Editor**'da o'zingizni admin qilib belgilang:
   ```sql
   update public.profiles set role = 'admin' where email = 'abbosxojavaqqosov@gmail.com';
   ```

---

## 2. Backend (Flask) — Render'ga joylash

1. `backend/` papkasini alohida GitHub repo qilib joylashtiring (yoki shu repo
   ichida subfolder sifatida, Render "Root Directory" ni `backend` qilib
   ko'rsatadi).
2. Render'da **New → Web Service** → repo'ni ulang.
   - **Root Directory:** `backend`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app`
3. **Environment** bo'limiga quyidagi o'zgaruvchilarni qo'shing
   (`.env.example` dagi izohlarga qarang):
   - `SUPABASE_URL`
   - `SUPABASE_SERVICE_ROLE_KEY`
   - `SUPABASE_JWT_SECRET`
   - `FRONTEND_ORIGIN` — frontend joylashgan domen (masalan
     `https://nitragen.onrender.com`), CORS uchun kerak.
4. Deploy qiling. Tayyor bo'lgach `https://<your-backend>.onrender.com/api/health`
   ochib `{"status":"ok"}` chiqishini tekshiring.

---

## 3. Frontend — joylashtirish

`frontend/index.html` — bitta statik fayl, istalgan statik hosting'da ishlaydi
(Render Static Site, Netlify, Vercel, GitHub Pages, yoki Render'ning o'zida
alohida Static Site sifatida).

Joylashtirishdan **oldin** faylning boshidagi (`<head>` ichidagi) uchta qiymatni
o'zingiznikiga almashtiring:

```html
const SUPABASE_URL = "https://YOUR-PROJECT-REF.supabase.co";
const SUPABASE_ANON_KEY = "YOUR-PUBLIC-ANON-KEY";
const API_BASE = "https://your-flask-backend.onrender.com";
```

Bu uchtasi ham **frontendga ochiq ko'rinadi** (brauzer kodini ko'rgan har kim
ko'radi) — bu normal holat: `anon key` maxsus ochiq bo'lish uchun mo'ljallangan,
haqiqiy himoya Supabase'dagi Row Level Security qoidalari orqali ta'minlanadi
(`supabase/schema.sql`dagi `create policy ...` qatorlari).

Render'da statik sayt sifatida joylashtirish:
- **New → Static Site** → repo → **Root Directory:** `frontend` →
  **Publish directory:** `.` (bo'sh joy, chunki bitta fayl).

---

## 4. Google OAuth redirect domenini yangilash

Frontend qaysi domenga joylashgan bo'lsa (masalan `nitragen.onrender.com`),
Supabase **Authentication → URL Configuration** bo'limida **Site URL** va
**Redirect URLs**'ga o'sha domenni qo'shishni unutmang — aks holda Google
login qaytib kelganda xatolik beradi.

---

## Loyiha tuzilishi

```
nitragen/
├── backend/            Flask API (listings, delete-requests, admin, ads)
│   ├── app.py
│   ├── requirements.txt
│   ├── Procfile
│   └── .env.example
├── supabase/
│   └── schema.sql       Jadvallar + RLS + storage bucket — Supabase SQL Editor'da ishga tushiriladi
└── frontend/
    └── index.html        Butun sayt (login, katalog, chat, sotuvchi va admin panellari)
```

## Qanday ishlaydi (qisqacha)

- **Login:** Frontend Supabase'ning o'z Google OAuth oqimini ishlatadi
  (`supabase.auth.signInWithOAuth`). Flask OAuth kodini o'zi bajarmaydi —
  faqat Supabase bergan tokenni tekshiradi.
- **E'lonlar:** Flask API orqali (`/api/listings`) — yaratish, ro'chirish
  so'rovi, admin tasdiqlashi shu yerda ishlaydi (Supabase'ning
  `service_role` kaliti bilan, RLS'ni chetlab o'tib, faqat tekshirilgan
  admin/foydalanuvchi so'rovlariga ruxsat beriladi).
- **Rasm yuklash:** Frontend rasmlarni to'g'ridan-to'g'ri Supabase Storage'ga
  yuklaydi (`listing-photos` bucket), keyin faqat URL manzillarini Flask'ga
  yuboradi.
- **Chat:** To'liq Supabase Realtime orqali, frontend-dan-frontend'ga — Flask
  faqat chatni "boshlash" (buyer+seller+listing bog'lash) uchun kerak,
  keyingi xabarlar RLS qoidalari orqali himoyalangan holda to'g'ridan-to'g'ri
  Supabase'ga yoziladi/o'qiladi.
- **Reklama:** faqat `role='admin'` bo'lgan foydalanuvchi
  `/api/admin/ads/<slot>` orqali yangilay oladi, hammaga `/api/ads` orqali
  ko'rinadi.

## Keyingi qadamlar (agar kerak bo'lsa)

- To'lov integratsiyasi (Payme/Click) — hozircha yo'q, chat orqali qo'lda
  kelishiladi.
- Email/SMS bildirishnomalar (masalan admin panelga yangi so'rov kelganda
  Telegram botga xabar yuborish) — aiogram bot loyihangizga ulash mumkin.
- Rasmlarni yuklashdan oldin siqish/o'lchamini kichraytirish (hozircha
  original hajmda yuklanadi).
