-- 2026-10-28 · Two receipt statuses for the CMS sources: opted_out and enrolled
-- Widens a CHECK list, never narrows it. No receipt is deleted or edited; existing values stay valid.
--
-- What this adds:
--   1. normalized_status accepts opted_out (claim_type medicare_optout: the NPI is on CMS's opt-out affidavit list)
--      and enrolled (claim_type pecos_enrollment: the NPI holds an approved enrollment in the public PECOS extract).
--      Their absence is not_found, as for every other source: not on that file on that date, never clear.
--   2. Column comments that state the receipt vocabulary, so the spec lives on the table it governs.

BEGIN;

ALTER TABLE credential_receipts DROP CONSTRAINT IF EXISTS credential_receipts_normalized_status_check;
ALTER TABLE credential_receipts ADD CONSTRAINT credential_receipts_normalized_status_check
  CHECK (normalized_status IN (
    'active','inactive','expired','suspended','revoked','probation',
    'excluded','reinstated','opted_out','enrolled','not_found','unavailable','unknown'));

COMMENT ON COLUMN credential_receipts.raw_status IS
  'Exactly what the source says, unaltered. For an absence, a note naming the snapshot the NPI was not in (e.g. "not in LEIE snapshot").';

COMMENT ON COLUMN credential_receipts.normalized_status IS
  'The receipt vocabulary. Licenses and NPI: active, inactive, expired, suspended, revoked, probation. '
  'Exclusions (OIG, SAM): excluded, reinstated. Medicare opt-out: opted_out. PECOS enrollment: enrolled. '
  'not_found: absent from that source''s snapshot on that date, never clear. unavailable: the source could not be read. '
  'unknown: the source''s status did not map.';

COMMIT;
