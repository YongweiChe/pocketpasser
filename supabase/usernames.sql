-- Usernames (unique, case-insensitive), replacing the Google name everywhere. Run after schema.sql.
alter table public.profiles add column if not exists username text;
alter table public.profiles alter column display_name drop not null;
update public.profiles set display_name = null;   -- stop keeping the Google name
alter table public.profiles drop constraint if exists username_format;
alter table public.profiles add constraint username_format check (username is null or username ~ '^[A-Za-z0-9_]{3,16}$');
create unique index if not exists profiles_username_lower on public.profiles (lower(username));

-- availability check for the picker (profiles are private, so this answers yes/no without exposing rows)
create or replace function public.username_available(name text) returns boolean
  language sql security definer set search_path = public stable
  as $$ select name ~ '^[A-Za-z0-9_]{3,16}$' and not exists (select 1 from public.profiles where lower(username) = lower(name) and id is distinct from auth.uid()) $$;
grant execute on function public.username_available(text) to anon, authenticated;

-- the board always shows the poster's current username (set by the database, not the browser)
create or replace function public.board_name() returns trigger
  language plpgsql security definer set search_path = public
  as $$ begin new.name := coalesce((select username from public.profiles where id = new.user_id), 'Player'); return new; end $$;
drop trigger if exists daily_scores_name on public.daily_scores;
create trigger daily_scores_name before insert on public.daily_scores for each row execute function public.board_name();

-- renaming updates your past board entries
create or replace function public.sync_board_name() returns trigger
  language plpgsql security definer set search_path = public
  as $$ begin if new.username is distinct from old.username and new.username is not null then
    update public.daily_scores set name = new.username where user_id = new.id; end if; return new; end $$;
drop trigger if exists profiles_sync_board on public.profiles;
create trigger profiles_sync_board after update of username on public.profiles for each row execute function public.sync_board_name();
