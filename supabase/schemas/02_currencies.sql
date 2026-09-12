-- currencies — small reference table of supported currency codes.
-- RLS is enabled with zero policies (service_role only); no client reads
-- this table directly today.
--
-- Seed rows (INR/USD/EUR/GBP/AED) are NOT declared here — declarative
-- schema files describe structure, not data. They live in
-- supabase/migrations/20260829150418_seed_currencies.sql (already applied)
-- and, going forward, new seed data belongs in supabase/seed.sql.

create table currencies (
  code text primary key default 'INR',
  symbol text not null default '₹',
  created_at timestamptz not null default now()
);
alter table currencies enable row level security;
