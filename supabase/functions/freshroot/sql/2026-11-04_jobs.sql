-- 2026-11-04 · FreshRoot bulk jobs, and rosters.test
-- Idempotent. Adds, never drops. No receipt, source or rights column is changed.
-- Kept beside the function because this change was scoped to supabase/functions/freshroot/, freshroot/ and scripts/;
-- it belongs in migrations/ with the others and can move there as-is. Applied live 2026-11-04.
--
-- What this adds:
--   1. rosters.test: a roster built to test the system. The hourly roster refresh (scripts/refresh_roster_receipts.py)
--      skips it, and its export says so at the top of report.md. Its receipts stay: receipts are append-only.
--   2. freshroot_jobs: one row per POST /v1/rosters/{id}/jobs. The freshroot edge function is the worker: it works a
--      job in batches in a background task and records progress here after every batch.
--   3. freshroot_job_claim(job, lease): the lease that keeps two workers off one job. A worker that dies leaves the
--      lease to lapse; the next GET /v1/jobs/{id} claims the job again and carries on from `processed`.
--
-- Closed to anon and authenticated, like the rest of the FreshRoot tables. Only service_role (the edge function) uses it.

BEGIN;

-- 1. Test rosters.
ALTER TABLE rosters ADD COLUMN IF NOT EXISTS test BOOLEAN NOT NULL DEFAULT FALSE;
COMMENT ON COLUMN rosters.test IS
  'A roster built to test the system: skipped by the hourly roster refresh; its export is headed as a test. Its receipts are kept (append-only).';

-- 2. Jobs.
CREATE TABLE IF NOT EXISTS freshroot_jobs (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  roster_id         TEXT NOT NULL REFERENCES rosters(id) ON DELETE CASCADE,
  tenant_id         UUID REFERENCES api_tenants(id) ON DELETE SET NULL,   -- who asked; access is by roster
  kind              TEXT NOT NULL DEFAULT 'add_npis' CHECK (kind IN ('add_npis')),
  status            TEXT NOT NULL DEFAULT 'queued' CHECK (status IN ('queued', 'running', 'done', 'failed')),
  input_count       INTEGER NOT NULL,                     -- lines or list items received
  npis              TEXT[] NOT NULL,                      -- the valid NPIs, de-duplicated, in input order
  states            JSONB NOT NULL DEFAULT '{}'::jsonb,   -- {npi: state} where the input named the license state
  processed         INTEGER NOT NULL DEFAULT 0,           -- npis[1:processed] are done
  added             INTEGER NOT NULL DEFAULT 0,           -- put on the roster by this job
  already_on_roster INTEGER NOT NULL DEFAULT 0,
  receipted         INTEGER NOT NULL DEFAULT 0,           -- NPIs that got at least one receipt during this job
  receipts_written  INTEGER NOT NULL DEFAULT 0,
  unmatched         JSONB NOT NULL DEFAULT '[]'::jsonb,   -- [{npi, reason}]: refused at intake or by the worker
  guard             JSONB,                                -- the anomaly guard's last reading: shares and limits
  write_failures    TEXT[] NOT NULL DEFAULT '{}',
  error             TEXT,
  attempts          INTEGER NOT NULL DEFAULT 0,           -- times a worker claimed it
  lease_until       TIMESTAMPTZ,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  started_at        TIMESTAMPTZ,
  finished_at       TIMESTAMPTZ,
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CHECK (processed >= 0 AND processed <= cardinality(npis)),
  CHECK (cardinality(npis) <= 5000)
);
ALTER TABLE freshroot_jobs ADD COLUMN IF NOT EXISTS states JSONB NOT NULL DEFAULT '{}'::jsonb;  -- added after the first apply
CREATE INDEX IF NOT EXISTS idx_freshroot_jobs_roster ON freshroot_jobs(roster_id, created_at DESC);

ALTER TABLE freshroot_jobs ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON freshroot_jobs FROM anon, authenticated;
GRANT SELECT, INSERT, UPDATE ON freshroot_jobs TO service_role;

-- 3. The lease. Claims a queued job, or a running one whose lease has lapsed; returns nothing when another worker
--    holds it or the job is finished. One UPDATE, so two callers never both get the row.
CREATE OR REPLACE FUNCTION freshroot_job_claim(p_job_id UUID, p_lease_seconds INTEGER)
RETURNS SETOF freshroot_jobs AS $$
  UPDATE freshroot_jobs
     SET status = 'running',
         lease_until = NOW() + make_interval(secs => p_lease_seconds),
         started_at = COALESCE(started_at, NOW()),
         attempts = attempts + 1,
         updated_at = NOW()
   WHERE id = p_job_id
     AND status IN ('queued', 'running')
     AND (lease_until IS NULL OR lease_until < NOW())
  RETURNING *;
$$ LANGUAGE sql VOLATILE;

REVOKE ALL ON FUNCTION freshroot_job_claim(UUID, INTEGER) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION freshroot_job_claim(UUID, INTEGER) TO service_role;

COMMIT;
