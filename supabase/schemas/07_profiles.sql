-- profiles — one-to-one app-side profile for each auth.users row, created
-- automatically by the on_auth_user_created trigger below.
create table profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  full_name text,
  avatar_url text,
  is_active boolean not null default true,
  is_superuser boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create trigger trg_profiles_updated_at
  before update on profiles
  for each row execute function set_updated_at();
alter table profiles enable row level security;
create policy "users can view own profile" on profiles
  for select using (auth.uid() = id);
create policy "users can update own profile" on profiles
  for update using (auth.uid() = id) with check (auth.uid() = id);

create or replace function handle_new_user()
returns trigger as $$
begin
  insert into public.profiles (id, full_name, avatar_url)
  values (new.id, new.raw_user_meta_data ->> 'full_name', new.raw_user_meta_data ->> 'avatar_url');
  return new;
end;
$$ language plpgsql security definer set search_path = public;

create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function handle_new_user();
