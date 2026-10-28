-- 2026-10-28 · poll late: a slow poller is never mistaken for a dark board.
--
-- The poller (scripts/poll_sources.py) runs from GitHub Actions at :17 and :47. GitHub runs schedules
-- best-effort and delays or drops runs, and the poller writes a run only when it finds a release, so a
-- source the poller has not looked at in hours read "due" or "stale", the same as a publisher that
-- missed its release. data_sources.last_polled_at is stamped by the poller each time it checks a source
-- (reachable or not; a dry run stamps nothing). v_source_status reads "poll late" when that stamp is more
-- than 90 minutes old: three missed :17/:47 slots, so one late or dropped run alone never trips it.
-- Sources the poller never checks (a person loads them, or no detection_url) keep last_polled_at null and
-- are unaffected.
--
-- Precedence: never > poll late > unscheduled > fresh > due > stale. A source with no completed run still
-- reads never; otherwise, while the poll is late, due and stale cannot be told from "not looked at yet".
-- last_polled_at is added as the view's last column, so existing columns keep their order and grants.
-- Idempotent.

begin;

alter table public.data_sources add column if not exists last_polled_at timestamptz;
comment on column public.data_sources.last_polled_at is
  'When scripts/poll_sources.py last checked this source for a new release. Null: the poller does not check it.';

create or replace view public.v_source_status as
with last_run as (
  select distinct on (ingestion_runs.source_id) ingestion_runs.source_id,
         ingestion_runs.completed_at,
         ingestion_runs.started_at,
         ingestion_runs.status,
         ingestion_runs.records_processed,
         ingestion_runs.source_published_at,
         ingestion_runs.detected_at
    from ingestion_runs
   where ingestion_runs.status::text = 'completed'::text
   order by ingestion_runs.source_id, ingestion_runs.completed_at desc nulls last
)
select s.name,
       s.category,
       s.jurisdiction,
       s.claim_types,
       s.cadence_hours,
       s.redistribution_permission,
       s.accepted_for_sale,
       lr.source_published_at as file_date,
       lr.detected_at,
       lr.completed_at as last_run_at,
       lr.records_processed,
       case
         when lr.completed_at is null or s.cadence_hours is null then null::timestamptz
         else lr.completed_at + make_interval(hours => s.cadence_hours)
       end as next_due_at,
       case
         when lr.completed_at is null then null::numeric
         else extract(epoch from now() - lr.completed_at) / 3600.0
       end as age_hours,
       case
         when lr.completed_at is null then 'never'::text
         when s.last_polled_at < now() - interval '90 minutes' then 'poll late'::text
         when s.cadence_hours is null then 'unscheduled'::text
         when now() <= lr.completed_at + make_interval(hours => s.cadence_hours) then 'fresh'::text
         when now() <= lr.completed_at + make_interval(hours => s.cadence_hours * 2) then 'due'::text
         else 'stale'::text
       end as freshness,
       s.last_polled_at
  from data_sources s
  left join last_run lr on lr.source_id = s.id
 where s.category::text = any (array['provider_data'::varchar, 'compliance'::varchar, 'licensing'::varchar]::text[])
 order by s.category, s.name;

commit;
