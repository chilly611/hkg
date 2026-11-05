-- 2026-11-05 · poll late before the first stamp.
--
-- 2026-10-28_poll_late.sql ages data_sources.last_polled_at into "poll late". A source the poller has never
-- stamped has a null stamp, and a null never ages, so a poller that has not run since the stamp shipped
-- (2026-10-28: no scheduled run for hours after the merge) left every source reading fresh. Now a source
-- the poller checks falls back to its last completed load when it has no stamp: no check and no load in
-- 90 minutes reads "poll late".
--
-- "A source the poller checks" needs one fact the database did not have: Florida MQA has a detection_url,
-- but a signed-in person loads it, so the poller never stamps it, and the fallback alone would read it
-- "poll late" forever. data_sources.person_run marks such sources. scripts/poll_sources.py reads the same
-- flag to decide what it skips, so the poller and the view cannot disagree. Sources with no detection_url
-- are never checked either and stay out of the test.
--
-- Precedence unchanged: never > poll late > unscheduled > fresh > due > stale. Columns unchanged, so the
-- view keeps its order and grants. Idempotent.

begin;

alter table public.data_sources add column if not exists person_run boolean not null default false;
comment on column public.data_sources.person_run is
  'A person loads this source: scripts/poll_sources.py never checks it, and v_source_status never reads it "poll late".';
update public.data_sources set person_run = true
 where name = 'Florida MQA licensee data download' and not person_run;

comment on column public.data_sources.last_polled_at is
  'When scripts/poll_sources.py last checked this source for a new release. Null: not checked yet, or the poller does not check it (person_run, or no detection_url).';

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
         when s.detection_url is not null and not s.person_run
              and coalesce(s.last_polled_at, lr.completed_at) < now() - interval '90 minutes' then 'poll late'::text
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
