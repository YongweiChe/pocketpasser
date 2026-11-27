-- Pocket Passer accounts + scores. Paste into Supabase: SQL Editor -> New query -> Run.
-- Sign-in is Google OAuth (Supabase Auth); every table is keyed to auth.users and protected by row-level security.

-- one row per player (public display name = first name + last initial, never the email)
create table if not exists public.profiles (
  id uuid primary key references auth.users on delete cascade,
  display_name text not null,
  created_at timestamptz not null default now()
);

-- every finished round (Today's 6, practice, versus, Drew Bledsoe mode)
create table if not exists public.rounds (
  id bigint generated always as identity primary key,
  user_id uuid not null default auth.uid() references auth.users on delete cascade,
  kind text not null check (kind in ('daily','practice','versus','bledsoe')),
  day date not null default current_date,
  qb text,                -- versus: the QB played against
  total numeric not null, -- EPA vs the pros over the round
  wins int,
  n int not null,         -- snaps played (Bledsoe mode: snaps survived)
  created_at timestamptz not null default now()
);

-- every snap (for history / stats later)
create table if not exists public.snaps (
  id bigint generated always as identity primary key,
  user_id uuid not null default auth.uid() references auth.users on delete cascade,
  kind text not null,
  play_key text not null,
  mine numeric not null,
  pro numeric not null,
  diff numeric not null,
  created_at timestamptz not null default now()
);

-- Today's 6 leaderboard: first finished run per player per day
create table if not exists public.daily_scores (
  user_id uuid not null default auth.uid() references auth.users on delete cascade,
  day date not null,
  name text not null,
  score numeric not null,
  wins int not null,
  created_at timestamptz not null default now(),
  primary key (user_id, day)
);

alter table public.profiles enable row level security;
alter table public.rounds enable row level security;
alter table public.snaps enable row level security;
alter table public.daily_scores enable row level security;

-- players read and write only their own rows
drop policy if exists "own profile" on public.profiles;
create policy "own profile" on public.profiles for all to authenticated using (auth.uid() = id) with check (auth.uid() = id);
drop policy if exists "own rounds" on public.rounds;
create policy "own rounds" on public.rounds for all to authenticated using (auth.uid() = user_id) with check (auth.uid() = user_id);
drop policy if exists "own snaps" on public.snaps;
create policy "own snaps" on public.snaps for all to authenticated using (auth.uid() = user_id) with check (auth.uid() = user_id);

-- the daily board is public to read (guests see it too); you can only post your own score
drop policy if exists "board is public" on public.daily_scores;
create policy "board is public" on public.daily_scores for select to anon, authenticated using (true);
drop policy if exists "post own score" on public.daily_scores;
create policy "post own score" on public.daily_scores for insert to authenticated with check (auth.uid() = user_id);

create index if not exists daily_scores_day on public.daily_scores (day, score desc);
create index if not exists rounds_user on public.rounds (user_id, created_at desc);

-- sanity limits on posted scores (scores are client-reported; this stops absurd values, not careful cheating)
alter table public.daily_scores drop constraint if exists daily_scores_sane;
alter table public.daily_scores add constraint daily_scores_sane check (score between -30 and 30 and wins between 0 and 6 and char_length(name) between 1 and 40 and day between current_date - 1 and current_date + 1);

-- per-snap results of a round (so past rounds can be reopened as a results page)
alter table public.rounds add column if not exists res jsonb;
