-- Adds a categories table so dishes reference a shared category list
-- instead of a free-text label, and swaps dishes.category (text) for
-- dishes.category_id (uuid, fk to categories). Hand-written rather than
-- `supabase db diff`-generated — no local Supabase/Docker stack available
-- in the environment this was authored in — so double-check it against a
-- diff before relying on it as the sole source of truth.

create table "public"."categories" (
    "id" uuid not null default gen_random_uuid(),
    "label" text not null,
    "created_at" timestamptz not null default now()
);

CREATE UNIQUE INDEX categories_pkey ON public.categories USING btree (id);
CREATE UNIQUE INDEX categories_label_key ON public.categories USING btree (label);

alter table "public"."categories" add constraint "categories_pkey" PRIMARY KEY using index "categories_pkey";
alter table "public"."categories" add constraint "categories_label_key" UNIQUE using index "categories_label_key";

alter table "public"."categories" enable row level security;

create policy "categories are publicly readable" on "public"."categories" for select
  using (true);

-- Backfill: one categories row per distinct dishes.category value already
-- in use, so existing dishes have somewhere to point before the old
-- column is dropped below.
insert into public.categories (label)
select distinct category from public.dishes
on conflict (label) do nothing;

alter table "public"."dishes" add column "category_id" uuid;

update public.dishes d
set category_id = c.id
from public.categories c
where c.label = d.category;

alter table "public"."dishes" alter column "category_id" set not null;
alter table "public"."dishes" add constraint "dishes_category_id_fkey"
  foreign key (category_id) references public.categories(id);

drop index if exists "public"."idx_dishes_category";
alter table "public"."dishes" drop column "category";
create index "idx_dishes_category" on public.dishes using btree (restaurant_id, category_id);
