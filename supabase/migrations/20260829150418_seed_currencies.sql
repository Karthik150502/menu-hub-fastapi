-- currencies has been empty in the live database this whole time — its
-- seed insert existed in Alembic's 0002_add_menu_pricing_and_tax_tables.py
-- but that migration was `alembic stamp`ped, never actually run (0002's
-- own docstring: every table in it already existed live, so upgrade() was
-- never executed against the real database). The 20260829142751 baseline
-- in this Supabase-CLI history carried the same insert forward but was
-- likewise only marked "applied" via `migration repair`, not executed.
-- Discovered live via dishes.currency_code's FK failing on "INR" not
-- existing — first time anything actually exercised that constraint.

insert into currencies (code, symbol) values
  ('INR', '₹'), ('USD', '$'), ('EUR', '€'), ('GBP', '£'), ('AED', 'AED')
on conflict (code) do nothing;
