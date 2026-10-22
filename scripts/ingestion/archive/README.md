These scripts predate .env and carry a hardcoded Supabase service_role key; they are kept for history and must not be run.
apply_oig_matches.py writes name-matched NPIs into oig_exclusions.npi, which receipts_for_exclusions reads as an exact NPI match, so running it would issue verified exclusion receipts for the wrong people.
