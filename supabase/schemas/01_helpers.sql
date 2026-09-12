-- Shared trigger helper: keeps `updated_at` current on any table that
-- attaches it via `before update ... execute function set_updated_at()`.

create or replace function set_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;
