-- Seeds the labels from constants/data/mode-data-categories.json (the
-- frontend's mock category list) verbatim, typos and all, so backend and
-- frontend agree on the same category set.

insert into public.categories (label) values
  ('All'),
  ('Non Veg'),
  ('Veg'),
  ('Beverages'),
  ('Deserts'),
  ('Chats'),
  ('Liqour/ Alcholol'),
  ('Chinese')
on conflict (label) do nothing;
