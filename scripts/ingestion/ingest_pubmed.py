#!/usr/bin/env python3
"""
PubMed/MEDLINE Citation Ingestor for Healthcare Knowledge Garden
Ingests high-impact citations from NCBI E-Utilities API into Supabase
"""

import json
import urllib.request
import urllib.error
import urllib.parse
import time
import sys
from xml.etree import ElementTree as ET
from datetime import datetime
import uuid

# Supabase config
SUPABASE_URL = "https://opbrzaegvfyjpyyrmdfe.supabase.co"
SERVICE_ROLE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9wYnJ6YWVndmZ5anB5eXJtZGZlIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NTcxODE4NSwiZXhwIjoyMDkxMjk0MTg1fQ.43H90jIDQADS0qKKrAk3dkQEy6hba7pMj3VssdeAWS4"
TABLE_NAME = "pubmed_citations"

# NCBI E-Utilities API base
ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

# Rate limiting: 0.4s between NCBI calls (max 3 req/sec without API key)
NCBI_DELAY_SEC = 0.4

# Search topics for high-impact healthcare content
# Format: (query, additional_filter, max_pmids_to_fetch)
SEARCH_TOPICS = [
    ('clinical guidelines', '2021:2026[PDAT]', 6000),
    ('drug safety adverse effect', '2023:2026[PDAT]', 6000),
    ('medical credentialing', '', 5000),
    ('healthcare quality', '2021:2026[PDAT]', 6000),
    ('systematic review', '2023:2026[PDAT]', 6000),
    ('telemedicine', '2023:2026[PDAT]', 5000),
    ('patient safety', '2021:2026[PDAT]', 6000),
    ('evidence based medicine', '2021:2026[PDAT]', 5000),
    ('clinical decision support', '2021:2026[PDAT]', 5000),
    ('physician competence', '', 4000),
    ('randomized controlled trial', '2022:2026[PDAT]', 6000),
    ('meta-analysis', '2021:2026[PDAT]', 6000),
    ('clinical practice', '2021:2026[PDAT]', 5000),
    ('medical education', '2021:2026[PDAT]', 5000),
    ('health disparities', '2021:2026[PDAT]', 5000),
    ('precision medicine', '2021:2026[PDAT]', 4000),
    ('biomarker discovery', '2021:2026[PDAT]', 4000),
    ('artificial intelligence healthcare', '2021:2026[PDAT]', 5000),
    ('digital health', '2021:2026[PDAT]', 5000),
    ('infectious disease', '2021:2026[PDAT]', 6000),
]


def log(msg):
    """Log to stderr with timestamp"""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}", file=sys.stderr)


def ncbi_request(url, params, use_post=False):
    """Make a request to NCBI API with rate limiting"""
    time.sleep(NCBI_DELAY_SEC)

    try:
        if use_post:
            # Use POST for long URLs (efetch with many IDs)
            param_str = "&".join(f"{k}={urllib.parse.quote(str(v))}" for k, v in params.items())
            data = param_str.encode('utf-8')
            req = urllib.request.Request(url, data=data, headers={
                'User-Agent': 'HKG-PubMed-Ingestor/1.0'
            })
        else:
            # Use GET for shorter URLs (esearch)
            param_str = "&".join(f"{k}={urllib.parse.quote(str(v))}" for k, v in params.items())
            full_url = f"{url}?{param_str}"
            req = urllib.request.Request(full_url, headers={
                'User-Agent': 'HKG-PubMed-Ingestor/1.0'
            })

        # Use longer timeout for large XML responses
        with urllib.request.urlopen(req, timeout=120) as resp:
            return resp.read()
    except urllib.error.URLError as e:
        log(f"ERROR: NCBI request failed: {e}")
        return None
    except Exception as e:
        log(f"ERROR: Unexpected error in NCBI request: {type(e).__name__}: {str(e)[:100]}")
        return None


def search_pubmed(query, max_results=10000):
    """Search PubMed and return list of PMIDs"""
    log(f"Searching PubMed: {query}")

    params = {
        'db': 'pubmed',
        'retmode': 'json',
        'retmax': min(10000, max_results),
        'term': query,
    }

    resp = ncbi_request(ESEARCH_URL, params)
    if not resp:
        return []

    try:
        data = json.loads(resp)
        pmids = data.get('esearchresult', {}).get('idlist', [])
        count = int(data.get('esearchresult', {}).get('count', 0))
        log(f"Found {count} results, fetching {len(pmids)} PMIDs")
        return pmids[:max_results]
    except Exception as e:
        log(f"ERROR parsing search results: {e}")
        return []


def fetch_pubmed_details(pmids):
    """Fetch full article details from PubMed for a batch of PMIDs"""
    if not pmids:
        return []

    pmid_list = ",".join(pmids)
    log(f"Fetching details for {len(pmids)} articles...")

    params = {
        'db': 'pubmed',
        'retmode': 'xml',
        'id': pmid_list,
    }

    resp = ncbi_request(EFETCH_URL, params, use_post=True)
    if not resp:
        return []

    articles = []
    try:
        root = ET.fromstring(resp)

        for article_elem in root.findall('.//PubmedArticle'):
            article = parse_article(article_elem)
            if article:
                articles.append(article)
    except Exception as e:
        log(f"ERROR parsing XML: {e}")

    return articles


def parse_article(article_elem):
    """Parse a single article element from PubMed XML"""
    try:
        # PMID
        pmid_elem = article_elem.find('.//PMID')
        pmid = pmid_elem.text if pmid_elem is not None else None
        if not pmid:
            return None

        # Title - REQUIRED field
        title_elem = article_elem.find('.//ArticleTitle')
        title = title_elem.text if title_elem is not None else None
        if title:
            title = title.strip()
        # Skip articles with no title
        if not title:
            return None

        # Abstract
        abstract_elem = article_elem.find('.//Abstract/AbstractText')
        abstract = abstract_elem.text if abstract_elem is not None else None

        # Authors
        authors = []
        for author_elem in article_elem.findall('.//Author'):
            author = {}
            ln = author_elem.find('LastName')
            fn = author_elem.find('ForeName')
            if ln is not None:
                author['name'] = f"{ln.text}"
                if fn is not None:
                    author['name'] = f"{fn.text} {ln.text}"
            aff = author_elem.find('Affiliation')
            if aff is not None:
                author['affiliation'] = aff.text
            if author.get('name'):
                authors.append(author)

        # Journal
        journal_elem = article_elem.find('.//Journal/Title')
        journal = journal_elem.text if journal_elem is not None else None

        # Publication date
        pub_date = None
        pdate_elem = article_elem.find('.//PubDate')
        if pdate_elem is not None:
            year = pdate_elem.find('Year')
            month = pdate_elem.find('Month')
            day = pdate_elem.find('Day')
            try:
                y = int(year.text) if year is not None else 2026
                m = int(month.text) if month is not None else 1
                d = int(day.text) if day is not None else 1
                # Clamp to valid date
                if m > 12:
                    m = 12
                if d > 28:
                    d = 28
                pub_date = f"{y:04d}-{m:02d}-{d:02d}"
            except:
                pub_date = None

        # MeSH terms
        mesh_terms = []
        for mesh_elem in article_elem.findall('.//MeshHeading/DescriptorName'):
            if mesh_elem.text:
                mesh_terms.append(mesh_elem.text)

        # DOI
        doi = None
        for aid_elem in article_elem.findall('.//ArticleId'):
            if aid_elem.get('IdType') == 'doi':
                doi = aid_elem.text
                break

        # PMC ID
        pmc_id = None
        for aid_elem in article_elem.findall('.//ArticleId'):
            if aid_elem.get('IdType') == 'pmc':
                pmc_id = aid_elem.text
                break

        return {
            'id': str(uuid.uuid4()),
            'pmid': pmid,
            'title': title,
            'abstract': abstract,
            'authors': authors,
            'journal': journal,
            'publication_date': pub_date,
            'mesh_terms': mesh_terms,
            'doi': doi,
            'pmc_id': pmc_id,
            'citation_count': 0,
            'data_source': 'PubMed/MEDLINE',
            'source_url': f'https://pubmed.ncbi.nlm.nih.gov/{pmid}/',
        }
    except Exception as e:
        log(f"ERROR parsing article: {e}")
        return None


def insert_to_supabase(records):
    """Insert records to Supabase via PostgREST UPSERT"""
    if not records:
        return 0

    url = f"{SUPABASE_URL}/rest/v1/{TABLE_NAME}"

    headers = {
        'apikey': SERVICE_ROLE_KEY,
        'Authorization': f'Bearer {SERVICE_ROLE_KEY}',
        'Content-Type': 'application/json',
        'Prefer': 'resolution=merge-duplicates',
    }

    # Filter out records with null titles or pmids
    valid_records = [
        r for r in records
        if r.get('title') and r.get('title').strip() and r.get('pmid')
    ]

    if not valid_records:
        return 0

    payload = json.dumps(valid_records).encode('utf-8')

    try:
        req = urllib.request.Request(url, data=payload, headers=headers, method='POST')
        with urllib.request.urlopen(req, timeout=60) as resp:
            resp.read()
            inserted_count = len(valid_records)
            skipped_count = len(records) - inserted_count
            if skipped_count > 0:
                log(f"Inserted {inserted_count} records (skipped {skipped_count} invalid)")
            else:
                log(f"Inserted {inserted_count} records to Supabase")
            return inserted_count
    except urllib.error.HTTPError as e:
        # Handle conflict errors gracefully
        if e.code == 409:
            log(f"NOTE: Some records already exist (conflict 409) - skipping duplicates")
            return 0
        error_body = e.read().decode('utf-8', errors='ignore')
        log(f"ERROR inserting to Supabase: {e.code} - {error_body[:200]}")
        return 0
    except Exception as e:
        log(f"ERROR: {type(e).__name__}: {str(e)[:100]}")
        return 0


def main():
    log("Starting PubMed citation ingestion (v3 - expanded search)...")
    log(f"Target: 20,000+ citations across {len(SEARCH_TOPICS)} topics")
    log("Using diverse search queries to maximize coverage")

    total_inserted = 0
    all_pmids_fetched = set()

    for topic, date_filter, max_per_topic in SEARCH_TOPICS:
        log(f"\n=== Processing topic: {topic} ===")

        # Build search query
        query = topic
        if date_filter:
            query += f" AND {date_filter}"

        # Search
        pmids = search_pubmed(query, max_per_topic)
        if not pmids:
            log(f"No results for {topic}")
            continue

        # Filter out already fetched
        new_pmids = [p for p in pmids if p not in all_pmids_fetched]
        log(f"Processing {len(new_pmids)} new PMIDs (already have {len(all_pmids_fetched)})")

        # Batch fetch in groups of 150 (to avoid URI length limits and timeouts)
        batch_size = 150
        for i in range(0, len(new_pmids), batch_size):
            batch = new_pmids[i:i+batch_size]
            articles = fetch_pubmed_details(batch)

            # Insert in groups of 150
            insert_batch_size = 150
            for j in range(0, len(articles), insert_batch_size):
                insert_batch = articles[j:j+insert_batch_size]
                inserted = insert_to_supabase(insert_batch)
                total_inserted += inserted
                all_pmids_fetched.update([a['pmid'] for a in insert_batch])

        log(f"Topic '{topic}' complete. Total inserted so far: {total_inserted}")

    log(f"\n=== INGESTION COMPLETE ===")
    log(f"Total citations inserted: {total_inserted}")
    log(f"Target was 20,000+")

    if total_inserted >= 20000:
        log("SUCCESS: Target reached!")
    else:
        log(f"WARNING: Only {total_inserted} citations ingested, target was 20,000+")


if __name__ == '__main__':
    main()
