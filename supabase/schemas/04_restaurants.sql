-- restaurants — one per owning auth.users row.
--
-- `shop_timings` exists live even though the original Alembic migration
-- never created it (provisioned out-of-band) — kept here since it reflects
-- the true live column set, which is what a declarative schema must match.
create table restaurants (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null,
  name text not null,
  description text,
  is_open boolean not null default true,
  currency varchar(10) not null default '₹',
  logo_url text,
  image_url text,
  address_line text,
  pincode varchar(20),
  city text,
  state text,
  country text not null default 'India',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  shop_timings json default '{}'::json
);
create index ix_restaurants_owner_id on restaurants (owner_id);
alter table restaurants
  add constraint fk_restaurants_owner_id foreign key (owner_id)
  references auth.users(id) on delete cascade;

alter table restaurants enable row level security;

create policy "restaurants are publicly readable" on restaurants
  for select using (true);

create policy "owner can manage own restaurant" on restaurants for all
  using (owner_id = auth.uid())
  with check (owner_id = auth.uid());
