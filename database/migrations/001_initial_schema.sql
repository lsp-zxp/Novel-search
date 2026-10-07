begin;

create table if not exists public.authors (
    id text primary key,
    pen_name text not null,
    real_name text not null,
    email text not null unique,
    identity_verified boolean not null default false,
    created_at timestamptz not null
);

create table if not exists public.novels (
    id text primary key,
    title text not null,
    author_id text not null references public.authors(id) on delete restrict,
    author_pen_name text not null,
    platform text not null,
    genre text not null,
    synopsis text not null,
    word_count integer not null check (word_count >= 0),
    current_status text not null,
    submitted_at timestamptz not null,
    contract_id text,
    is_original boolean not null default true,
    content_rating text not null default 'general'
);

create table if not exists public.workflow_events (
    id text primary key,
    novel_id text not null references public.novels(id) on delete cascade,
    state text not null,
    occurred_at timestamptz not null,
    operator text not null
);

create table if not exists public.contracts (
    id text primary key,
    novel_id text not null references public.novels(id) on delete cascade,
    version integer not null check (version > 0),
    status text not null,
    license_type text not null,
    author_share numeric(5,4) not null check (author_share between 0 and 1),
    settlement_cycle text not null,
    effective_from date not null,
    effective_to date,
    source_clause text not null,
    check (effective_to is null or effective_to >= effective_from)
);

create table if not exists public.settlements (
    id text primary key,
    novel_id text not null references public.novels(id) on delete cascade,
    period text not null check (period ~ '^[0-9]{4}-[0-9]{2}$'),
    distributable_revenue numeric(14,2) not null check (distributable_revenue >= 0),
    configured_author_share numeric(5,4) not null check (configured_author_share between 0 and 1),
    author_amount numeric(14,2) not null check (author_amount >= 0),
    status text not null,
    created_at timestamptz not null
);

create table if not exists public.expected_anomalies (
    id text primary key,
    novel_id text not null references public.novels(id) on delete cascade,
    anomaly_type text not null,
    risk_level text not null check (risk_level in ('low', 'medium', 'high')),
    expected_result text not null,
    expected_affected_amount numeric(14,2) not null default 0
);

create index if not exists idx_novels_author on public.novels(author_id);
create index if not exists idx_novels_status on public.novels(current_status);
create index if not exists idx_novels_platform on public.novels(platform);
create index if not exists idx_workflow_novel_time on public.workflow_events(novel_id, occurred_at);
create index if not exists idx_contracts_novel_effective on public.contracts(novel_id, effective_from desc);
create index if not exists idx_settlements_novel_period on public.settlements(novel_id, period);
create index if not exists idx_anomalies_novel on public.expected_anomalies(novel_id);

alter table public.authors enable row level security;
alter table public.novels enable row level security;
alter table public.workflow_events enable row level security;
alter table public.contracts enable row level security;
alter table public.settlements enable row level security;
alter table public.expected_anomalies enable row level security;

revoke all on table public.authors from anon, authenticated;
revoke all on table public.novels from anon, authenticated;
revoke all on table public.workflow_events from anon, authenticated;
revoke all on table public.contracts from anon, authenticated;
revoke all on table public.settlements from anon, authenticated;
revoke all on table public.expected_anomalies from anon, authenticated;

grant all on table public.authors to service_role;
grant all on table public.novels to service_role;
grant all on table public.workflow_events to service_role;
grant all on table public.contracts to service_role;
grant all on table public.settlements to service_role;
grant all on table public.expected_anomalies to service_role;

commit;
