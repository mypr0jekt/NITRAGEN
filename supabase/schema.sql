-- NITRAGEN — Supabase schema

-- 1. PROFILES
create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  email text unique not null,
  name text,
  avatar_url text,
  role text not null default 'user' check (role in ('user','admin')),
  created_at timestamptz not null default now()
);

create or replace function public.handle_new_user()
returns trigger as $$
begin
  insert into public.profiles (id, email, name, avatar_url)
  values (
    new.id,
    new.email,
    coalesce(new.raw_user_meta_data->>'full_name', new.raw_user_meta_data->>'name'),
    new.raw_user_meta_data->>'avatar_url'
  )
  on conflict (id) do nothing;
  return new;
end;
$$ language plpgsql security definer;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute procedure public.handle_new_user();

-- 2. LISTINGS
create table if not exists public.listings (
  id bigint generated always as identity primary key,
  seller_id uuid not null references public.profiles(id),
  title text not null,
  price integer not null check (price >= 0),
  rank text not null check (rank in ('master','epic','legend','mythic')),
  heroes text[] not null default '{}',
  comment text default '',
  main_photo_index int not null default 0,
  status text not null default 'active' check (status in ('active','pending_delete','sold')),
  created_at timestamptz not null default now()
);

create table if not exists public.listing_photos (
  id bigint generated always as identity primary key,
  listing_id bigint not null references public.listings(id) on delete cascade,
  photo_url text not null,
  position int not null default 0
);

-- 3. DELETE REQUESTS
create table if not exists public.delete_requests (
  id bigint generated always as identity primary key,
  listing_id bigint not null references public.listings(id) on delete cascade,
  requested_by uuid not null references public.profiles(id),
  status text not null default 'pending' check (status in ('pending','approved','rejected')),
  created_at timestamptz not null default now()
);

-- 4. CHATS
create table if not exists public.chats (
  id bigint generated always as identity primary key,
  listing_id bigint not null references public.listings(id),
  buyer_id uuid not null references public.profiles(id),
  seller_id uuid not null references public.profiles(id),
  created_at timestamptz not null default now(),
  unique(listing_id, buyer_id)
);

create table if not exists public.chat_messages (
  id bigint generated always as identity primary key,
  chat_id bigint not null references public.chats(id) on delete cascade,
  sender_id uuid not null references public.profiles(id),
  sender_role text not null check (sender_role in ('buyer','seller','admin')),
  content text not null,
  created_at timestamptz not null default now()
);

-- 5. ADS
create table if not exists public.ads (
  slot text primary key check (slot in ('top','bottom')),
  title text,
  subtitle text,
  cta text,
  color1 text default '#241a3d',
  color2 text default '#1a2b2a',
  updated_at timestamptz not null default now()
);
insert into public.ads (slot) values ('top'),('bottom') on conflict do nothing;

-- ROW LEVEL SECURITY
alter table public.profiles enable row level security;
alter table public.listings enable row level security;
alter table public.listing_photos enable row level security;
alter table public.delete_requests enable row level security;
alter table public.chats enable row level security;
alter table public.chat_messages enable row level security;
alter table public.ads enable row level security;

create or replace function public.is_admin()
returns boolean as $$
  select exists(select 1 from public.profiles where id = auth.uid() and role = 'admin');
$$ language sql stable security definer;

create policy "profiles are readable by anyone logged in" on public.profiles
  for select using (auth.role() = 'authenticated');
create policy "users update own profile" on public.profiles
  for update using (auth.uid() = id);

create policy "active listings are public" on public.listings
  for select using (status = 'active' or seller_id = auth.uid() or public.is_admin());
create policy "sellers create their own listings" on public.listings
  for insert with check (seller_id = auth.uid());
create policy "sellers or admin update listings" on public.listings
  for update using (seller_id = auth.uid() or public.is_admin());

create policy "photos follow listing visibility" on public.listing_photos
  for select using (
    exists(select 1 from public.listings l where l.id = listing_id
           and (l.status = 'active' or l.seller_id = auth.uid() or public.is_admin()))
  );
create policy "sellers add photos to own listings" on public.listing_photos
  for insert with check (
    exists(select 1 from public.listings l where l.id = listing_id and l.seller_id = auth.uid())
  );

create policy "sellers see own delete requests" on public.delete_requests
  for select using (requested_by = auth.uid() or public.is_admin());
create policy "sellers create delete requests for own listings" on public.delete_requests
  for insert with check (
    requested_by = auth.uid()
    and exists(select 1 from public.listings l where l.id = listing_id and l.seller_id = auth.uid())
  );
create policy "admin updates delete requests" on public.delete_requests
  for update using (public.is_admin());

create policy "participants see their chat" on public.chats
  for select using (buyer_id = auth.uid() or seller_id = auth.uid() or public.is_admin());
create policy "buyer starts a chat" on public.chats
  for insert with check (buyer_id = auth.uid());

create policy "participants read chat messages" on public.chat_messages
  for select using (
    exists(select 1 from public.chats c where c.id = chat_id
           and (c.buyer_id = auth.uid() or c.seller_id = auth.uid() or public.is_admin()))
  );
create policy "participants send chat messages" on public.chat_messages
  for insert with check (
    sender_id = auth.uid()
    and exists(select 1 from public.chats c where c.id = chat_id
           and (c.buyer_id = auth.uid() or c.seller_id = auth.uid() or public.is_admin()))
  );

create policy "ads are public" on public.ads for select using (true);
create policy "admin manages ads" on public.ads for update using (public.is_admin());

-- REALTIME
alter publication supabase_realtime add table public.chat_messages;

-- STORAGE
insert into storage.buckets (id, name, public)
values ('listing-photos', 'listing-photos', true)
on conflict (id) do nothing;

create policy "anyone can view listing photos" on storage.objects
  for select using (bucket_id = 'listing-photos');
create policy "authenticated users upload listing photos" on storage.objects
  for insert with check (bucket_id = 'listing-photos' and auth.role() = 'authenticated');

-- ADMIN QILISH (o'zingizning emailingizni qo'ying)
-- UPDATE public.profiles SET role = 'admin' WHERE email = 'abbosxojavaqqosov@gmail.com';
