-- SARATHI Phase 1 schema: reminders + briefing history.
-- Accessed only from the backend with the service-role key; RLS is enabled
-- with no anon policies so the anon key cannot read anything.

create extension if not exists pgcrypto;

create table if not exists public.reminders (
  id uuid primary key default gen_random_uuid(),
  title text not null,
  notes text,
  due_at timestamptz,
  location text,
  status text not null default 'pending' check (status in ('pending', 'done', 'cancelled')),
  source_transcript text,
  calendar_event_id text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.briefings (
  id uuid primary key default gen_random_uuid(),
  query text not null,
  type text not null check (type in ('REMINDER', 'MEDIA_WATCH', 'SPEECH_PREP', 'GENERAL')),
  spoken text not null,
  detail text,
  sources jsonb not null default '[]'::jsonb,
  reminder_id uuid references public.reminders (id) on delete set null,
  created_at timestamptz not null default now()
);

create index if not exists reminders_due_at_idx on public.reminders (due_at);
create index if not exists reminders_status_idx on public.reminders (status);
create index if not exists briefings_created_at_idx on public.briefings (created_at desc);

alter table public.reminders enable row level security;
alter table public.briefings enable row level security;
