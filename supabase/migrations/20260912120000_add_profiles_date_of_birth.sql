alter table "public"."profiles" add column "date_of_birth" date;

create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer set search_path = public
as $$
begin
  insert into public.profiles (id, full_name, avatar_url, date_of_birth)
  values (
    new.id,
    new.raw_user_meta_data ->> 'full_name',
    new.raw_user_meta_data ->> 'avatar_url',
    (new.raw_user_meta_data ->> 'date_of_birth')::date
  );
  return new;
end;
$$;
