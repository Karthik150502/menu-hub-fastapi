-- categories — shared menu-category lookup (e.g. "Veg", "Beverages"),
-- referenced by dishes.category_id. Publicly readable so the frontend's
-- category picker / GET /restaurants/{id}/dishes?category= filter can
-- read it without auth; there's no client-facing write path yet, so no
-- insert/update/delete policy.

create table categories (
  id uuid primary key default gen_random_uuid(),
  label text not null unique,
  created_at timestamptz not null default now()
);
alter table categories enable row level security;
create policy "categories are publicly readable" on categories for select
  using (true);
