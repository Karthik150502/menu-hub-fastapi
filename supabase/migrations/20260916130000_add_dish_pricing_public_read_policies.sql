-- dishes and item_prices only had an owner-scoped "for all" RLS policy —
-- fine while every read went through the service-role client, but
-- GET /restaurants/{id}/dishes reads through the anon client (like
-- restaurants' own "publicly readable" policy), and RLS was silently
-- returning zero rows for anyone but the restaurant's owner. Mirrors
-- restaurants' "restaurants are publicly readable" policy.

create policy "dishes are publicly readable" on public.dishes for select
  using (true);

create policy "item_prices are publicly readable" on public.item_prices for select
  using (true);
