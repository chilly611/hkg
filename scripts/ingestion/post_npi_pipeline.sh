#!/bin/bash
# Post-NPI-Load Pipeline
# Monitors the NPI bulk load, then triggers:
#   1. Addresses + Taxonomies extraction
#   2. OIG-NPI reconciliation
#   3. Final dashboard stats

LOG="/tmp/npi_full_ingestion.log"
ADDR_TAX_LOG="/tmp/npi_addr_tax.log"
WORKDIR="/sessions/laughing-modest-gates"

SUPABASE_URL="https://opbrzaegvfyjpyyrmdfe.supabase.co"
SUPABASE_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9wYnJ6YWVndmZ5anB5eXJtZGZlIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NTcxODE4NSwiZXhwIjoyMDkxMjk0MTg1fQ.43H90jIDQADS0qKKrAk3dkQEy6hba7pMj3VssdeAWS4"

echo "=========================================="
echo "[Pipeline] Monitoring NPI bulk load..."
echo "=========================================="

# Wait for NPI ingestion process to finish
while pgrep -f "ingest_npi_stdin.py" > /dev/null 2>&1; do
    LAST=$(tail -1 "$LOG" 2>/dev/null)
    echo "[$(date +%H:%M:%S)] NPI still running: $LAST"
    sleep 30
done

echo ""
echo "=========================================="
echo "[Pipeline] NPI bulk load COMPLETE!"
echo "=========================================="
tail -10 "$LOG"

# Get final provider count
echo ""
echo "[Pipeline] Checking provider count..."
PROVIDER_COUNT=$(python3 -c "
import urllib.request, json
req = urllib.request.Request(
    '${SUPABASE_URL}/rest/v1/providers?select=id&limit=1',
    headers={'apikey': '${SUPABASE_KEY}', 'Authorization': 'Bearer ${SUPABASE_KEY}', 'Prefer': 'count=exact'}
)
resp = urllib.request.urlopen(req, timeout=15)
cr = resp.headers.get('Content-Range', '?')
print(cr.split('/')[-1])
")
echo "[Pipeline] Providers in DB: $PROVIDER_COUNT"

# Step 1: OIG-NPI Reconciliation
echo ""
echo "=========================================="
echo "[Pipeline] Step 1: OIG-NPI Reconciliation"
echo "=========================================="
python3 -c "
import json, urllib.request
url = '${SUPABASE_URL}/rest/v1/rpc/reconcile_oig_exclusions'
headers = {
    'apikey': '${SUPABASE_KEY}',
    'Authorization': 'Bearer ${SUPABASE_KEY}',
    'Content-Type': 'application/json'
}
req = urllib.request.Request(url, data=b'{}', headers=headers, method='POST')
try:
    resp = urllib.request.urlopen(req, timeout=120)
    result = json.loads(resp.read().decode())
    print(f'OIG Reconciliation result: {json.dumps(result, indent=2)}')
except Exception as e:
    print(f'OIG Reconciliation error: {e}')
    # Try via direct SQL RPC
    print('(Function may not exist or may need different invocation)')
"

# Step 2: Addresses + Taxonomies
echo ""
echo "=========================================="
echo "[Pipeline] Step 2: Addresses + Taxonomies"
echo "=========================================="
echo "[Pipeline] Starting addr+tax extraction from full NPI CSV..."
unzip -p /tmp/npi_full.zip "npidata_pfile_*.csv" 2>/dev/null | python3 "$WORKDIR/ingest_npi_addr_tax.py" 2>&1 | tee "$ADDR_TAX_LOG"

# Step 3: Final Stats
echo ""
echo "=========================================="
echo "[Pipeline] Step 3: Final Database Stats"
echo "=========================================="
python3 -c "
import urllib.request, json
KEY = '${SUPABASE_KEY}'
URL = '${SUPABASE_URL}'
tables = ['providers', 'provider_addresses', 'provider_taxonomies', 'icd10_cm_codes', 'icd10_pcs_codes', 'oig_exclusions', 'ndc_codes', 'hcpcs_codes', 'drg_codes', 'data_sources']
total = 0
for t in tables:
    try:
        req = urllib.request.Request(
            f'{URL}/rest/v1/{t}?select=id&limit=1',
            headers={'apikey': KEY, 'Authorization': f'Bearer {KEY}', 'Prefer': 'count=exact'}
        )
        resp = urllib.request.urlopen(req, timeout=15)
        cr = resp.headers.get('Content-Range', '?')
        count = int(cr.split('/')[-1])
        total += count
        print(f'  {t:30s} {count:>12,d}')
    except Exception as e:
        print(f'  {t:30s} ERROR: {e}')
print(f'  {\"TOTAL\":30s} {total:>12,d}')
"

echo ""
echo "=========================================="
echo "[Pipeline] ALL DONE!"
echo "=========================================="
