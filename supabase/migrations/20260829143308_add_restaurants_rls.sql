-- restaurants never got RLS in any prior migration (0001, 0002, 0004 all
-- skipped it) — closing that gap. GET /restaurants and GET /restaurants/{id}
-- are public endpoints today (see app/api/v1/endpoints/restaurants.py), so
-- reads stay open; writes are owner-only, mirroring the "owner can manage
-- own X" policies already in place on dishes/item_prices/etc.

alter table restaurants enable row level security;

create policy "restaurants are publicly readable" on restaurants
  for select using (true);

create policy "owner can manage own restaurant" on restaurants for all
  using (owner_id = auth.uid())
  with check (owner_id = auth.uid());
