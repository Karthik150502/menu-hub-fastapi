-- dishes — menu items belonging to a restaurant.
create table dishes (
  id uuid primary key default gen_random_uuid(),
  restaurant_id uuid not null references restaurants(id) on delete cascade,
  name text not null,
  description text,
  base_price numeric(10,2) not null,
  currency_code text not null default 'INR' references currencies(code),
  category text not null,
  image_url text,
  available boolean not null default true,
  veg boolean not null default true,
  show_in_menu boolean not null default true,
  tag text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index idx_dishes_restaurant on dishes (restaurant_id);
create index idx_dishes_category on dishes (restaurant_id, category);
create trigger trg_dishes_updated_at
  before update on dishes
  for each row execute function set_updated_at();
alter table dishes enable row level security;
create policy "owner can manage own dishes" on dishes for all
  using (restaurant_id in (select id from restaurants where owner_id = auth.uid()))
  with check (restaurant_id in (select id from restaurants where owner_id = auth.uid()));
