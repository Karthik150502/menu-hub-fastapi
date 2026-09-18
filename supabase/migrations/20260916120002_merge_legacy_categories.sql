-- Dishes seeded before the categories table existed used lowercase
-- slug-style labels (non-veg, veg, beverages, deserts, chinese, chats,
-- liqour). The previous migration's backfill turned those into their own
-- category rows, separate from the Title-Case labels seeded from
-- constants/data/mode-data-categories.json in the migration right before
-- this one. Re-point those dishes at the matching Title-Case row and drop
-- the now-orphaned lowercase rows, so ?category=Non Veg actually matches
-- dishes that predate this feature.

with pairs (old_label, new_label) as (
  values
    ('non-veg', 'Non Veg'),
    ('veg', 'Veg'),
    ('beverages', 'Beverages'),
    ('deserts', 'Deserts'),
    ('chinese', 'Chinese'),
    ('chats', 'Chats'),
    ('liqour', 'Liqour/ Alcholol')
)
update public.dishes d
set category_id = new_c.id
from pairs p
join public.categories old_c on old_c.label = p.old_label
join public.categories new_c on new_c.label = p.new_label
where d.category_id = old_c.id;

with pairs (old_label, new_label) as (
  values
    ('non-veg', 'Non Veg'),
    ('veg', 'Veg'),
    ('beverages', 'Beverages'),
    ('deserts', 'Deserts'),
    ('chinese', 'Chinese'),
    ('chats', 'Chats'),
    ('liqour', 'Liqour/ Alcholol')
)
delete from public.categories c
using pairs p
where c.label = p.old_label;
