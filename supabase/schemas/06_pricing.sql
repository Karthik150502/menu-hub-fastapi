-- item_prices — one-to-one priced snapshot of a dish (base price, discount,
-- computed final price/tax total).
create table item_prices (
  id uuid primary key default gen_random_uuid(),
  dish_id uuid not null unique references dishes(id) on delete cascade,
  base_price numeric(10,2) not null,
  currency_code text not null references currencies(code),
  total_tax_amount numeric(10,2) not null default 0,
  final_price numeric(10,2) not null,
  mrp numeric(10,2),
  discount_type text,
  discount_on text,
  discount_value numeric(10,2),
  discount_label text,
  discount_valid_from timestamptz,
  discount_valid_until timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint chk_discount_consistent check (
    (discount_type is null and discount_on is null and discount_value is null)
    or (discount_type is not null and discount_on is not null and discount_value is not null)
  ),
  check (discount_type in ('percentage', 'fixed')),
  check (discount_on in ('basePrice', 'priceIncludingTaxes'))
);
create index idx_item_prices_dish on item_prices (dish_id);
create trigger trg_item_prices_updated_at
  before update on item_prices
  for each row execute function set_updated_at();
alter table item_prices enable row level security;
create policy "owner can manage own item_prices" on item_prices for all
  using (dish_id in (
    select id from dishes where restaurant_id in (select id from restaurants where owner_id = auth.uid())
  ))
  with check (dish_id in (
    select id from dishes where restaurant_id in (select id from restaurants where owner_id = auth.uid())
  ));

-- Keeps dishes.base_price mirrored from item_prices.base_price (the source
-- of truth once a dish has been priced).
create or replace function sync_dish_base_price()
returns trigger as $$
begin
  update dishes
  set base_price = new.base_price, updated_at = now()
  where id = new.dish_id
    and base_price is distinct from new.base_price;
  return new;
end;
$$ language plpgsql;

create trigger trg_item_prices_sync_dish_base_price
  after insert or update of base_price on item_prices
  for each row execute function sync_dish_base_price();

-- tax_line_items — one-to-one breakdown of item_prices.total_tax_amount.
create table tax_line_items (
  id uuid primary key default gen_random_uuid(),
  item_price_id uuid not null unique references item_prices(id) on delete cascade,
  total_tax_amount numeric(10,2) not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create trigger trg_tax_line_items_updated_at
  before update on tax_line_items
  for each row execute function set_updated_at();
alter table tax_line_items enable row level security;
create policy "owner can manage own tax_line_items" on tax_line_items for all
  using (item_price_id in (
    select ip.id from item_prices ip
    join dishes d on d.id = ip.dish_id
    where d.restaurant_id in (select id from restaurants where owner_id = auth.uid())
  ))
  with check (item_price_id in (
    select ip.id from item_prices ip
    join dishes d on d.id = ip.dish_id
    where d.restaurant_id in (select id from restaurants where owner_id = auth.uid())
  ));

-- tax_line_item_groups — which tax_groups apply to a tax_line_item, and
-- how much each contributed.
create table tax_line_item_groups (
  tax_line_item_id uuid not null references tax_line_items(id) on delete cascade,
  tax_group_id bigint not null references tax_groups(id) on delete restrict,
  computed_amount numeric(10,2) not null default 0,
  primary key (tax_line_item_id, tax_group_id)
);
alter table tax_line_item_groups enable row level security;
create policy "owner can manage own tax_line_item_groups" on tax_line_item_groups for all
  using (tax_line_item_id in (
    select tli.id from tax_line_items tli
    join item_prices ip on ip.id = tli.item_price_id
    join dishes d on d.id = ip.dish_id
    where d.restaurant_id in (select id from restaurants where owner_id = auth.uid())
  ))
  with check (tax_line_item_id in (
    select tli.id from tax_line_items tli
    join item_prices ip on ip.id = tli.item_price_id
    join dishes d on d.id = ip.dish_id
    where d.restaurant_id in (select id from restaurants where owner_id = auth.uid())
  ));

-- tax_line_item_taxes — which individual item_taxes apply directly to a
-- tax_line_item (outside of a tax_group), and how much each contributed.
create table tax_line_item_taxes (
  tax_line_item_id uuid not null references tax_line_items(id) on delete cascade,
  item_tax_id bigint not null references item_taxes(id) on delete restrict,
  computed_amount numeric(10,2) not null default 0,
  primary key (tax_line_item_id, item_tax_id)
);
alter table tax_line_item_taxes enable row level security;
create policy "owner can manage own tax_line_item_taxes" on tax_line_item_taxes for all
  using (tax_line_item_id in (
    select tli.id from tax_line_items tli
    join item_prices ip on ip.id = tli.item_price_id
    join dishes d on d.id = ip.dish_id
    where d.restaurant_id in (select id from restaurants where owner_id = auth.uid())
  ))
  with check (tax_line_item_id in (
    select tli.id from tax_line_items tli
    join item_prices ip on ip.id = tli.item_price_id
    join dishes d on d.id = ip.dish_id
    where d.restaurant_id in (select id from restaurants where owner_id = auth.uid())
  ));

-- Keeps tax_line_items.total_tax_amount and item_prices.total_tax_amount in
-- sync with the sum of tax_line_item_groups + tax_line_item_taxes.
create or replace function refresh_tax_line_item_total()
returns trigger as $$
declare
  affected_line uuid := coalesce(new.tax_line_item_id, old.tax_line_item_id);
  new_total numeric(10,2);
  affected_price uuid;
begin
  select coalesce(sum(computed_amount), 0) into new_total from (
    select computed_amount from tax_line_item_groups where tax_line_item_id = affected_line
    union all
    select computed_amount from tax_line_item_taxes where tax_line_item_id = affected_line
  ) t;

  update tax_line_items set total_tax_amount = new_total, updated_at = now()
  where id = affected_line
  returning item_price_id into affected_price;

  update item_prices set total_tax_amount = new_total, updated_at = now()
  where id = affected_price;

  return null;
end;
$$ language plpgsql;

create trigger trg_tax_line_item_groups_refresh
  after insert or update or delete on tax_line_item_groups
  for each row execute function refresh_tax_line_item_total();
create trigger trg_tax_line_item_taxes_refresh
  after insert or update or delete on tax_line_item_taxes
  for each row execute function refresh_tax_line_item_total();
