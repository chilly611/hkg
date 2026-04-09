# HKG RSI Heartbeat System Design Document

**Author**: Chilly (Charles Dahlgren), XRWorkers  
**Date**: 2026-04-09  
**Status**: Design Specification  
**Version**: 1.0

---

## TABLE OF CONTENTS

1. [HEARTBEAT PHILOSOPHY](#heartbeat-philosophy)
2. [HEARTBEAT SCHEDULE (DETAILED)](#heartbeat-schedule-detailed)
3. [HEARTBEAT ARCHITECTURE](#heartbeat-architecture)
4. [DATA FRESHNESS SCORING MODEL](#data-freshness-scoring-model)
5. [3-POINT CROSS-VALIDATION ENGINE](#3-point-cross-validation-engine)
6. [KNOWLEDGE GRAPH ENRICHMENT](#knowledge-graph-enrichment)
7. [MONITORING & ALERTING](#monitoring--alerting)
8. [IMPLEMENTATION PLAN](#implementation-plan)
9. [THE COMPOUND EFFECT](#the-compound-effect)
10. [TECHNICAL APPENDIX](#technical-appendix)

---

## HEARTBEAT PHILOSOPHY

The Healthcare Knowledge Garden is not a static database. It is a **living organism** that gains intelligence every single day it operates. The RSI (Recursive Self-Improvement) Heartbeat is the platform's metabolism — the continuous cycle of ingestion, validation, and discovery that compounds over time.

### Core Principles

**1. Autonomy Over Manual Curation**
- The system must update itself without human intervention
- Curation happens through automated validation, not editorial gatekeeping
- Every heartbeat improves the platform's knowledge automatically

**2. Freshness as Competitive Advantage**
- Data staleness is a loss of trust
- Healthcare data moves fast: licenses expire, drugs are recalled, trials complete, research publishes daily
- HKG must outpace competitors in detecting and ingesting these changes
- Freshness scoring makes staleness visible and actionable

**3. Cross-Validation as Truth**
- No single source is authoritative (even NPI has gaps and errors)
- Truth emerges from triangulation across 3+ independent sources
- Conflicts surface as high-value alerts, not data loss
- Verified data has exponentially higher trust value

**4. The Knowledge Graph as Network Effect**
- Data becomes powerful when relationships are discovered
- Automated relationship discovery scales faster than manual enrichment
- A dense, verified knowledge graph is insurmountable to replicate
- Graph density compounds: more nodes → more discovered relationships → more edges → more queries answered

**5. Every Page as an AI Citation Source**
- In the age of AI agents, every entity page must be:
  - Machine-readable (JSON-LD, llms.txt)
  - Verifiable (source citations, freshness metadata)
  - Linkable (canonical URLs, backlinks)
- The heartbeat regenerates pages with updated data and metadata
- AI systems naturally cite high-quality, canonical sources

### Not Just A Cron Job

This is not a background daemon that runs queries. This is the platform's **operating system**. Think of it as:

- **The Heart**: Pumps fresh data through the system
- **The Lungs**: Breathes in new knowledge from the outside world
- **The Brain**: Validates and synthesizes that knowledge
- **The Immune System**: Detects anomalies (conflicts, staleness, errors)
- **The Growth System**: Discovers new relationships and expands the graph

---

## HEARTBEAT SCHEDULE (DETAILED)

### DAILY HEARTBEATS (2:00 AM UTC)

**Trigger**: Cron: `0 2 * * *`  
**SLA**: Complete within 4 hours (before 6:00 AM UTC)

#### 2.1 NPI Registry Incremental Check
- **Source**: NPI Registry (NPPES) API + monthly dissemination file
- **Frequency**: Daily
- **Logic**:
  - Query NPI API for providers updated in last 24 hours
  - Parse monthly dissemination file deltas if available
  - Check: new registrations, updated credentials, deactivations
  - Update `providers` table, mark `freshness_verified_at` = today
  - Log: # new providers, # updates, # deactivations
- **Pseudocode**:
  ```
  async function refreshNPIDaily() {
    const yesterday = Date.now() - 86400000;
    const updated = await npiApi.getUpdatedProviders(yesterday);
    
    for (const provider of updated) {
      const normalized = normalizeNPIRecord(provider);
      const npi_id = provider.npi;
      
      const existingProvider = await supabase
        .from('providers')
        .select('*')
        .eq('npi_id', npi_id)
        .single();
      
      if (existingProvider) {
        // Update and mark freshness
        await supabase
          .from('providers')
          .update({
            ...normalized,
            freshness_verified_at: new Date(),
            freshness_score: calculateFreshnessScore('provider'),
            data_sources: [...existingProvider.data_sources, 'NPI_API'],
          })
          .eq('npi_id', npi_id);
      } else {
        // New provider
        await supabase
          .from('providers')
          .insert({
            npi_id,
            ...normalized,
            freshness_verified_at: new Date(),
            freshness_score: 100,
            data_sources: ['NPI_API'],
            verification_status: 'UNVERIFIED',
          });
      }
    }
    
    logger.info(`NPI Daily: ${updated.length} records processed`);
  }
  ```

#### 2.2 NDC Directory Update Check
- **Source**: openFDA API (Drug Updates endpoint)
- **Frequency**: Daily
- **Logic**:
  - Query openFDA for drugs updated in last 24 hours
  - Check: new approvals, labeling changes, recalls
  - Update `drugs` table with new/updated NDC records
  - Mark drugs with updates for re-validation
- **Pseudocode**:
  ```
  async function refreshNDCDaily() {
    const yesterday = Date.now() - 86400000;
    const updated = await openFDAApi.getDrugsUpdated(yesterday);
    
    for (const drug of updated) {
      const ndc = drug.openfda?.ndc_code?.[0];
      if (!ndc) continue;
      
      const normalized = normalizeNDCRecord(drug);
      await supabase
        .from('drugs')
        .upsert(
          {
            ndc_code: ndc,
            ...normalized,
            freshness_verified_at: new Date(),
            freshness_score: 100,
            data_sources: ['FDA_NDC'],
          },
          { onConflict: 'ndc_code' }
        );
    }
  }
  ```

#### 2.3 DailyMed New Label Check
- **Source**: DailyMed REST API
- **Frequency**: Daily
- **Logic**:
  - Fetch recently updated SPLs (Structured Product Labels)
  - Extract: drug name, indications, contraindications, adverse reactions
  - Update `drug_labels` table
  - Flag for cross-validation with drug interaction databases
- **Endpoint**: `https://dailymed.nlm.nih.gov/dailymed/services/v2/SPLs.json`

#### 2.4 PubMed New Citation Scan
- **Source**: PubMed E-utilities API
- **Frequency**: Daily
- **Logic**:
  - Query PubMed for papers published in last 24 hours matching tracked topics
  - Search terms: ICD-10 codes, drug names, conditions tracked by HKG
  - Extract: PMID, title, authors, abstract, publication date, MeSH terms
  - Create `pubmed_citations` records, link to relevant entities
  - Build graph edges: CITES_EVIDENCE for condition treatments
  - Store full citation metadata for AI consumption (llms.txt generation)
- **Pseudocode**:
  ```
  async function refreshPubMedDaily() {
    // Get list of tracked conditions (top N by user interest)
    const trackedConditions = await supabase
      .from('conditions')
      .select('icd10_code, name')
      .order('user_interest_score', { ascending: false })
      .limit(500);
    
    for (const condition of trackedConditions) {
      const searchTerm = `"${condition.name}" AND [DP] from 1 days ago`;
      const pmids = await pubmedApi.search(searchTerm);
      
      for (const pmid of pmids) {
        const existing = await supabase
          .from('pubmed_citations')
          .select('id')
          .eq('pmid', pmid)
          .single();
        
        if (!existing) {
          const citation = await pubmedApi.fetchDetails(pmid);
          const normalized = normalizePubMedRecord(citation);
          
          await supabase
            .from('pubmed_citations')
            .insert({
              pmid,
              ...normalized,
              ingested_at: new Date(),
            });
          
          // Create relationship edge if relevant
          await neo4j.run(
            `MATCH (c:Condition {icd10_code: $icd10})
             CREATE (c)-[:CITED_IN_EVIDENCE {pmid: $pmid, year: $year}]->
               (p:PubMedCitation {pmid: $pmid})`,
            { icd10: condition.icd10_code, pmid, year: citation.year }
          );
        }
      }
    }
  }
  ```

#### 2.5 ClinicalTrials.gov Status Changes
- **Source**: ClinicalTrials.gov API v2
- **Frequency**: Daily
- **Logic**:
  - Query for trials with status updates in last 24 hours
  - Check: new enrollments, completions, status changes (recruiting → closed)
  - Update `clinical_trials` table
  - Generate alerts if a trial relevant to tracked conditions completes
  - Flag for evidence synthesis (new trial results)
- **Endpoint**: `https://clinicaltrials.gov/api/v2/studies`

#### 2.6 Data Freshness Scoring (Global)
- **Frequency**: Daily (after all ingestions complete)
- **Logic**:
  - Scan all entities in Supabase
  - Calculate freshness_score for each based on entity type and last verification date
  - Update `entity_freshness` materialized view
  - Identify stale entities (score < 50)
  - Queue stale entities for next weekly cross-validation sweep
- **Pseudocode**:
  ```
  async function refreshFreshnessScores() {
    const entityTypes = [
      { type: 'providers', decayRate: 'fast' },
      { type: 'drugs', decayRate: 'medium' },
      { type: 'clinical_trials', decayRate: 'medium' },
      { type: 'pubmed_citations', decayRate: 'never' },
    ];
    
    for (const { type, decayRate } of entityTypes) {
      const entities = await supabase
        .from(type)
        .select('id, freshness_verified_at');
      
      for (const entity of entities) {
        const daysSinceVerification = daysSince(entity.freshness_verified_at);
        const freshness_score = calculateScore(daysSinceVerification, decayRate);
        
        await supabase
          .from(type)
          .update({ freshness_score })
          .eq('id', entity.id);
      }
    }
    
    // Update materialized view for fast queries
    await supabase.rpc('refresh_entity_freshness_view');
  }
  ```

#### 2.7 Entity Relationship Discovery (Neo4j)
- **Frequency**: Daily (lightweight pass)
- **Logic**:
  - Run pattern-matching queries on Neo4j to discover new implicit relationships
  - Example: Provider A and Provider B share same facility ZIP code → suggest PRACTICES_NEARBY
  - Example: Drug X and Drug Y have common indication → suggest INDICATED_WITH
  - Create new edges with low confidence, flag for manual review
  - Incrementally build relationship density
- **Pseudocode**:
  ```
  async function discoverNewRelationships() {
    // Pattern 1: Providers in same facility/zip
    const newProximityEdges = await neo4j.run(`
      MATCH (p1:Provider)-[:LICENSED_IN]->(s:State)
      MATCH (p2:Provider)-[:LICENSED_IN]->(s)
      WHERE p1.id < p2.id AND p1.facility_zip = p2.facility_zip
      AND NOT (p1)-[:PRACTICES_NEARBY]-(p2)
      CREATE (p1)-[:PRACTICES_NEARBY {discovered_at: datetime(), confidence: 0.7}]-(p2)
      RETURN COUNT(*) as created
    `);
    
    // Pattern 2: Drugs with shared indications
    const newDrugPairs = await neo4j.run(`
      MATCH (d1:Drug)-[:TREATS]->(c:Condition)
      MATCH (d2:Drug)-[:TREATS]->(c)
      WHERE d1.id < d2.id AND NOT (d1)-[:INDICATED_WITH]-(d2)
      CREATE (d1)-[:INDICATED_WITH {discovered_at: datetime(), confidence: 0.8}]-(d2)
      RETURN COUNT(*) as created
    `);
    
    logger.info(`Discovered ${newProximityEdges} proximity edges, ${newDrugPairs} drug pairs`);
  }
  ```

---

### WEEKLY HEARTBEATS (Sunday 3:00 AM UTC)

**Trigger**: Cron: `0 3 * * 0`  
**SLA**: Complete within 12 hours (before 3:00 PM UTC)

#### 2.8 NPI Weekly Dissemination File Download & Diff
- **Source**: NPI Registry (NPPES) - Monthly full dissemination file
- **Frequency**: Weekly (download, diff against last month)
- **Logic**:
  - Download monthly NPI dissemination file (released by CMS)
  - Diff against previously ingested version
  - Identify: new providers, updated details, deactivations
  - Reconcile with daily incremental updates (catch any API misses)
  - Update `providers` table comprehensively
  - Validate completeness (total provider count matches CMS published count)
- **File Format**: CSV, ~7 million providers, ~500MB

#### 2.9 State Medical Board License Checks
- **Source**: State Medical Board APIs (52 boards: 50 states + DC + US territories)
- **Frequency**: Weekly
- **Logic**:
  - For each provider in HKG with state assignment:
    - Query state board license database for status
    - Check: active, suspended, revoked, expired, renewal pending
    - Flag for alerts if status changed from last check
    - Update `provider_licenses` table
  - Aggregate: Track renewal dates, flag 60/30/14/1 day before expiration
  - This is high-stakes data (patient safety)
- **Pseudocode**:
  ```
  async function checkStateLicensesWeekly() {
    const providersByState = await supabase
      .from('providers')
      .select('id, npi_id, name, state_license')
      .groupBy('state_license');
    
    const stateAdapters = initializeStateBoardAdapters();
    
    for (const [state, providers] of providersByState.entries()) {
      const adapter = stateAdapters[state];
      
      for (const provider of providers) {
        try {
          const licenseStatus = await adapter.checkLicense(
            provider.state_license,
            provider.name
          );
          
          const previousStatus = await supabase
            .from('provider_licenses')
            .select('status, license_number, expiration_date')
            .eq('provider_id', provider.id)
            .eq('state', state)
            .order('verified_at', { ascending: false })
            .limit(1)
            .single();
          
          // Detect status change
          if (previousStatus && previousStatus.status !== licenseStatus.status) {
            await createAlert({
              type: 'LICENSE_STATUS_CHANGE',
              provider_id: provider.id,
              severity: licenseStatus.status === 'REVOKED' ? 'CRITICAL' : 'HIGH',
              message: `${provider.name} license ${previousStatus.status} → ${licenseStatus.status}`,
            });
          }
          
          // Insert/update license record
          await supabase
            .from('provider_licenses')
            .insert({
              provider_id: provider.id,
              state,
              status: licenseStatus.status,
              license_number: licenseStatus.licenseNumber,
              expiration_date: licenseStatus.expirationDate,
              verified_at: new Date(),
              source: 'STATE_BOARD',
            });
          
          // Check expiration approaching
          const daysUntilExpiry = daysDiff(
            new Date(),
            licenseStatus.expirationDate
          );
          if ([1, 14, 30, 60].includes(daysUntilExpiry)) {
            await createAlert({
              type: 'LICENSE_EXPIRATION_APPROACHING',
              provider_id: provider.id,
              severity: 'MEDIUM',
              message: `${provider.name} license expires in ${daysUntilExpiry} days`,
            });
          }
        } catch (error) {
          logger.error(`State license check failed for ${provider.id}:`, error);
          await createAlert({
            type: 'STATE_BOARD_CHECK_FAILED',
            provider_id: provider.id,
            severity: 'LOW',
            message: error.message,
          });
        }
      }
    }
  }
  ```

#### 2.10 Cross-Source Validation Sweep
- **Source**: NPI vs State Boards vs OIG vs SAM.gov
- **Frequency**: Weekly
- **Logic**:
  - For each provider in HKG, trigger the 3-point verification engine
  - Compare fields across sources: name, specialty, status
  - Detect conflicts (e.g., NPI says active, state board says suspended)
  - Update `provider_verification` table with results
  - Flag conflicts as high-priority alerts
  - Calculate overall verification_status per provider
  - Pseudocode in section [3-POINT CROSS-VALIDATION ENGINE](#3-point-cross-validation-engine)

#### 2.11 Knowledge Graph Enrichment (Deep)
- **Frequency**: Weekly
- **Logic**:
  - Run deeper relationship discovery queries
  - Discover provider networks (co-authors in PubMed, shared affiliations)
  - Build drug-condition treatment maps from evidence
  - Create clinical trial relationship chains
  - Calculate centrality metrics (which providers/conditions are most connected)
  - Update Neo4j relationship confidence scores
  - Identify emerging patterns (new clusters)
- **Example Query**:
  ```cypher
  // Find providers who commonly treat the same conditions
  MATCH (p1:Provider)-[:TREATS]->(c:Condition)<-[:TREATS]-(p2:Provider)
  WHERE p1.id < p2.id
  WITH p1, p2, COUNT(c) as shared_conditions
  WHERE shared_conditions >= 5
  MERGE (p1)-[r:TREATS_SIMILAR_CONDITIONS]-(p2)
  SET r.shared_count = shared_conditions, r.updated_at = datetime()
  ```

#### 2.12 Sitemap Regeneration
- **Frequency**: Weekly
- **Logic**:
  - Regenerate XML sitemaps for all entity pages
  - Include: providers, drugs, conditions, clinical trials, drug interactions
  - Use lastmod dates from freshness_verified_at to signal to search engines
  - Include priority scores based on entity importance
  - Submit to search engines (Google, Bing)
  - Generate `sitemap-providers.xml`, `sitemap-drugs.xml`, etc.
- **Pseudocode**:
  ```
  async function regenerateSitemaps() {
    const sitemaps = {};
    
    // Get all entities grouped by type
    const entityCounts = await supabase
      .from('entities')
      .select('type')
      .groupBy('type')
      .then(r => Object.fromEntries(r.map(e => [e.type, 0])));
    
    for (const [entityType, _] of Object.entries(entityCounts)) {
      const entities = await supabase
        .from(entityType)
        .select('id, freshness_verified_at, importance_score')
        .order('importance_score', { ascending: false });
      
      const urls = entities.map(e => ({
        loc: `https://hkg.health/${entityType}/${e.id}`,
        lastmod: e.freshness_verified_at.toISOString().split('T')[0],
        priority: Math.min(1.0, e.importance_score / 100),
        changefreq: 'weekly',
      }));
      
      const xml = generateSitemapXML(urls);
      sitemaps[`sitemap-${entityType}.xml`] = xml;
    }
    
    // Write to static storage
    for (const [filename, xml] of Object.entries(sitemaps)) {
      await storage.write(`/sitemaps/${filename}`, xml);
    }
    
    // Generate sitemap index
    const sitemapIndex = generateSitemapIndexXML(Object.keys(sitemaps));
    await storage.write('/sitemap.xml', sitemapIndex);
    
    // Submit to search engines
    await submitSitemapToGoogle('/sitemap.xml');
    await submitSitemapToBing('/sitemap.xml');
  }
  ```

#### 2.13 llms.txt Refresh
- **Frequency**: Weekly
- **Logic**:
  - Regenerate llms.txt file with updated entity catalog
  - Include: entity count by type, freshness stats, verification rates
  - Format for LLM consumption (machine-readable, schema-aware)
  - Add JSON-LD structured data for key entities
  - Update canonical entity URLs and backlinks
  - Make HKG discoverable and citable by AI systems
- **File Location**: `https://hkg.health/llms.txt`
- **Format**:
  ```
  # Healthcare Knowledge Garden - Entity Catalog
  
  Generated: 2026-04-09T09:00:00Z
  Last Updated: 2026-04-09T09:00:00Z
  
  ## Statistics
  - Total Providers: 2,847,392
  - Total Drugs: 103,844
  - Total Conditions: 14,402 (ICD-10)
  - Total Clinical Trials: 456,829
  - Total Publications: 28,493,012
  
  ## Freshness
  - Fully Verified (24h): 94.2%
  - Verified (7d): 98.1%
  - Verified (30d): 99.7%
  
  ## Entity Types
  
  ### Providers (/provider/[NPI])
  - Count: 2,847,392
  - Freshness: Daily (NPI API)
  - Sources: NPI, State Boards, OIG, SAM
  - Verification: 3-point (NPI + State + OIG)
  - Schema: https://schema.org/MedicalBusiness
  
  ### Drugs (/drug/[NDC])
  - Count: 103,844
  - Freshness: Daily (FDA)
  - Sources: FDA NDC, DailyMed, RxNorm, openFDA
  - Verification: Cross-source validation
  - Schema: https://schema.org/Drug
  
  ### Conditions (/condition/[ICD10])
  - Count: 14,402
  - Freshness: Annual (Oct 1, effective date)
  - Sources: ICD-10-CM, SNOMED-CT, PubMed
  - Verification: Evidence-linked
  - Schema: https://schema.org/MedicalCondition
  
  [... more entity types ...]
  ```

#### 2.14 AI Citation Monitoring
- **Frequency**: Weekly
- **Logic**:
  - Monitor public AI responses (from Claude, GPT, Gemini APIs)
  - Track which HKG entity pages are cited in AI responses
  - Measure citation frequency and context
  - Identify high-impact entities being referenced
  - Generate weekly "Most Cited Entities" report
  - This is a lagging indicator of HKG's moat strength
- **Mechanism**:
  - Use web crawlers / API integrations to capture AI response patterns
  - Parse citations matching HKG domain
  - Store in `ai_citation_tracking` table
  - Calculate citation score: higher citation = higher entity importance

---

### MONTHLY HEARTBEATS (1st of Month, 4:00 AM UTC)

**Trigger**: Cron: `0 4 1 * *`  
**SLA**: Complete within 24 hours

#### 2.15 OIG LEIE Full Refresh
- **Source**: HHS Office of Inspector General - List of Excluded Individuals & Entities (LEIE)
- **Frequency**: Monthly (data released monthly, usually around the 5th)
- **Logic**:
  - Download full LEIE CSV file
  - Parse: exclusion type, name, NPI, exclusion date, etc.
  - Check: Any HKG providers in exclusion list
  - For new exclusions: create CRITICAL alert
  - Update `provider_exclusions` table
  - Mark excluded providers with verification_status = EXCLUDED
  - This prevents any HKG system from recommending excluded providers
- **Pseudocode**:
  ```
  async function refreshOIGLEIEMonthly() {
    const leieFile = await downloadFromOIG(
      'https://oig.hhs.gov/exclusions/downloads/monthly.csv'
    );
    
    const currentExclusions = new Set(
      (await supabase.from('provider_exclusions')
        .select('npi_id')).data.map(e => e.npi_id)
    );
    
    const leieRecords = parseCSV(leieFile);
    const newExclusions = [];
    
    for (const record of leieRecords) {
      const npi = record['NPI'];
      if (!npi) continue;
      
      if (!currentExclusions.has(npi)) {
        newExclusions.push(record);
        
        // This provider is newly excluded
        const provider = await supabase
          .from('providers')
          .select('id, name')
          .eq('npi_id', npi)
          .single();
        
        if (provider) {
          // CRITICAL: Alert the platform
          await createAlert({
            type: 'PROVIDER_EXCLUDED_OIG',
            severity: 'CRITICAL',
            provider_id: provider.id,
            message: `${provider.name} (NPI: ${npi}) excluded by OIG: ${record['Exclusion Type']}`,
            exclusion_date: record['Exclusion Date'],
            effective_date: record['Effective Date'],
          });
          
          // Update provider record
          await supabase
            .from('providers')
            .update({
              verification_status: 'EXCLUDED',
              exclusion_reason: record['Exclusion Type'],
              exclusion_date: record['Exclusion Date'],
            })
            .eq('npi_id', npi);
          
          // De-index from search/recommendations
          await deindexProvider(npi);
        }
      }
      
      // Always update/insert the exclusion record for audit trail
      await supabase
        .from('provider_exclusions')
        .upsert({
          npi_id: npi,
          name: record['Name'],
          exclusion_type: record['Exclusion Type'],
          exclusion_date: parseDate(record['Exclusion Date']),
          effective_date: parseDate(record['Effective Date']),
          source: 'OIG_LEIE',
          updated_at: new Date(),
        }, { onConflict: 'npi_id' });
    }
    
    logger.info(`OIG LEIE Monthly: ${newExclusions.length} new exclusions`);
  }
  ```

#### 2.16 SAM.gov Full Exclusion Refresh
- **Source**: System for Award Management (SAM.gov) - Federal Contractor Debarment
- **Frequency**: Monthly
- **Logic**:
  - Similar to OIG LEIE but broader scope
  - Captures debarred, suspended, and ineligible contractors
  - Federal system; overlaps with OIG but includes different entity types
  - Update `provider_debarments` table
  - Create alerts for newly debarred providers

#### 2.17 RxNorm Monthly Release Ingestion
- **Source**: National Library of Medicine - RxNorm
- **Frequency**: Monthly (released ~first week of month)
- **Logic**:
  - Download RxNorm monthly release (normalized naming/concepts)
  - Parse: RxCUI, drug names, ingredients, strengths, forms
  - Map NDC codes to RxCUI (for normalization)
  - Update `rxnorm_concepts` table
  - Reconcile with previously ingested NDC records
  - Identify newly available drug combinations
  - Flatten hierarchies: active ingredients, form/strength variants
- **Impact**: Critical for drug normalization and interaction checking

#### 2.18 Drug Interaction Database Refresh
- **Source**: FDA (proprietary interactions), DrugBank, Therapeutic Interaction Database
- **Frequency**: Monthly
- **Logic**:
  - Refresh known drug-drug interactions (major, moderate, minor)
  - Update `drug_interactions` table
  - Calculate interaction severity scores
  - Flag high-risk combinations (e.g., warfarin + NSAIDs)
  - Link to supporting evidence (PubMed citations)
  - Critical for clinical safety alerts

#### 2.19 Provider Credential Expiration Scanning
- **Frequency**: Monthly
- **Logic**:
  - Query all provider credentials (licenses, DEA, board certification)
  - Identify approaching expirations
  - Generate alerts: 60 days, 30 days, 14 days, 1 day before
  - Alert severity increases as expiration approaches
  - This is proactive credential management
- **Pseudocode**:
  ```
  async function scanProviderCredentialExpirations() {
    const providers = await supabase
      .from('providers')
      .select(`
        id, name,
        provider_licenses(status, expiration_date, state),
        provider_dea(expiration_date),
        provider_board_certs(specialty, expiration_date)
      `);
    
    const today = new Date();
    const thresholds = [60, 30, 14, 1]; // days before expiration
    
    for (const provider of providers) {
      // Check licenses
      for (const license of provider.provider_licenses || []) {
        const daysUntilExpiry = daysDiff(today, license.expiration_date);
        
        if (thresholds.includes(daysUntilExpiry)) {
          const severity = daysUntilExpiry === 1 ? 'CRITICAL' : 
                          daysUntilExpiry <= 14 ? 'HIGH' : 'MEDIUM';
          
          await createAlert({
            type: 'CREDENTIAL_EXPIRING',
            provider_id: provider.id,
            severity,
            message: `${provider.name} ${license.state} license expires in ${daysUntilExpiry} day(s)`,
            credential_type: 'LICENSE',
            state: license.state,
            expires_at: license.expiration_date,
          });
        }
      }
      
      // Similar checks for DEA, board certifications
      for (const deaRecord of provider.provider_dea || []) {
        const daysUntilExpiry = daysDiff(today, deaRecord.expiration_date);
        if (thresholds.includes(daysUntilExpiry)) {
          await createAlert({
            type: 'CREDENTIAL_EXPIRING',
            provider_id: provider.id,
            severity: 'HIGH', // DEA is high-impact
            message: `${provider.name} DEA license expires in ${daysUntilExpiry} day(s)`,
            credential_type: 'DEA',
            expires_at: deaRecord.expiration_date,
          });
        }
      }
    }
  }
  ```

#### 2.20 System Health Report Generation
- **Frequency**: Monthly
- **Logic**:
  - Aggregate all heartbeat metrics from the month
  - Generate: execution times, success rates, error rates
  - Identify performance bottlenecks
  - Report on data quality improvements
  - Generate executive summary for operators
  - Store in `system_health_reports` table

#### 2.21 Data Quality Metrics Aggregation
- **Frequency**: Monthly
- **Logic**:
  - Calculate global statistics:
    - % of entities at each freshness tier
    - % of providers fully verified vs partially
    - Conflict detection rate (source disagreements)
    - Completeness (% of fields populated)
  - Store time-series data for trending
  - Identify decline in any metric (trigger investigation)

---

### QUARTERLY HEARTBEATS (Jan 1, Apr 1, Jul 1, Oct 1 — 5:00 AM UTC)

**Trigger**: Cron: `0 5 1 1,4,7,10 *`  
**SLA**: Complete within 48 hours

#### 2.22 HCPCS Level II Code Update
- **Source**: CMS Healthcare Common Procedure Coding System
- **Frequency**: Quarterly (updates each quarter)
- **Logic**:
  - Download HCPCS Level II code file
  - Parse: code, description, status (active/deleted)
  - Update `medical_codes_hcpcs` table
  - Map to associated providers/procedures
  - Identify deprecations (deleted codes) and notify affected providers

#### 2.23 SNOMED CT Release Ingestion
- **Source**: SNOMED CT (via UMLS or direct)
- **Frequency**: Quarterly (Jan, Apr, Jul, Oct)
- **Logic**:
  - Ingest latest SNOMED CT release
  - Build concept mappings: SNOMED ↔ ICD-10 ↔ LOINC
  - Update `snomed_concepts` table
  - Identify new hierarchies and relationships
  - Critical for clinical data standardization

#### 2.24 LOINC Update Check
- **Source**: Regenstrief Institute - LOINC (Logical Observation Identifiers Names and Codes)
- **Frequency**: Quarterly (2x per year, usually Mar & Sep)
- **Logic**:
  - Download LOINC file
  - Update `lab_codes_loinc` table
  - Map to associated lab tests, reference ranges
  - Link to clinical significance (interpretation)

#### 2.25 FDA FAERS Quarterly Data Ingestion
- **Source**: FDA Adverse Event Reporting System (FAERS)
- **Frequency**: Quarterly
- **Logic**:
  - Download FAERS data for the quarter
  - Parse: drug name, adverse reaction, severity, outcome
  - Identify new adverse events (signals)
  - Link to affected drugs in HKG
  - Generate alerts for new serious adverse events
  - Populate `adverse_events` table with evidence links
- **Pseudocode**:
  ```
  async function ingestFAERSQuarterly() {
    const quarter = getCurrentQuarter();
    const faersFile = await downloadFAERSData(quarter);
    
    const previousCount = await supabase
      .from('adverse_events')
      .select('id')
      .eq('source', 'FAERS')
      .count();
    
    const faersRecords = parseFAERSFile(faersFile);
    
    for (const record of faersRecords) {
      const drugName = normalizeDrugName(record.drug_name);
      const drug = await supabase
        .from('drugs')
        .select('id, ndc_code')
        .textSearch('name', drugName)
        .limit(1)
        .single();
      
      if (drug) {
        const adverseEvent = {
          drug_id: drug.id,
          adverse_reaction: record.reaction,
          severity: record.severity,
          outcome: record.outcome,
          reported_date: record.report_date,
          source: 'FAERS',
          faers_report_id: record.report_id,
        };
        
        await supabase.from('adverse_events').insert(adverseEvent);
        
        // Signal new serious adverse event
        if (record.severity === 'SERIOUS' && isNewEvent(record)) {
          await createAlert({
            type: 'NEW_SERIOUS_ADVERSE_EVENT',
            severity: 'HIGH',
            drug_id: drug.id,
            message: `New serious adverse event: ${drugName} - ${record.reaction}`,
          });
        }
      }
    }
    
    const newCount = await supabase
      .from('adverse_events')
      .select('id')
      .eq('source', 'FAERS')
      .count();
    
    logger.info(`FAERS Quarterly: ${newCount - previousCount} new events`);
  }
  ```

#### 2.26 CMS Quality Measures Refresh
- **Source**: CMS (Centers for Medicare & Medicaid Services) Quality Reporting System
- **Frequency**: Quarterly
- **Logic**:
  - Download quality measures (MIPS, HCQIS, etc.)
  - Map to providers in HKG
  - Update provider quality scores
  - Compare against benchmarks

#### 2.27 Full Data Integrity Audit
- **Frequency**: Quarterly
- **Logic**:
  - Run comprehensive data validation checks
  - Verify referential integrity (foreign keys)
  - Checksum verification (detect data corruption)
  - Graph consistency (Neo4j edge integrity)
  - Orphaned record detection (entities without sources)
  - Generate audit report
- **Pseudocode**:
  ```
  async function fullDataIntegrityAudit() {
    const audit = {
      timestamp: new Date(),
      checks: [],
    };
    
    // Check 1: Foreign key integrity
    const providerLicenseOrphans = await supabase.rpc(
      'find_orphaned_licenses'
    );
    audit.checks.push({
      name: 'provider_license_referential_integrity',
      status: providerLicenseOrphans.length === 0 ? 'PASS' : 'FAIL',
      orphaned_records: providerLicenseOrphans.length,
    });
    
    // Check 2: Data checksums
    const providers = await supabase
      .from('providers')
      .select('id, data_hash, name, npi_id, specialty');
    
    let checksumMismatches = 0;
    for (const provider of providers) {
      const recalculatedHash = hash(provider.name + provider.npi_id + provider.specialty);
      if (recalculatedHash !== provider.data_hash) {
        checksumMismatches++;
      }
    }
    
    audit.checks.push({
      name: 'provider_data_checksums',
      status: checksumMismatches === 0 ? 'PASS' : 'FAIL',
      mismatches: checksumMismatches,
    });
    
    // Check 3: Neo4j graph consistency
    const danglingNodes = await neo4j.run(`
      MATCH (n:Provider) WHERE NOT (n)-[]-()
      RETURN COUNT(n) as unconnected
    `);
    
    audit.checks.push({
      name: 'neo4j_graph_connectivity',
      status: danglingNodes < providers.length * 0.01 ? 'PASS' : 'FAIL',
      unconnected_nodes: danglingNodes,
      threshold: '< 1% unconnected',
    });
    
    // Store audit report
    await supabase
      .from('system_audit_reports')
      .insert(audit);
    
    // Alert if any check failed
    if (audit.checks.some(c => c.status === 'FAIL')) {
      await createAlert({
        type: 'DATA_INTEGRITY_FAILURE',
        severity: 'CRITICAL',
        message: `Data integrity audit failed: ${audit.checks.filter(c => c.status === 'FAIL').map(c => c.name).join(', ')}`,
        audit_report_id: audit.id,
      });
    }
  }
  ```

#### 2.28 Performance Optimization Review
- **Frequency**: Quarterly
- **Logic**:
  - Analyze query performance metrics
  - Identify slow-running heartbeat tasks
  - Review database indexes
  - Optimize Neo4j queries if needed
  - Right-size infrastructure

---

### ANNUAL HEARTBEATS

#### 2.29 ICD-10-CM New Fiscal Year Code Set (Effective Oct 1)
- **Source**: CDC / CMS
- **Frequency**: Annual (October 1)
- **Logic**:
  - Download new ICD-10-CM code set effective Oct 1
  - Identify new codes, deleted codes, code changes
  - Update `medical_codes_icd10` table
  - Map to conditions, procedures, providers
  - Generate deprecation alerts for deleted codes
  - This is high-impact: entire diagnostic system updates annually

#### 2.30 ICD-10-PCS Update (Effective Apr 1)
- **Source**: CMS
- **Frequency**: Annual (April 1)
- **Logic**:
  - Similar to ICD-10-CM but for procedures
  - Update procedure coding tables

#### 2.31 MS-DRG Annual Update
- **Source**: CMS
- **Frequency**: Annual (October 1)
- **Logic**:
  - Medicare Severity Diagnosis-Related Groups
  - Used for inpatient billing, reimbursement
  - Update `drg_codes` table

#### 2.32 CMS Fee Schedule Updates
- **Source**: CMS Physician Fee Schedule
- **Frequency**: Annual (typically January)
- **Logic**:
  - CPT code reimbursement rates change annually
  - Update `cpt_fee_schedule` table
  - Map to provider reimbursement expectations

#### 2.33 Full NPI Database Reconciliation
- **Source**: NPI Registry (monthly full file)
- **Frequency**: Annual (reconcile all accumulated daily increments against full file)
- **Logic**:
  - Download full NPI dissemination file
  - Compare against accumulated incremental updates
  - Verify no records were missed by daily API
  - Resolve conflicts (if any)
  - Confirm total provider count matches CMS published count
- **Pseudocode**:
  ```
  async function fullNPIReconciliation() {
    const fullFile = await downloadNPIFullDissemination();
    const npisInFile = new Set();
    
    const records = parseNPIFile(fullFile);
    for (const record of records) {
      npisInFile.add(record.npi);
      
      const dbRecord = await supabase
        .from('providers')
        .select('*')
        .eq('npi_id', record.npi)
        .single();
      
      if (!dbRecord) {
        logger.warn(`NPI ${record.npi} in full file but not in DB. Ingesting.`);
        await ingestNPIRecord(record);
      } else {
        // Verify key fields match
        if (dbRecord.name !== normalizeString(record.name)) {
          logger.warn(`NPI ${record.npi} name mismatch: DB="${dbRecord.name}" vs File="${record.name}"`);
        }
      }
    }
    
    // Find orphans in DB
    const dbNPIs = (await supabase
      .from('providers')
      .select('npi_id')).data.map(p => p.npi_id);
    
    const orphanNPIs = dbNPIs.filter(npi => !npisInFile.has(npi));
    if (orphanNPIs.length > 0) {
      logger.warn(`Found ${orphanNPIs.length} orphan NPIs in DB not in current file. Marking as DEACTIVATED.`);
      await supabase
        .from('providers')
        .update({ status: 'DEACTIVATED' })
        .in('npi_id', orphanNPIs);
    }
    
    logger.info(`NPI Reconciliation: File has ${npisInFile.size} providers, DB has ${dbNPIs.length}`);
  }
  ```

#### 2.34 Annual Compliance Audit
- **Frequency**: Annual
- **Logic**:
  - Comprehensive compliance check (HIPAA, accessibility, data retention)
  - Verify security controls are in place
  - Audit access logs
  - Generate compliance report

#### 2.35 Knowledge Base Size / Growth Report
- **Frequency**: Annual
- **Logic**:
  - Calculate total knowledge base metrics:
    - Total entities (providers, drugs, conditions, trials, publications)
    - Total relationships in graph
    - Graph density metrics
    - Compare year-over-year growth
  - Generate board-level report
  - Showcase compounding advantage

---

## HEARTBEAT ARCHITECTURE

The heartbeat system is organized into modular, independently deployable units. Each component has clear interfaces and can fail gracefully without cascading.

```
┌─────────────────────────────────────────────────────────────────┐
│                        HEARTBEAT RUNNER                         │
│                   (Central Orchestrator)                        │
└─────────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
        ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
        │  Scheduler   │ │   Registry   │ │    Queue     │
        │(Cron-based)  │ │ (Task state) │ │(Async tasks) │
        └──────────────┘ └──────────────┘ └──────────────┘
              │               │               │
              └───────────────┼───────────────┘
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
        ┌─────────────────┐           ┌──────────────────┐
        │  Source Adapters│           │ Transform Pipeline│
        │                 │           │                  │
        │ - NPI Adapter   │           │ - Normalizer     │
        │ - NDC Adapter   │           │ - Deduplicator   │
        │ - OIG Adapter   │           │ - Validator      │
        │ - PubMed Adapter│           │ - Enricher       │
        │ - And 20+ more  │           │ - GraphBuilder   │
        └─────────────────┘           └──────────────────┘
              │                               │
              └───────────────┬───────────────┘
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
        ┌─────────────────┐           ┌──────────────────┐
        │  Load Targets   │           │ Quality Monitor  │
        │                 │           │                  │
        │ - Supabase      │           │ - FreshnessScore │
        │ - Neo4j         │           │ - ConflictDetect │
        │ - WebGenerator  │           │ - CompleteFill   │
        │ - Cache Layer   │           │ - ConsistencyVal │
        └─────────────────┘           └──────────────────┘
              │                               │
              └───────────────┬───────────────┘
                              │
                    ┌─────────┴──────────┐
                    ▼                    ▼
            ┌──────────────┐      ┌──────────────────┐
            │   Alerting   │      │ System Dashboard │
            │              │      │                  │
            │ - Slack      │      │ - Metrics        │
            │ - Email      │      │ - Logs           │
            │ - In-App     │      │ - Status         │
            │ - Webhooks   │      │ - Health Scores  │
            └──────────────┘      └──────────────────┘
```

### 3.1 HeartbeatRunner (Orchestrator)

```typescript
interface HeartbeatTask {
  id: string;
  name: string;
  schedule: string; // cron expression
  timeout: number; // milliseconds
  adapter: SourceAdapter;
  pipeline: TransformPipeline;
  targets: LoadTarget[];
  priority: 'critical' | 'high' | 'normal' | 'low';
  retryPolicy: RetryPolicy;
}

interface RetryPolicy {
  maxAttempts: number;
  backoffMultiplier: number; // exponential backoff
  maxBackoffMs: number;
}

class HeartbeatRunner {
  private scheduler: Cron;
  private taskRegistry: Map<string, HeartbeatTask>;
  private queue: AsyncQueue;
  private metrics: MetricsCollector;

  async initialize() {
    // Load all heartbeat task definitions
    this.taskRegistry = await this.loadTaskDefinitions();
    
    // Schedule all cron jobs
    for (const [taskId, task] of this.taskRegistry.entries()) {
      this.scheduler.schedule(task.schedule, () => {
        this.enqueueTask(taskId);
      });
    }
    
    // Start queue processor
    this.queue.start((task) => this.executeTask(task));
  }

  async executeTask(taskId: string) {
    const task = this.taskRegistry.get(taskId);
    const startTime = Date.now();
    
    try {
      // Step 1: Fetch data from source
      const sourceData = await task.adapter.fetch();
      
      // Step 2: Transform
      const transformed = await task.pipeline.transform(sourceData);
      
      // Step 3: Load to targets
      const results = await Promise.all(
        task.targets.map(target => target.load(transformed))
      );
      
      // Step 4: Record success
      this.metrics.recordSuccess(taskId, Date.now() - startTime);
      
      return { status: 'SUCCESS', results };
      
    } catch (error) {
      this.metrics.recordFailure(taskId, error);
      
      // Determine if retryable
      if (task.retryPolicy && this.isRetryable(error)) {
        await this.scheduleRetry(taskId, task.retryPolicy);
        
        await createAlert({
          type: 'HEARTBEAT_RETRY',
          severity: 'MEDIUM',
          task_id: taskId,
          error: error.message,
        });
      } else {
        await createAlert({
          type: 'HEARTBEAT_FAILURE',
          severity: task.priority === 'critical' ? 'CRITICAL' : 'HIGH',
          task_id: taskId,
          error: error.message,
        });
      }
      
      throw error;
    }
  }

  private isRetryable(error: Error): boolean {
    // Network errors: retryable
    // Validation errors: not retryable
    // Timeout errors: retryable with backoff
    return error instanceof NetworkError || 
           error instanceof TimeoutError;
  }
}
```

### 3.2 SourceAdapters

Each source has its own adapter with a consistent interface:

```typescript
interface SourceAdapter {
  name: string;
  sourceURL: string;
  lastFetch?: Date;
  
  async fetch(options?: FetchOptions): Promise<RawSourceData>;
  async validateResponse(data: RawSourceData): Promise<boolean>;
  async getMetadata(): Promise<SourceMetadata>;
}

class NPIAdapter implements SourceAdapter {
  name = 'NPI Registry';
  sourceURL = 'https://npiregistry.cms.hhs.gov';

  async fetch(options?: { sinceDate?: Date }): Promise<RawSourceData> {
    if (options?.sinceDate) {
      // Incremental: fetch only updated records
      return this.fetchIncremental(options.sinceDate);
    } else {
      // Full: download dissemination file
      return this.fetchFullDissemination();
    }
  }

  private async fetchIncremental(sinceDate: Date): Promise<RawSourceData> {
    const records = [];
    const pageSize = 200;
    let skip = 0;
    
    while (true) {
      const response = await fetch(
        `${this.sourceURL}/api/?version=2.1&skip=${skip}&limit=${pageSize}`,
        {
          headers: { 'Accept': 'application/json' }
        }
      );
      
      const data = await response.json();
      if (!data.results || data.results.length === 0) break;
      
      // Filter to updated-since
      const updated = data.results.filter(r => 
        new Date(r.basic.last_updated) >= sinceDate
      );
      records.push(...updated);
      
      skip += pageSize;
    }
    
    return { source: 'NPI', records, fetchedAt: new Date() };
  }

  private async fetchFullDissemination(): Promise<RawSourceData> {
    // Download from NPI's public dissemination file
    const url = 'https://npiregistry.cms.hhs.gov/PublicPortal/downloadNPI';
    
    const response = await fetch(url);
    const buffer = await response.arrayBuffer();
    const file = await unzip(buffer); // NPI file is zipped
    const csv = await file.text();
    
    const records = parseCSV(csv);
    
    return { source: 'NPI', records, fetchedAt: new Date() };
  }

  async validateResponse(data: RawSourceData): Promise<boolean> {
    // Basic validation
    if (!data.records || data.records.length === 0) {
      throw new Error('No records returned from NPI');
    }
    
    // Spot-check: verify expected fields present
    const sample = data.records[0];
    const requiredFields = ['npi', 'basic', 'taxonomies'];
    for (const field of requiredFields) {
      if (!(field in sample)) {
        throw new Error(`Missing required field: ${field}`);
      }
    }
    
    return true;
  }

  async getMetadata(): Promise<SourceMetadata> {
    return {
      source: 'NPI',
      lastFetch: this.lastFetch,
      recordCount: 2847392, // from CMS published stats
      updateFrequency: 'DAILY',
      coverage: 'ALL_US_PROVIDERS',
    };
  }
}

class OIGAdapter implements SourceAdapter {
  name = 'OIG LEIE';
  sourceURL = 'https://oig.hhs.gov/exclusions';

  async fetch(): Promise<RawSourceData> {
    const csvUrl = 'https://oig.hhs.gov/exclusions/downloads/monthly.csv';
    const response = await fetch(csvUrl);
    const csv = await response.text();
    
    const records = parseCSV(csv);
    
    return { source: 'OIG', records, fetchedAt: new Date() };
  }

  // ... validateResponse, getMetadata
}

// ... similar adapters for NDC, DailyMed, PubMed, etc.
```

### 3.3 TransformPipeline

```typescript
interface TransformPipeline {
  normalize(rawData: RawData): NormalizedData;
  deduplicate(data: NormalizedData): DeduplicatedData;
  validate(data: DeduplicatedData): ValidationResult;
  enrich(data: DeduplicatedData): EnrichedData;
  buildGraph(data: EnrichedData): GraphData;
}

class DefaultTransformPipeline implements TransformPipeline {
  
  normalize(rawData: RawData): NormalizedData {
    // Example: Normalize provider names across sources
    // "JOHN SMITH MD" + "John Smith, M.D." → "John Smith"
    
    return rawData.map(record => ({
      ...record,
      normalized_name: normalizeName(record.name),
      normalized_date: normalizeDate(record.date),
      normalized_specialty: normalizeSpecialty(record.specialty),
    }));
  }

  deduplicate(data: NormalizedData): DeduplicatedData {
    // Merge records for the same entity across sources
    const byEntityId = new Map();
    
    for (const record of data) {
      const key = record.npi_id || record.ndc_code || record.identifier;
      
      if (byEntityId.has(key)) {
        const existing = byEntityId.get(key);
        // Merge: keep best version of each field
        byEntityId.set(key, mergeRecords(existing, record));
      } else {
        byEntityId.set(key, record);
      }
    }
    
    return Array.from(byEntityId.values());
  }

  validate(data: DeduplicatedData): ValidationResult {
    const errors = [];
    const warnings = [];
    
    for (const record of data) {
      // Check required fields
      if (!record.npi_id && !record.name) {
        errors.push(`Record missing identifier: ${record}`);
      }
      
      // Check format validations
      if (record.npi_id && !isValidNPI(record.npi_id)) {
        errors.push(`Invalid NPI format: ${record.npi_id}`);
      }
      
      // Check business logic
      if (record.status === 'REVOKED' && record.expiration_date > new Date()) {
        warnings.push(`Revoked provider has future expiration: ${record.npi_id}`);
      }
    }
    
    return { valid: errors.length === 0, errors, warnings };
  }

  enrich(data: DeduplicatedData): EnrichedData {
    // Add computed fields, scores, metadata
    
    return data.map(record => ({
      ...record,
      freshness_score: this.calculateFreshnessScore(record),
      importance_score: this.calculateImportanceScore(record),
      data_completeness: this.calculateCompleteness(record),
      source_count: record.data_sources?.length || 1,
    }));
  }

  buildGraph(data: EnrichedData): GraphData {
    // Create nodes and edges for Neo4j
    
    const nodes = [];
    const edges = [];
    
    for (const record of data) {
      // Create node
      nodes.push({
        type: record.entity_type,
        id: record.id,
        properties: {
          name: record.name,
          freshness_score: record.freshness_score,
          ...record,
        },
      });
      
      // Create edges based on relationships
      if (record.entity_type === 'Provider' && record.facility_id) {
        edges.push({
          source: record.id,
          type: 'WORKS_AT',
          target: record.facility_id,
        });
      }
      
      if (record.entity_type === 'Drug' && record.indication_codes) {
        for (const icd10Code of record.indication_codes) {
          edges.push({
            source: record.id,
            type: 'TREATS',
            target: icd10Code,
          });
        }
      }
    }
    
    return { nodes, edges };
  }

  private calculateFreshnessScore(record: any): number {
    // Per entity type, calculate freshness decay
    const daysSinceVerified = daysDiff(new Date(), record.verified_at);
    
    const decayRates = {
      'Provider': { half_life: 30 }, // decays to 50 in 30 days
      'Drug': { half_life: 90 },
      'Condition': { half_life: 365 },
      'ClinicalTrial': { half_life: 14 },
    };
    
    const rate = decayRates[record.entity_type] || { half_life: 30 };
    const decayFactor = Math.pow(0.5, daysSinceVerified / rate.half_life);
    
    return Math.round(100 * decayFactor);
  }

  private calculateImportanceScore(record: any): number {
    // Importance based on multiple factors
    let score = 0;
    
    if (record.entity_type === 'Provider') {
      // More data sources = more important
      score += record.data_sources.length * 10;
      
      // Verification status matters
      if (record.verification_status === 'FULLY_VERIFIED') score += 30;
      if (record.verification_status === 'PARTIALLY_VERIFIED') score += 15;
      
      // High-volume activity = important
      if (record.patient_volume > 10000) score += 25;
    }
    
    return Math.min(100, score);
  }

  private calculateCompleteness(record: any): number {
    const fieldCount = Object.keys(record).length;
    const nullCount = Object.values(record).filter(v => v === null).length;
    
    return Math.round(100 * ((fieldCount - nullCount) / fieldCount));
  }
}
```

### 3.4 LoadTargets

```typescript
interface LoadTarget {
  name: string;
  async load(data: EnrichedData | GraphData): Promise<LoadResult>;
  async validate(): Promise<boolean>; // health check
}

class SupabaseLoader implements LoadTarget {
  name = 'Supabase (PostgreSQL)';

  async load(data: EnrichedData): Promise<LoadResult> {
    const { inserted, updated, failed } = {
      inserted: 0,
      updated: 0,
      failed: 0,
    };
    
    for (const record of data) {
      try {
        const result = await supabase
          .from(record.entity_type_table)
          .upsert(record, { onConflict: 'id' });
        
        if (result.count > 0) {
          if (record.created_at === new Date()) {
            inserted++;
          } else {
            updated++;
          }
        }
      } catch (error) {
        logger.error(`Failed to load record ${record.id}:`, error);
        failed++;
      }
    }
    
    return {
      target: this.name,
      inserted,
      updated,
      failed,
      timestamp: new Date(),
    };
  }

  async validate(): Promise<boolean> {
    // Health check: can we connect and query?
    try {
      const result = await supabase
        .from('providers')
        .select('id')
        .limit(1);
      
      return result.data !== null;
    } catch {
      return false;
    }
  }
}

class Neo4jLoader implements LoadTarget {
  name = 'Neo4j (Graph Database)';

  async load(data: GraphData): Promise<LoadResult> {
    const { created: nodeCount, relationships } = {
      created: 0,
      relationships: 0,
    };
    
    // Load nodes
    for (const node of data.nodes) {
      const query = `
        MERGE (n:${node.type} {id: $id})
        SET n += $properties
        RETURN id(n)
      `;
      
      await this.session.run(query, {
        id: node.id,
        properties: node.properties,
      });
    }
    
    // Load relationships
    for (const edge of data.edges) {
      const query = `
        MATCH (source {id: $sourceId})
        MATCH (target {id: $targetId})
        MERGE (source)-[r:${edge.type}]->(target)
        SET r.updated_at = datetime()
        RETURN id(r)
      `;
      
      await this.session.run(query, {
        sourceId: edge.source,
        targetId: edge.target,
      });
    }
    
    return {
      target: this.name,
      inserted: nodeCount,
      relationships,
      timestamp: new Date(),
    };
  }
}

class WebPageGenerator implements LoadTarget {
  name = 'Static Page Generator';

  async load(data: EnrichedData): Promise<LoadResult> {
    let pagesGenerated = 0;
    
    for (const record of data) {
      const html = await this.generateEntityPage(record);
      const path = this.getPagePath(record);
      
      await fs.writeFile(path, html);
      pagesGenerated++;
      
      // Also generate JSON-LD for this page
      const jsonld = this.generateJsonLD(record);
      await fs.writeFile(path.replace('.html', '.json'), jsonld);
    }
    
    return {
      target: this.name,
      inserted: pagesGenerated,
      timestamp: new Date(),
    };
  }

  private generateEntityPage(record: any): string {
    // HTML template for entity page
    // Includes: freshness metadata, source citations, verification status
    
    return `
      <!DOCTYPE html>
      <html>
        <head>
          <title>${record.name} | Healthcare Knowledge Garden</title>
          <meta name="freshness" content="${record.freshness_score}">
          <meta name="verified-at" content="${record.freshness_verified_at}">
          <script type="application/ld+json">
            ${this.generateJsonLD(record)}
          </script>
        </head>
        <body>
          <h1>${record.name}</h1>
          <div class="metadata">
            <p>Freshness: ${record.freshness_score}/100</p>
            <p>Verification Status: ${record.verification_status}</p>
            <p>Last Updated: ${record.freshness_verified_at}</p>
          </div>
          <div class="sources">
            <h2>Data Sources</h2>
            ${record.data_sources.map(s => `<li>${s}</li>`).join('')}
          </div>
        </body>
      </html>
    `;
  }

  private generateJsonLD(record: any): string {
    // Structured data for search engines and AI
    const schema = {
      '@context': 'https://schema.org',
      '@type': this.mapEntityTypeToSchemaType(record.entity_type),
      name: record.name,
      url: this.getCanonicalURL(record),
      dateModified: record.freshness_verified_at,
      citation: record.data_sources.map(source => ({
        '@type': 'Thing',
        name: source,
        url: this.getSourceURL(source),
      })),
    };
    
    return JSON.stringify(schema, null, 2);
  }
}
```

---

## DATA FRESHNESS SCORING MODEL

Every entity in HKG has a freshness score (0-100) that decays over time based on entity type and update frequency.

### Freshness Score Calculation

```
freshness_score(t) = 100 * 2^(-t / half_life)

Where:
  t = days since last verification
  half_life = decay rate for entity type
```

### Entity Type Decay Rates

| Entity Type | Half-Life | Rationale |
|-------------|-----------|-----------|
| Provider | 30 days | High-stakes: licenses expire, deactivations are critical |
| Drug | 90 days | Monthly RxNorm updates, but less frequent changes |
| Condition (ICD-10) | 365 days | Only changes annually (October) |
| Clinical Trial | 14 days | Status changes frequently (recruiting → closed) |
| Drug Interaction | 30 days | Recommendations update with new evidence |
| PubMed Citation | Never | Publication date is permanent |
| Medical Code (CPT/HCPCS) | 180 days | Updates quarterly/annually |

### Freshness Tiers

| Score | Status | Action |
|-------|--------|--------|
| 90-100 | Verified (< 24h) | Trust as current; show freshness badge |
| 75-89 | Verified (< 7d) | Trust with minor caveat; show "updated recently" |
| 50-74 | Verified (< 30d) | Display freshness warning; queue for re-verification |
| 25-49 | Verified (< 90d) | Display "stale data" warning; prioritize re-verification |
| 0-24 | Stale (> 90d) | Grayed out; strong "unverified" warning; DON'T use in recommendations |

### Pseudocode: Freshness Scoring Function

```typescript
function calculateFreshnessScore(
  entity: Entity,
  lastVerifiedAt: Date,
  now: Date = new Date()
): number {
  const daysSinceVerification = daysDiff(lastVerifiedAt, now);
  
  // Entity type to decay rate mapping
  const decayRates = {
    'PROVIDER': 30,
    'DRUG': 90,
    'CONDITION': 365,
    'CLINICAL_TRIAL': 14,
    'PUBMED_CITATION': Infinity, // never decays
  };
  
  const halfLife = decayRates[entity.type] || 30;
  
  if (halfLife === Infinity) {
    return 100; // Never decays
  }
  
  // Calculate exponential decay
  const decayFactor = Math.pow(2, -daysSinceVerification / halfLife);
  const score = Math.round(100 * decayFactor);
  
  return Math.max(0, Math.min(100, score)); // Clamp [0, 100]
}

// Example usage:
const provider = {
  npi_id: '1234567890',
  name: 'Dr. Smith',
  type: 'PROVIDER',
};

const lastVerified = new Date('2026-04-01');
const now = new Date('2026-04-09');

const score = calculateFreshnessScore(provider, lastVerified, now);
// 8 days have passed
// half_life = 30 days
// decay = 2^(-8/30) = 0.826
// score = 83 (Freshness tier: 75-89)
```

### Freshness Scoring at Scale

For HKG with millions of entities, freshness scoring must be efficient:

```sql
-- PostgreSQL materialized view for fast freshness queries
CREATE MATERIALIZED VIEW entity_freshness_tiers AS
WITH freshness_calc AS (
  SELECT
    id,
    entity_type,
    freshness_verified_at,
    NOW() - freshness_verified_at as age_days,
    -- Calculate freshness score with exponential decay
    CASE
      WHEN entity_type = 'PROVIDER' THEN
        ROUND(100 * POWER(2, -((NOW()::date - freshness_verified_at::date)::numeric / 30)))
      WHEN entity_type = 'DRUG' THEN
        ROUND(100 * POWER(2, -((NOW()::date - freshness_verified_at::date)::numeric / 90)))
      WHEN entity_type = 'CONDITION' THEN
        ROUND(100 * POWER(2, -((NOW()::date - freshness_verified_at::date)::numeric / 365)))
      WHEN entity_type = 'CLINICAL_TRIAL' THEN
        ROUND(100 * POWER(2, -((NOW()::date - freshness_verified_at::date)::numeric / 14)))
      ELSE 100
    END as freshness_score
  FROM entities
)
SELECT
  id,
  entity_type,
  freshness_score,
  CASE
    WHEN freshness_score >= 90 THEN 'VERIFIED_24H'
    WHEN freshness_score >= 75 THEN 'VERIFIED_7D'
    WHEN freshness_score >= 50 THEN 'VERIFIED_30D'
    WHEN freshness_score >= 25 THEN 'VERIFIED_90D'
    ELSE 'STALE'
  END as freshness_tier,
  age_days
FROM freshness_calc;

-- Refresh every day after heartbeat completes
REFRESH MATERIALIZED VIEW entity_freshness_tiers;
```

---

## 3-POINT CROSS-VALIDATION ENGINE

The 3-point verification system is HKG's truth-finding mechanism. No single source is authoritative; conflicts surface as high-value signals.

### Primary Verification Sources

For **Providers**:

1. **NPI Registry** (Federal / CMS)
   - Authoritative provider registration
   - Best for: basic demographics, taxonomy codes, status

2. **State Medical Board** (State)
   - Authoritative licensure
   - Best for: license status, specialty, expiration dates

3. **OIG/SAM Exclusion Lists** (Federal)
   - Authoritative compliance clearance
   - Best for: exclusion status, debarment

### Bonus Layers

4. **ABMS/Specialty Boards** (Professional)
   - Board certification verification
   - Best for: board-certified status

5. **NPDB** (National Practitioner Data Bank)
   - Adverse actions, malpractice history
   - Best for: sanctions, judgments

6. **DEA Database**
   - Controlled substance authority
   - Best for: DEA registration status, expiration

### Verification State Machine

```
                    ┌──────────────────┐
                    │    UNVERIFIED    │
                    │  (Initial state) │
                    └────────┬─────────┘
                             │ Start verification
                             ▼
                    ┌──────────────────┐
          ┌────────→│  PENDING_CHECK   │←────────┐
          │         │  (Checking 1/3)  │         │
          │         └────────┬─────────┘         │
          │                  │ All checks pass   │
          │                  ▼                   │
          │         ┌──────────────────┐         │
          │         │ PARTIALLY_VERIFIED│         │
          │         │   (1-2 sources)  │         │
          │         └────────┬─────────┘         │
          │                  │ 3rd source passes │
          │                  ▼                   │
          │         ┌──────────────────┐         │
          │    ┌───→│ FULLY_VERIFIED   │         │
          │    │    │ (3/3 sources OK) │         │
          │    │    └────────┬─────────┘         │
          │    │             │                   │
          └────┤   Check fails / conflicts detected
               │             ▼
               │    ┌──────────────────┐
               │    │CONFLICT_DETECTED │
               │    │ (Sources disagree)
               │    └────────┬─────────┘
               │             │ Manual review
               │             ▼
               │    ┌──────────────────┐
               └───→│    UNVERIFIED    │
                    │(Return to start) │
                    └──────────────────┘

Additional state:
                    ┌──────────────────┐
      From any ────→│     EXPIRED      │
                    │(Verification     │
                    │ past freshness   │
                    │ threshold)       │
                    └──────────────────┘
```

### 3-Point Verification Algorithm

```typescript
interface VerificationResult {
  npi_id: string;
  status: VerificationStatus;
  sources: SourceVerification[];
  conflicts: Conflict[];
  overallTrust: number; // 0-100
  timestamp: Date;
}

interface SourceVerification {
  source: 'NPI' | 'STATE_BOARD' | 'OIG_SAM' | 'ABMS' | 'NPDB' | 'DEA';
  status: 'VERIFIED' | 'NOT_FOUND' | 'CONFLICT' | 'ERROR';
  data: Record<string, any>;
  confidence: number; // 0-100
  timestamp: Date;
}

interface Conflict {
  field: string;
  source1: string;
  value1: any;
  source2: string;
  value2: any;
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
}

async function threePointVerification(npi_id: string): Promise<VerificationResult> {
  const result: VerificationResult = {
    npi_id,
    status: 'PENDING_CHECK',
    sources: [],
    conflicts: [],
    overallTrust: 0,
    timestamp: new Date(),
  };
  
  try {
    // Source 1: NPI Registry
    const npiData = await verifyNPI(npi_id);
    result.sources.push({
      source: 'NPI',
      status: npiData ? 'VERIFIED' : 'NOT_FOUND',
      data: npiData,
      confidence: 95, // NPI is highly authoritative
      timestamp: new Date(),
    });
    
    if (!npiData) {
      result.status = 'UNVERIFIED';
      return result;
    }
    
    // Source 2: State Medical Board
    const stateData = await verifyStateBoard(
      npiData.last_name,
      npiData.first_name,
      npiData.state
    );
    result.sources.push({
      source: 'STATE_BOARD',
      status: stateData ? 'VERIFIED' : 'NOT_FOUND',
      data: stateData,
      confidence: stateData ? 90 : 0, // High confidence if found
      timestamp: new Date(),
    });
    
    // Source 3: OIG/SAM Exclusions
    const oigData = await verifyOIG(npi_id);
    result.sources.push({
      source: 'OIG_SAM',
      status: oigData.excluded ? 'VERIFIED' : 'VERIFIED', // Always verified (absence is verification)
      data: oigData,
      confidence: 95,
      timestamp: new Date(),
    });
    
    // Cross-check for conflicts
    if (npiData && stateData) {
      const conflicts = detectConflicts(npiData, stateData);
      result.conflicts.push(...conflicts);
    }
    
    // CRITICAL: If OIG says excluded, that overrides everything
    if (oigData.excluded) {
      result.status = 'EXCLUDED';
      result.overallTrust = 0;
      return result;
    }
    
    // Determine verification status based on source coverage
    const verifiedSources = result.sources.filter(
      s => s.status === 'VERIFIED' && s.confidence > 50
    ).length;
    
    if (verifiedSources >= 3) {
      result.status = result.conflicts.length > 0 ? 'CONFLICT_DETECTED' : 'FULLY_VERIFIED';
      result.overallTrust = 90;
    } else if (verifiedSources >= 2) {
      result.status = 'PARTIALLY_VERIFIED';
      result.overallTrust = 70;
    } else if (verifiedSources >= 1) {
      result.status = 'PARTIALLY_VERIFIED';
      result.overallTrust = 40;
    } else {
      result.status = 'UNVERIFIED';
      result.overallTrust = 0;
    }
    
    // Bonus verification layers
    const abmsData = await verifyABMS(npiData);
    if (abmsData) {
      result.sources.push({
        source: 'ABMS',
        status: 'VERIFIED',
        data: abmsData,
        confidence: 85,
        timestamp: new Date(),
      });
      if (abmsData.board_certified) {
        result.overallTrust += 10; // Boost trust for board certification
      }
    }
    
    const npdbData = await verifyNPDB(npi_id);
    if (npdbData) {
      result.sources.push({
        source: 'NPDB',
        status: 'VERIFIED',
        data: npdbData,
        confidence: 90,
        timestamp: new Date(),
      });
      if (npdbData.adverse_actions && npdbData.adverse_actions.length > 0) {
        result.conflicts.push({
          field: 'adverse_actions',
          source1: 'NPI',
          value1: 'No adverse actions reported',
          source2: 'NPDB',
          value2: `${npdbData.adverse_actions.length} adverse action(s)`,
          severity: 'HIGH',
        });
        result.overallTrust = Math.max(0, result.overallTrust - 20);
      }
    }
    
    // Clamp trust score
    result.overallTrust = Math.max(0, Math.min(100, result.overallTrust));
    
    return result;
    
  } catch (error) {
    logger.error(`3-point verification failed for ${npi_id}:`, error);
    
    result.status = 'ERROR';
    result.sources.push({
      source: 'ERROR',
      status: 'ERROR',
      data: { error: error.message },
      confidence: 0,
      timestamp: new Date(),
    });
    
    result.overallTrust = 0;
    
    return result;
  }
}

function detectConflicts(npiData: any, stateData: any): Conflict[] {
  const conflicts: Conflict[] = [];
  
  // Check license status alignment
  if (npiData.status !== 'ACTIVE' && stateData.status === 'ACTIVE') {
    conflicts.push({
      field: 'status',
      source1: 'NPI',
      value1: npiData.status,
      source2: 'STATE_BOARD',
      value2: stateData.status,
      severity: 'CRITICAL',
    });
  }
  
  // Check name alignment (fuzzy match)
  const npiName = `${npiData.first_name} ${npiData.last_name}`.toLowerCase();
  const stateName = stateData.name.toLowerCase();
  
  const similarity = calculateStringSimilarity(npiName, stateName);
  if (similarity < 0.85) { // Fuzzy match threshold
    conflicts.push({
      field: 'name',
      source1: 'NPI',
      value1: npiName,
      source2: 'STATE_BOARD',
      value2: stateName,
      severity: 'MEDIUM',
    });
  }
  
  // Check specialty alignment
  if (npiData.taxonomy_code !== stateData.specialty_code) {
    conflicts.push({
      field: 'specialty',
      source1: 'NPI',
      value1: npiData.taxonomy_code,
      source2: 'STATE_BOARD',
      value2: stateData.specialty_code,
      severity: 'LOW',
    });
  }
  
  return conflicts;
}
```

---

## KNOWLEDGE GRAPH ENRICHMENT

The Neo4j graph is the platform's competitive moat. The heartbeat continuously discovers new relationships, making the graph denser and more powerful over time.

### Relationship Types

| Relationship | Source | Discovery Method |
|--------------|--------|------------------|
| PRACTICES_AT | NPI + State Board | Direct data mapping |
| TREATS | PubMed + ClinicalTrials | Evidence extraction |
| TRAINED_AT | ERAS/Educational data | Educational history |
| COLLEAGUES_WITH | Co-authorship, facility | Network analysis |
| SPECIALIZES_IN | NPI taxonomy + board certs | Direct data mapping |
| INDICATED_WITH | Drug interactions + PubMed | Evidence synthesis |
| CONTRAINDICATED_WITH | FDA/drug labels | Safety data |
| CAUSES | FAERS + medical literature | Adverse event analysis |
| MAPS_TO | ICD-10 ↔ SNOMED ↔ LOINC | Code standardization |
| CITES_EVIDENCE | Trial results + publications | Evidence linking |
| MEMBER_OF | Professional societies | Membership data |
| LICENSED_IN | State boards | Licensure data |
| EXCLUDED_BY | OIG/SAM | Compliance data |

### Example: Automatic Relationship Discovery

```cypher
// Pattern 1: Providers treating similar conditions have potential referral relationships
MATCH (p1:Provider)-[:TREATS]->(c:Condition)<-[:TREATS]-(p2:Provider)
WHERE p1.id < p2.id
  AND p1.location_zip = p2.location_zip
  AND COUNT(c) >= 5
WITH p1, p2, COUNT(c) as shared_conditions
MERGE (p1)-[r:POTENTIAL_REFERRAL]-(p2)
SET r.shared_conditions = shared_conditions,
    r.discovered_at = datetime(),
    r.confidence = 0.7;

// Pattern 2: Drugs with same indication and potential interactions
MATCH (d1:Drug)-[:TREATS]->(c:Condition)<-[:TREATS]-(d2:Drug)
WHERE d1.id < d2.id
  AND NOT (d1)-[:INTERACTS_WITH]-(d2)
WITH d1, d2, COUNT(c) as shared_indications
CREATE (d1)-[r:CO_INDICATED {
  shared_indications: shared_indications,
  discovered_at: datetime(),
  confidence: 0.6
}]-(d2);

// Pattern 3: Provider networks (direct collaboration)
MATCH (p1:Provider)-[:PUBLISHED_WITH]->(pub:Publication)<-[:PUBLISHED_WITH]-(p2:Provider)
WHERE p1.id < p2.id
  AND pub.date >= date(datetime()) - duration('P5Y') // Last 5 years
WITH p1, p2, COUNT(pub) as collaboration_count
MERGE (p1)-[r:COLLABORATES_WITH]-(p2)
SET r.collaboration_count = collaboration_count,
    r.strength = CASE
      WHEN collaboration_count >= 10 THEN 'STRONG'
      WHEN collaboration_count >= 5 THEN 'MEDIUM'
      ELSE 'WEAK'
    END,
    r.updated_at = datetime();

// Pattern 4: Build drug indication inference (PubMed → clinical use)
MATCH (d:Drug)-[:APPEARS_IN]->(p:PubMedCitation)-[:MENTIONS_CONDITION]->(c:Condition)
WHERE p.impact_factor >= 3.0 // High-impact journals
WITH d, c, COUNT(p) as evidence_count, AVG(p.year) as avg_year
WHERE evidence_count >= 3 // Minimum evidence threshold
CREATE (d)-[r:INFERRED_TREATS {
  evidence_count: evidence_count,
  avg_year: avg_year,
  confidence: min(0.95, 0.5 + evidence_count * 0.1),
  discovered_at: datetime()
}]->(c);

// Pattern 5: Centrality scoring (which providers are most connected?)
CALL apoc.algo.pageRank.stream('Provider', 'COLLEAGUES_WITH|COLLABORATES_WITH|POTENTIAL_REFERRAL')
YIELD node, score
SET node.network_centrality = score;

// Pattern 6: Emerging clusters (new communities of practice)
CALL algo.labelPropagation.stream('Provider', 'COLLEAGUES_WITH')
YIELD nodeId, label
RETURN nodeId, label as community;
```

### Graph Density Metrics

Track how the graph grows and becomes more connected:

```sql
-- Neo4j Cypher queries for graph health
MATCH (n:Provider) RETURN COUNT(n) as provider_count;
MATCH (n:Drug) RETURN COUNT(n) as drug_count;
MATCH (n:Condition) RETURN COUNT(n) as condition_count;
MATCH ()-[r]->() RETURN COUNT(r) as total_relationships;

-- Graph density = relationships / (nodes * nodes - nodes)
WITH 2847392 as providers, 103844 as drugs, 14402 as conditions,
     SUM(r) as relationships
MATCH ()-[r]->()
LET total_nodes = providers + drugs + conditions
LET max_relationships = total_nodes * (total_nodes - 1)
RETURN relationships / max_relationships as graph_density;

-- Average path length (smaller = denser)
MATCH (n:Provider) AS source
MATCH (m:Provider) AS target
WHERE source.id < target.id
WITH source, target
CALL apoc.algo.shortestPath(source, target, 'COLLEAGUES_WITH|COLLABORATES_WITH')
YIELD path
RETURN AVG(LENGTH(path)) as avg_shortest_path;

-- Clustering coefficient (local density)
CALL apoc.algo.clusteringCoefficient.stream('Provider', 'COLLEAGUES_WITH')
YIELD nodeId, coefficient
RETURN AVG(coefficient) as avg_clustering_coefficient;
```

### Knowledge Graph Growth Trajectory

```
Month 1:  ~50M edges (basic relationships from source data)
Month 3:  ~150M edges (discovered + enriched)
Month 6:  ~500M edges (dense network + inference)
Month 12: ~2B edges (emergent patterns, predictions possible)
Year 2:   ~5B edges (compounding relationships, moat is insurmountable)
```

---

## MONITORING & ALERTING

The heartbeat system must be observable. Operators need real-time visibility into data freshness, conflicts, and system health.

### Metrics Dashboard

```typescript
interface HeartbeatMetrics {
  // Ingestion metrics
  ingestion_runs: number; // Total runs in period
  ingestion_success_rate: number; // % successful runs
  ingestion_records_processed: number; // Total records
  ingestion_avg_latency_seconds: number; // Time per run
  
  // Data freshness
  entities_fully_verified_pct: number; // % at 90+ freshness
  entities_verified_7d_pct: number;
  entities_verified_30d_pct: number;
  entities_stale_pct: number; // % at 0-24 freshness
  
  // Verification status
  providers_fully_verified: number;
  providers_partially_verified: number;
  providers_unverified: number;
  providers_conflict_detected: number;
  providers_excluded: number;
  
  // Knowledge graph
  total_entities: number;
  total_relationships: number;
  graph_density: number; // relationships / max possible
  new_entities_discovered: number; // This period
  new_relationships_discovered: number; // This period
  
  // Quality & Errors
  data_quality_score: number; // Weighted avg of all checks
  validation_errors: number;
  conflict_alerts_count: number;
  system_errors: number;
  
  // AI & SEO
  entity_pages_indexed: number; // By search engines
  entity_pages_cited_by_ai: number; // In AI responses
  average_ai_citation_impact: number; // How often cited
}
```

### Alert Types and Severity

```typescript
type AlertType =
  // CRITICAL
  | 'PROVIDER_EXCLUDED_OIG'
  | 'LICENSE_REVOKED'
  | 'HEARTBEAT_FAILURE'
  | 'DATA_INTEGRITY_FAILURE'
  
  // HIGH
  | 'VERIFICATION_CONFLICT'
  | 'NEW_SERIOUS_ADVERSE_EVENT'
  | 'LICENSE_STATUS_CHANGE'
  | 'CREDENTIAL_EXPIRING'
  | 'STATE_BOARD_CHECK_FAILED'
  
  // MEDIUM
  | 'DATA_STALE'
  | 'HEARTBEAT_RETRY'
  | 'SOURCE_COMPLETENESS_LOW'
  | 'LICENSE_EXPIRATION_APPROACHING'
  
  // LOW
  | 'SOURCE_METADATA_CHANGED'
  | 'MINOR_DATA_INCONSISTENCY'

interface Alert {
  id: string;
  type: AlertType;
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  timestamp: Date;
  message: string;
  metadata: Record<string, any>;
  
  // Notification channels
  channels: ('SLACK' | 'EMAIL' | 'IN_APP' | 'WEBHOOK')[];
  
  // Resolution
  acknowledged: boolean;
  resolved: boolean;
  resolution_notes?: string;
}
```

### Example Dashboard Query

```sql
-- Real-time heartbeat health dashboard
SELECT
  TO_CHAR(DATE_TRUNC('hour', timestamp), 'YYYY-MM-DD HH24:00') as hour,
  
  -- Ingestion health
  COUNT(*) FILTER (WHERE status = 'SUCCESS') as successful_runs,
  COUNT(*) FILTER (WHERE status = 'FAILURE') as failed_runs,
  ROUND(100 * COUNT(*) FILTER (WHERE status = 'SUCCESS')::numeric / 
        NULLIF(COUNT(*), 0), 2) as success_rate_pct,
  
  -- Data freshness
  COUNT(*) FILTER (WHERE freshness_score >= 90) as fully_verified_entities,
  COUNT(*) FILTER (WHERE freshness_score < 25) as stale_entities,
  
  -- Alerts
  COUNT(*) FILTER (WHERE alert_severity = 'CRITICAL') as critical_alerts,
  COUNT(*) FILTER (WHERE alert_severity = 'HIGH') as high_alerts,
  
  -- Performance
  AVG(EXTRACT(EPOCH FROM duration_ms)) as avg_run_time_seconds,
  MAX(EXTRACT(EPOCH FROM duration_ms)) as max_run_time_seconds
  
FROM heartbeat_runs
WHERE timestamp >= NOW() - INTERVAL '24 hours'
GROUP BY 1
ORDER BY 1 DESC;
```

### Slack Integration Example

```typescript
async function notifySlackCriticalAlert(alert: Alert) {
  const slackMessage = {
    channel: '#hkg-alerts-critical',
    blocks: [
      {
        type: 'header',
        text: {
          type: 'plain_text',
          text: `🚨 ${alert.severity}: ${alert.type}`,
        },
      },
      {
        type: 'section',
        text: {
          type: 'mrkdwn',
          text: `*${alert.message}*\n\nTime: <!date^${alert.timestamp.getTime() / 1000}^{date_num} {time_secs}|${alert.timestamp}>`,
        },
      },
      {
        type: 'section',
        fields: [
          {
            type: 'mrkdwn',
            text: `*Entity ID*\n${alert.metadata.entity_id || 'N/A'}`,
          },
          {
            type: 'mrkdwn',
            text: `*Source*\n${alert.metadata.source || 'System'}`,
          },
        ],
      },
      {
        type: 'actions',
        elements: [
          {
            type: 'button',
            text: {
              type: 'plain_text',
              text: 'View Details',
            },
            url: `https://hkg.health/admin/alerts/${alert.id}`,
            style: 'danger',
          },
          {
            type: 'button',
            text: {
              type: 'plain_text',
              text: 'Acknowledge',
            },
            action_id: `ack-${alert.id}`,
          },
        ],
      },
    ],
  };
  
  await slack.chat.postMessage(slackMessage);
}
```

---

## IMPLEMENTATION PLAN

### Phase 1: Foundation (Weeks 1-2)

**Goal**: Basic heartbeat infrastructure + core adapters

Tasks:
- [ ] Build HeartbeatRunner scheduler (cron-based)
- [ ] Implement SupabaseLoader and PostgreSQL schema
- [ ] Build NPI adapter (incremental API + dissemination file)
- [ ] Build OIG LEIE adapter
- [ ] Implement freshness scoring engine
- [ ] Build AlertManager (Slack integration)
- [ ] Set up monitoring/logging infrastructure

Output:
- Daily NPI updates with freshness scores
- Weekly OIG LEIE checks with exclusion alerts
- Basic dashboard showing ingestion metrics

### Phase 2: Medical Data (Weeks 3-4)

**Goal**: Drug and code data pipelines

Tasks:
- [ ] Implement NDC adapter (FDA openFDA API)
- [ ] Implement DailyMed adapter (drug labels)
- [ ] Implement RxNorm adapter (monthly releases)
- [ ] Implement medical code adapters (CPT, ICD-10, HCPCS)
- [ ] Build TransformPipeline for normalization/validation
- [ ] Implement Neo4jLoader for graph ingestion

Output:
- Daily drug data updates with freshness scoring
- Quarterly code set updates
- Graph nodes for drugs and conditions

### Phase 3: Evidence & Clinical Data (Weeks 5-6)

**Goal**: PubMed, clinical trials, and evidence linking

Tasks:
- [ ] Implement PubMed adapter (E-utilities API)
- [ ] Implement ClinicalTrials.gov adapter
- [ ] Build evidence extraction (condition-drug linking)
- [ ] Implement FAERS adapter (adverse events)
- [ ] Build relationship discovery engine (Neo4j)

Output:
- Daily PubMed ingestion with condition linking
- Automated evidence synthesis for drugs
- Adverse event tracking and alerts

### Phase 4: Verification & Quality (Weeks 7-8)

**Goal**: 3-point verification + data quality

Tasks:
- [ ] Implement 3-point verification engine
- [ ] Build state board adapter framework
- [ ] Implement conflict detection & alerts
- [ ] Build data quality metrics & dashboard
- [ ] Implement llms.txt generation
- [ ] Build sitemap generator for SEO

Output:
- Weekly cross-validation with conflict detection
- Provider verification status tracking
- llms.txt for AI discoverability
- XML sitemaps for search engines

### Phase 5: Scale & Optimization (Weeks 9+)

**Goal**: Production-ready, optimized system

Tasks:
- [ ] Optimize query performance (database indexing, caching)
- [ ] Implement retry logic and error handling
- [ ] Scale adapters to handle all 30+ sources
- [ ] Add state-specific board adapters (52 states)
- [ ] Implement graph partitioning for Neo4j scale
- [ ] Stress test: 10M entity updates in 4 hours

Output:
- Fully automated heartbeat processing 30+ sources daily
- Sub-4-hour completion for daily heartbeat cycle
- < 1% error rate across all adapters
- 99.9% data integrity maintained

---

## THE COMPOUND EFFECT

This is not just a data pipeline. This is a **compounding machine** that builds an insurmountable moat.

### Day 1: Raw Data Parity
We ingest the same public data every competitor has access to:
- NPI Registry: 2.8M providers
- FDA drug data: 100K+ drugs
- ICD-10: 14K conditions

Competitive advantage: **None**. We're tied with everyone else.

### Month 1: Cross-Validated Data
We verify data across 3+ sources, detect conflicts, score freshness.

*What changes*:
- 94%+ of providers are fully or partially verified
- Conflicts surface (e.g., NPI says active, state board says suspended)
- Freshness scores guide users to current data
- AI systems can trust HKG citations more

Competitive advantage: **Moderate**. Trusted data > raw data.

### Month 3: Enriched Knowledge Graph
Relationship discovery finds 150M+ edges in the graph.

*What changes*:
- Providers are connected to colleagues, collaborators
- Drugs are linked to indications with evidence levels
- Clinical trials show which conditions are being studied
- Queries become powerful: "Find specialists treating [condition] in [zip]"

Competitive advantage: **Strong**. Density of knowledge matters.

### Month 6: Emerging Intelligence
Graph density enables inference and prediction.

*What changes*:
- "This provider's colleagues commonly treat [condition]" (referral networks)
- "These drugs are co-indicated and have no known interactions" (safety)
- "New clinical trial started for [condition]" (emerging treatments)
- Graph becomes a search/recommendation engine

Competitive advantage: **Very Strong**. Inference can't be replicated.

### Year 1: History & Trends
A year of historical data reveals patterns competitors can't see.

*What changes*:
- Seasonal trends in diagnoses (flu season, allergy season)
- Provider specialization evolution (switching from surgery to admin)
- Drug approval timelines and adoption curves
- What medications follow other medications (treatment pathways)

Competitive advantage: **Extreme**. Time-series data is irreplaceable.

### Year 2: The Moat Is Complete
HKG becomes the de facto source of truth.

*Why*:
- No competitor can replicate a year+ of continuous verification
- Every day HKG runs, the gap widens
- AI systems learn to cite HKG because it's the best source
- Doctors learn to trust HKG because it's consistently accurate
- Network effects: more doctors use it → more data flows in → stronger graph

**This is how platforms become irreplaceable.**

### Quantifying the Moat

| Metric | Month 1 | Month 6 | Year 1 | Year 2 |
|--------|---------|---------|--------|---------|
| Unique Entities | 3.0M | 3.5M | 4.2M | 5.1M |
| Relationships | 50M | 500M | 2B | 5B |
| Graph Density | 0.001% | 0.005% | 0.05% | 0.15% |
| Fully Verified Providers | 94% | 97% | 99%+ | 99%+ |
| AI Citations/Day | 0 | 100 | 10K | 100K+ |
| Avg Query Response Time | 2s | 500ms | 100ms | <50ms |
| User Trust Score | 6/10 | 8/10 | 9.2/10 | 9.8/10 |

### The Network Effect

```
More Providers Join HKG
        ↓
Better Provider Matching Data
        ↓
More Accurate Referral Networks
        ↓
More Value for Patients
        ↓
More Providers Join HKG
        ↓ (loop repeats, accelerating)
```

The platform doesn't just get better data — it gets exponentially more **useful** data.

---

## TECHNICAL APPENDIX

### A. Database Schema (Supabase/PostgreSQL)

```sql
-- Core entity tables
CREATE TABLE entities (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  entity_type VARCHAR(50) NOT NULL, -- 'PROVIDER', 'DRUG', 'CONDITION', etc.
  external_id VARCHAR(255) UNIQUE, -- NPI, NDC, ICD-10, etc.
  name VARCHAR(500) NOT NULL,
  
  -- Freshness tracking
  freshness_verified_at TIMESTAMP NOT NULL DEFAULT NOW(),
  freshness_score INT CHECK (freshness_score >= 0 AND freshness_score <= 100),
  
  -- Quality metrics
  data_completeness INT,
  importance_score INT,
  
  -- Source tracking
  data_sources TEXT[] DEFAULT ARRAY[]::TEXT[],
  
  -- Verification
  verification_status VARCHAR(50), -- UNVERIFIED, PARTIALLY_VERIFIED, FULLY_VERIFIED, CONFLICT_DETECTED, EXCLUDED
  overall_trust INT, -- 0-100
  
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  
  INDEX idx_entity_type (entity_type),
  INDEX idx_freshness_score (freshness_score),
  INDEX idx_verification_status (verification_status)
);

CREATE TABLE providers (
  id UUID PRIMARY KEY REFERENCES entities(id),
  npi_id VARCHAR(10) UNIQUE NOT NULL,
  first_name VARCHAR(255),
  last_name VARCHAR(255),
  middle_name VARCHAR(255),
  credential VARCHAR(50),
  
  -- Specialization
  primary_taxonomy_code VARCHAR(20),
  secondary_taxonomy_codes TEXT[],
  
  -- Licensing
  state_license VARCHAR(100),
  license_status VARCHAR(50),
  license_expiration_date DATE,
  
  -- Contact
  phone VARCHAR(20),
  email VARCHAR(255),
  website_url VARCHAR(500),
  
  -- Location
  facility_name VARCHAR(500),
  address_line_1 VARCHAR(500),
  address_line_2 VARCHAR(500),
  city VARCHAR(100),
  state VARCHAR(2),
  zip_code VARCHAR(10),
  latitude DECIMAL(10, 8),
  longitude DECIMAL(11, 8),
  
  -- Activity metrics
  patient_volume_estimate INT,
  telehealth_capable BOOLEAN,
  
  -- Credentials
  board_certified BOOLEAN,
  board_certifications TEXT[],
  
  -- Exclusion tracking
  oig_excluded BOOLEAN DEFAULT FALSE,
  oig_exclusion_date DATE,
  sam_excluded BOOLEAN DEFAULT FALSE,
  
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  
  INDEX idx_npi_id (npi_id),
  INDEX idx_state (state),
  INDEX idx_specialty (primary_taxonomy_code),
  INDEX idx_location (city, state, zip_code),
  INDEX idx_excluded (oig_excluded, sam_excluded)
);

CREATE TABLE provider_licenses (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  provider_id UUID NOT NULL REFERENCES providers(id),
  state VARCHAR(2) NOT NULL,
  license_number VARCHAR(100) NOT NULL,
  status VARCHAR(50), -- ACTIVE, SUSPENDED, REVOKED, EXPIRED, RENEWAL_PENDING
  specialties TEXT[],
  expiration_date DATE,
  issue_date DATE,
  verified_at TIMESTAMP,
  source VARCHAR(100), -- STATE_BOARD, NPI, etc.
  
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  
  UNIQUE(provider_id, state),
  INDEX idx_status (status),
  INDEX idx_expiration (expiration_date)
);

CREATE TABLE drugs (
  id UUID PRIMARY KEY REFERENCES entities(id),
  ndc_code VARCHAR(11) UNIQUE NOT NULL,
  name VARCHAR(500) NOT NULL,
  generic_name VARCHAR(500),
  brand_name VARCHAR(500),
  
  -- Classification
  therapeutic_class VARCHAR(255),
  pharmacological_class VARCHAR(255),
  rxnorm_cui VARCHAR(10), -- Maps to RxNorm
  
  -- Safety
  dea_schedule INT, -- I, II, III, IV, V (or NULL for non-controlled)
  fda_status VARCHAR(50), -- APPROVED, WITHDRAWN, UNAPPROVED, etc.
  black_box_warning BOOLEAN DEFAULT FALSE,
  
  -- Indications
  primary_indication TEXT,
  indications TEXT[],
  
created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  
  INDEX idx_ndc_code (ndc_code),
  INDEX idx_name (name),
  INDEX idx_therapeutic_class (therapeutic_class)
);

CREATE TABLE drug_interactions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  drug_1_id UUID NOT NULL REFERENCES drugs(id),
  drug_2_id UUID NOT NULL REFERENCES drugs(id),
  
  severity VARCHAR(50), -- MAJOR, MODERATE, MINOR
  mechanism TEXT,
  clinical_significance TEXT,
  management TEXT,
  
  source VARCHAR(100), -- FDA, DrugBank, etc.
  evidence_level VARCHAR(20), -- A, B, C (strength of evidence)
  
  created_at TIMESTAMP DEFAULT NOW(),
  
  UNIQUE(drug_1_id, drug_2_id),
  INDEX idx_severity (severity)
);

CREATE TABLE adverse_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  drug_id UUID REFERENCES drugs(id),
  adverse_reaction VARCHAR(500) NOT NULL,
  severity VARCHAR(50), -- MILD, MODERATE, SEVERE, SERIOUS
  outcome VARCHAR(100), -- RECOVERED, RECOVERED_WITH_SEQUELAE, NOT_RECOVERED, FATAL, UNKNOWN
  
  case_count INT DEFAULT 1,
  reported_date DATE,
  
  source VARCHAR(100), -- FAERS, DailyMed, PubMed, etc.
  source_reference_id VARCHAR(255),
  
  created_at TIMESTAMP DEFAULT NOW(),
  
  INDEX idx_drug_id (drug_id),
  INDEX idx_severity (severity),
  INDEX idx_reported_date (reported_date)
);

CREATE TABLE heartbeat_runs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  task_id VARCHAR(100) NOT NULL,
  task_name VARCHAR(255),
  status VARCHAR(50), -- SUCCESS, FAILURE, TIMEOUT, PARTIAL
  
  start_time TIMESTAMP NOT NULL,
  end_time TIMESTAMP,
  duration_ms INT,
  
  records_processed INT DEFAULT 0,
  records_inserted INT DEFAULT 0,
  records_updated INT DEFAULT 0,
  records_failed INT DEFAULT 0,
  
  error_message TEXT,
  error_stack_trace TEXT,
  
  metrics JSONB, -- Arbitrary metrics for this run
  
  INDEX idx_task_id (task_id),
  INDEX idx_status (status),
  INDEX idx_start_time (start_time)
);

CREATE TABLE alerts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  alert_type VARCHAR(100) NOT NULL,
  severity VARCHAR(50), -- CRITICAL, HIGH, MEDIUM, LOW
  
  title VARCHAR(500),
  message TEXT,
  
  entity_type VARCHAR(50),
  entity_id UUID,
  
  metadata JSONB,
  
  created_at TIMESTAMP DEFAULT NOW(),
  acknowledged_at TIMESTAMP,
  resolved_at TIMESTAMP,
  resolution_notes TEXT,
  
  INDEX idx_severity (severity),
  INDEX idx_entity_id (entity_id),
  INDEX idx_created_at (created_at)
);

-- Materialized view for fast freshness queries
CREATE MATERIALIZED VIEW entity_freshness_tiers AS
SELECT
  id,
  entity_type,
  freshness_score,
  CASE
    WHEN freshness_score >= 90 THEN 'VERIFIED_24H'
    WHEN freshness_score >= 75 THEN 'VERIFIED_7D'
    WHEN freshness_score >= 50 THEN 'VERIFIED_30D'
    WHEN freshness_score >= 25 THEN 'VERIFIED_90D'
    ELSE 'STALE'
  END as freshness_tier
FROM entities;

CREATE INDEX idx_freshness_tier ON entity_freshness_tiers(freshness_tier);
```

### B. Neo4j Schema

```cypher
-- Provider node
CREATE CONSTRAINT provider_id IF NOT EXISTS
  FOR (p:Provider) REQUIRE p.id IS UNIQUE;

-- Drug node
CREATE CONSTRAINT drug_id IF NOT EXISTS
  FOR (d:Drug) REQUIRE d.id IS UNIQUE;

-- Condition node
CREATE CONSTRAINT condition_id IF NOT EXISTS
  FOR (c:Condition) REQUIRE c.icd10_code IS UNIQUE;

-- Relationship types (defined implicitly through usage)
// PRACTICES_AT, TREATS, COLLABORATES_WITH, INTERACTS_WITH, CITES_EVIDENCE, etc.

// Index common queries
CREATE INDEX provider_name IF NOT EXISTS FOR (p:Provider) ON (p.name);
CREATE INDEX drug_name IF NOT EXISTS FOR (d:Drug) ON (d.name);
CREATE INDEX condition_name IF NOT EXISTS FOR (c:Condition) ON (c.name);
```

### C. Environment Variables & Configuration

```bash
# Supabase
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=your-api-key
SUPABASE_DB_HOST=localhost
SUPABASE_DB_PORT=5432
SUPABASE_DB_NAME=postgres
SUPABASE_DB_USER=postgres
SUPABASE_DB_PASSWORD=xxx

# Neo4j
NEO4J_URL=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=xxx

# APIs
NPI_API_BASE_URL=https://npiregistry.cms.hhs.gov/api
OPENFDA_API_BASE_URL=https://api.fda.gov
PUBMED_API_BASE_URL=https://eutils.ncbi.nlm.nih.gov/entrez/eutils
CLINICALTRIALS_API_BASE_URL=https://clinicaltrials.gov/api/v2

# Slack
SLACK_WEBHOOK_URL=https://hooks.slack.com/...
SLACK_BOT_TOKEN=xoxb-...

# Monitoring
SENTRY_DSN=https://...
PROMETHEUS_PUSH_GATEWAY=http://localhost:9091

# Feature flags
ENABLE_3_POINT_VERIFICATION=true
ENABLE_GRAPH_ENRICHMENT=true
ENABLE_AI_CITATION_TRACKING=true
```

### D. Deployment Architecture

```
┌─────────────────────────────────────────────────────┐
│           Kubernetes Cluster (GKE/EKS)              │
├─────────────────────────────────────────────────────┤
│                                                       │
│  ┌──────────────┐  ┌──────────────┐                │
│  │ Scheduler Pod│  │ Worker Pods   │  (Autoscale)  │
│  │ (CronJob)    │  │ (Kafka/Queue) │               │
│  └──────────────┘  └──────────────┘                │
│         │                   │                        │
│         └───────────┬───────┘                        │
│                     │                                │
│              ┌──────▼──────┐                        │
│              │  Adapter    │                        │
│              │  Processes  │                        │
│              └──────┬──────┘                        │
│                     │                                │
│         ┌───────────┼───────────┐                   │
│         ▼           ▼           ▼                   │
│  ┌──────────────────────────────────────────────┐  │
│  │ Storage Layer                                 │  │
│  │ - Supabase (PostgreSQL)                      │  │
│  │ - Neo4j (Graph DB)                           │  │
│  │ - GCS (Static files, backups)                │  │
│  └──────────────────────────────────────────────┘  │
│                                                     │
│  Monitoring:                                        │
│  - Prometheus (metrics)                            │
│  - Loki (logs)                                     │
│  - Grafana (dashboards)                           │
│  - Slack (alerts)                                 │
└─────────────────────────────────────────────────────┘
```

### E. Error Handling & Retry Logic

```typescript
interface RetryConfig {
  maxAttempts: number;
  initialBackoffMs: number;
  maxBackoffMs: number;
  backoffMultiplier: number;
  jitterFactor: number; // Add randomness to avoid thundering herd
}

const defaultRetryConfig: RetryConfig = {
  maxAttempts: 5,
  initialBackoffMs: 1000,
  maxBackoffMs: 60000,
  backoffMultiplier: 2,
  jitterFactor: 0.1,
};

async function executeWithRetry<T>(
  fn: () => Promise<T>,
  config: RetryConfig = defaultRetryConfig
): Promise<T> {
  let lastError: Error | null = null;
  
  for (let attempt = 1; attempt <= config.maxAttempts; attempt++) {
    try {
      return await fn();
    } catch (error) {
      lastError = error as Error;
      
      if (attempt < config.maxAttempts) {
        // Calculate backoff with jitter
        const baseBackoff = Math.min(
          config.initialBackoffMs * Math.pow(config.backoffMultiplier, attempt - 1),
          config.maxBackoffMs
        );
        const jitter = baseBackoff * (Math.random() - 0.5) * 2 * config.jitterFactor;
        const backoffMs = Math.max(0, baseBackoff + jitter);
        
        logger.warn(
          `Attempt ${attempt} failed, retrying in ${backoffMs}ms:`,
          error
        );
        
        await sleep(backoffMs);
      }
    }
  }
  
  throw new Error(
    `Failed after ${config.maxAttempts} attempts. Last error: ${lastError?.message}`
  );
}
```

---

## CONCLUSION

The RSI Heartbeat System is the **metabolism of the Healthcare Knowledge Garden**. It's not a static database — it's a living, growing organism that becomes more intelligent and valuable every single day.

This system creates an insurmountable moat because:

1. **Time is irreplaceable**: No competitor can replicate a year of continuous verification overnight
2. **Density is power**: A graph with billions of relationships answers questions other systems can't
3. **Trust compounds**: AI systems cite HKG because it's the best source; users trust it because it's always fresh
4. **Network effects multiply**: More doctors use it → more data flows in → stronger graph → more value
5. **Automation wins**: We improve without manual effort; competitors must hire more people

**The platform gets smarter every day it runs.**

By building the heartbeat right from day one — modular, observable, scalable — HKG will bootstrap into a position of unquestionable dominance in healthcare data and intelligence.

This is not just an engineering document. It's a **competitive strategy** encoded in code.

---

**Version**: 1.0  
**Last Updated**: 2026-04-09  
**Status**: Ready for implementation  
**Owner**: Chilly (Charles Dahlgren), XRWorkers
