-- 2026-10-28 · FreshRoot lookup: an index for name search on providers
-- Adds, never drops. No receipt, source or rights column is changed.
--
-- GET /v1/lookup searches individual providers by last-name prefix and first-name prefix (NPPES stores names upper
-- case). The database collation is en_US.UTF-8, so the existing idx_providers_last_name cannot serve LIKE 'ABC%':
-- before this index, 'HERNAND%' + 'CARL%' was a parallel seq scan of 9.4M rows (13.6 s), and an exact last name
-- with a first-name prefix was a bitmap heap scan (6.0 s for GARCIA + MAR%).
-- varchar_pattern_ops on both columns lets the last-name prefix be the range and the first-name prefix be checked on
-- the index entries, so only matching rows reach the heap.
--
-- CONCURRENTLY: providers is not locked against the weekly NPPES load while this builds. It cannot run inside a
-- transaction, so this file has no BEGIN/COMMIT.

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_providers_individual_name_prefix
  ON providers (last_name varchar_pattern_ops, first_name varchar_pattern_ops)
  WHERE entity_type = 'individual';

-- After running:
--   EXPLAIN ANALYZE SELECT npi FROM providers
--   WHERE entity_type = 'individual' AND last_name LIKE 'HERNAND%' AND first_name LIKE 'CARL%'
--   ORDER BY last_name, first_name LIMIT 21;   -- Index Scan using idx_providers_individual_name_prefix
