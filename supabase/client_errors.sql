-- Errors players hit in the browser (message, where, device), so bugs can be found from real sessions. Insert-only for players.
create table if not exists public.client_errors (
  id bigint generated always as identity primary key,
  at timestamptz not null default now(),
  msg text not null check (char_length(msg) <= 500),
  stack text check (char_length(stack) <= 2000),
  ctx text check (char_length(ctx) <= 300),
  ua text check (char_length(ua) <= 300)
);
alter table public.client_errors enable row level security;
drop policy if exists "anyone can report" on public.client_errors;
create policy "anyone can report" on public.client_errors for insert to anon, authenticated with check (true);
grant insert on public.client_errors to anon, authenticated;
