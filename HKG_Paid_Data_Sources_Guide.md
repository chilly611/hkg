# HKG Paid Data Sources Guide

**Version**: 1.0  
**Date**: April 9, 2026  
**Author**: Chilly (Charles Dahlgren), XRWorkers  
**Status**: Active — Action items flagged for immediate execution

---

## EXECUTIVE SUMMARY

The Healthcare Knowledge Garden has mapped 30+ data sources. Most are free (NPI, ICD-10, OIG, etc.), but critical sources require paid subscriptions. This guide prioritizes which to buy, in what order, with step-by-step signup instructions.

**Year 1 Budget Estimate: $25–60K** across all paid sources. ROI justification: Each data source unlocks a core MLP feature. The Admin Lane's credentialing engine cannot compete without CAQH; the billing code search is unusable without AMA CPT descriptions; the Doctor Lane lacks nationwide verification without FSMB.

---

## TIER 1: BUY NOW (Highest ROI for the MLP)

### 1. CAQH ProView API Access

#### What It Gives You
Access to **4.8M+ provider credentialing profiles** — the most comprehensive source in healthcare. This includes:
- Full demographics (name, DOB, SSN, address history)
- Education (medical school, residency, fellowship)
- Licensure status (state, license number, expiration)
- Board certifications (specialty, board name, dates)
- Malpractice history (paid claims, amount, specialty)
- DEA registration (controlled substance license)
- Practice locations and tax ID information
- Insurance participation and payer networks
- Credentialing questionnaire responses

This is THE credentialing data hub that every hospital system and insurance company uses.

#### Why Buy Now
The **Admin Lane (credentialing engine)** is the MLP's primary revenue source. Every hospital admin and credentialing specialist needs to verify providers at scale. CAQH data is what:
- Insurance companies use for network adequacy audits
- Hospitals use for credentialing committees
- Payers use for fraud/abuse checks
- State medical boards reference for cross-verification

Having API access makes your credentialing funnel **10x faster** than competitors scraping state boards one by one. You go from "maybe we can check 50 providers per day" to "1,000+ per minute."

#### Cost
**Custom enterprise pricing** — contact CAQH sales. Typical range:
- **Pilot/Sandbox**: $0–2K/year (limited query volume)
- **Mid-market platform**: $10–25K/year (10K–100K queries/month)
- **Enterprise integration**: $25–75K+/year (unlimited/high volume)

Billing models vary:
- Per-provider lookup
- Per-query
- Tiered monthly subscription based on volume
- Revenue-sharing arrangements (CAQH takes % of your billing if you're a reseller)

#### Step-by-Step Signup

**Step 1: Request Demo**
1. Navigate to https://www.caqh.org/solutions/provider-data/credentialing-suite
2. Click **"Contact Us"** or **"Request a Demo"**
3. You'll land on a form

**Step 2: Fill Demo Request Form**
Provide:
- Company name: **XRWorkers / Healthcare Knowledge Garden**
- Contact name: **Charles Dahlgren (Chilly)**
- Use case description (copy template below)
- Expected query volume: **Start with "10K queries/month, scaling to 100K+"**
- Timeline: **"Launching credentialing platform April 2026, need API access within 3 weeks"**

**Template Use Case Description**:
> Healthcare Knowledge Garden is an AI-native credentialing platform for hospital systems and health plans. We aggregate provider data from public sources (NPI, state boards, ABMS, DEA, NPDB) and need CAQH ProView API to unify and verify this data at scale. Our Admin Lane provides real-time credentialing verification, malpractice history, and board certification checks. We expect to onboard 20+ hospital systems in Year 1, with each system credentialing 100–500 providers. We see CAQH as our primary source of truth for baseline provider demographics and history.

**Step 3: Sales Rep Assignment**
- CAQH will contact you within 1–2 business days
- Mention you're building a **multi-sided platform** (they care about volume and sustainability)
- Request a **pilot/sandbox account** first (lower commitment, 30–90 days)
- Negotiate: "We'll drive provider adoption and data quality improvements"

**Step 4: Contract & API Credentials**
Once contract is signed:
- You'll receive **API credentials** (username/password + optional TLS certificate)
- CAQH will provide sandbox API endpoint (test environment)
- Production endpoint activated after 2–3 weeks of testing

**Step 5: API Integration**
- Documentation: https://docs.mulesoft.com/caqh-connector/latest/
- Protocol: REST API (XML or JSON responses)
- Authentication: OAuth 2.0 or API key (depends on your agreement)
- Response includes: Full provider profile, licensure, education, malpractice, DEA, practice locations
- Typical response time: 100–500ms per query

**Step 6: Integration Checklist**
- [ ] Sandbox endpoint tested with 10–50 test queries
- [ ] Logging configured (audit trail for HIPAA/compliance)
- [ ] Error handling implemented (rate limits, timeouts, retries)
- [ ] Provider deduplication logic (match CAQH IDs to your internal DB)
- [ ] Data refresh schedule (daily? weekly? real-time?)

#### Expected Timeline
**2–4 weeks** from first contact to production API access:
- Day 1–2: Demo request submitted
- Day 3–7: Sales rep demo + pricing discussion
- Day 8–14: Contract negotiation
- Day 14–21: Sandbox testing
- Day 21–28: Production activation

#### Negotiation Tips
1. **Pilot first**: Ask for a 60-day pilot with 10K queries at no cost (they often grant this). Prove volume.
2. **Volume projection**: Tell them you plan to drive provider adoption across hospital systems (they love this — more providers = more value for CAQH).
3. **Revenue model**: If HKG becomes a credentialing platform reseller, mention that. CAQH may offer rev-share or tiered pricing.
4. **Ask for early access**: Frame it as "We're building the next-gen credentialing layer; having CAQH as your representative in the market is mutual benefit."

---

### 2. AMA CPT License

#### What It Gives You
Legal right to display **CPT code descriptions** alongside code numbers. Without this license:
- ❌ You can only show: `99213`
- ✅ With license, you show: `99213 – Office visit, established patient, low complexity`

CPT codes are the billing language of healthcare. Every diagnosis has a code; every procedure has a code. Your Admin Lane's billing code engine is useless without descriptions.

#### Why Buy Now
Medical billing is core to the Admin Lane. Every hospital admin, biller, and credentialer needs to look up and cross-reference CPT codes daily. Use cases:
- **Billing verification**: "Is this procedure code valid for this diagnosis?"
- **Insurance contract compliance**: "What does our payer reimburse for this code?"
- **Fraud detection**: "This surgeon is billing 99215 (high complexity) for 95% of visits — that's a red flag."
- **Prior authorization**: "What's the exact description for this CPT code we're requesting auth for?"

Without CPT descriptions, your code search tool is essentially useless. Competitors will have them; you won't.

#### Cost
Varies significantly by use case. Typical pricing:

| License Type | Annual Cost | Use Case |
|---|---|---|
| **Digital Products** | $500–5,000 | SaaS platforms, internal tools, APIs |
| **Software Integration** | $1,000–10,000 | Embedded in EHRs, billing software |
| **Healthcare Provider** | $1,000–3,000 | Hospital or health system internal use |
| **Health Plan** | $2,000–10,000 | Payer/insurance company |
| **Enterprise** | $10,000+ | Large-scale licensing |

**For HKG: Expect $1,000–3,000/year** as a "Digital Products" platform license.

#### Step-by-Step Signup

**Step 1: Review Licensing Requirements**
1. Visit https://www.ama-assn.org/practice-management/cpt/ama-cpt-licensing-overview
2. Read the FAQ: https://www.ama-assn.org/practice-management/cpt/cpt-licensing-frequently-asked-questions-faqs
3. Key takeaway: You **cannot display CPT descriptions without a license**. AMA enforces this strictly.

**Step 2: Determine Your License Type**
For HKG, the right category is **"Digital Products"** or **"Software Integration"**:
- Scope: SaaS platform with Admin Lane tools (billing code search, credentialing verification)
- Distribution: Cloud-based, multi-tenant (hospital customers access via login)
- Users: Hospital admins, billers, credentialing specialists

**Step 3: Medicare/CMS License Consideration**
If you're using CPT codes for Medicare billing or reporting:
- Check CMS license requirement: https://www.cms.gov/license/ama
- Most platforms need **both** AMA CPT license AND CMS license
- CMS license is free but has compliance requirements

**Step 4: Contact AMA Licensing**
Email: **amalicensing@ama-assn.org**

**Subject Line**: `CPT License Request for Healthcare Knowledge Garden Platform`

**Email Template**:
```
Dear AMA Licensing Team,

We are requesting a CPT license for our healthcare credentialing and 
billing platform, Healthcare Knowledge Garden (HKG).

Company: XRWorkers / Healthcare Knowledge Garden
Primary Contact: Charles Dahlgren (Chilly)
Use Case: Digital SaaS platform for hospital credentialing, billing 
code search, and provider verification

Product Description:
Healthcare Knowledge Garden is an AI-native credentialing platform 
that aggregates provider data and medical billing codes. Our Admin Lane 
includes a billing code search engine that helps hospital admins verify 
procedure codes, check insurance contracts, and detect billing anomalies.

We need CPT code descriptions displayed alongside code numbers in:
- Billing code search interface
- Provider credentialing workflows
- Prior authorization tools

Expected User Base:
- Initial: 10 hospital systems (500–1,000 users)
- Year 1: 20+ systems (5,000+ users)

Distribution: Cloud-based SaaS (no downloads, web-only access)

We would like a quote for "Digital Products" or "Software Integration" 
licensing and would appreciate information on:
1. Pricing for our expected user volume
2. License duration (annual? perpetual?)
3. Data update frequency (CPT codes change annually)
4. Integration requirements (API, flat files, other?)
5. CMS licensing requirements if we support Medicare billing

Please advise next steps.

Best regards,
Charles Dahlgren
Founder, XRWorkers
Healthcare Knowledge Garden
[phone] [email]
```

**Step 5: Contract & Data Delivery**
Once approved:
- AMA will send a **license agreement** with specific restrictions (e.g., no redistribution, audit rights)
- You'll receive **CPT data files** (XML, CSV, or database format)
- **Annual updates** provided (CPT codes change every January)
- **Compliance audits** may occur (AMA checks that you're not violating terms)

**Step 6: Integration into HKG**
- Import CPT descriptions into Supabase `medical_codes` table
- Join with ICD-10 codes for diagnosis-procedure mapping
- Ensure audit logging (track who searches for what codes)
- Disable code downloads/exports (prevent unauthorized redistribution)

#### Expected Timeline
**2–6 weeks** from first contact to license:
- Day 1–3: Email inquiry
- Day 3–7: AMA responds with questionnaire
- Day 7–14: You complete application
- Day 14–28: Contract negotiation & signature
- Day 28–42: Data delivery and integration

#### Important Compliance Notes
1. **Display requirement**: CPT descriptions must be displayed *exactly as provided by AMA*. Do not edit or paraphrase.
2. **Redistribution**: You cannot sell or share CPT data with third parties (unless licensed separately).
3. **Audit rights**: AMA reserves the right to audit your platform usage.
4. **Attribution**: You may be required to display "CPT © American Medical Association" on your platform.
5. **Annual renewal**: License must be renewed each year (costs may increase).

---

## TIER 2: BUY WITHIN 30 DAYS (Accelerates Doctor Lane)

### 3. FSMB Physician Data Center (PDC) API

#### What It Gives You
Aggregated **physician licensure and discipline data from all 70 state medical boards** in one API. Instead of building 50+ individual state board scrapers, you get:
- **1M+ actively licensed physicians**
- **2M+ total records** (includes inactive, retired, surrendered licenses)
- **Licensure status** (active, inactive, expired, suspended)
- **Discipline records** (license suspension, revocation, fines)
- **Board actions** (restriction letters, probation)
- **Multi-state search** (one query covers all states)

This is the **source of truth** for physician licensure across the US.

#### Why Buy in 30 Days
The Doctor Lane needs verified physician data. Building individual state board integrations is **2–4 weeks of work per state** (HTML parsing, OCR, data cleanup). FSMB PDC gives you **nationwide coverage immediately**.

Use cases:
- **Patient search**: "Is Dr. Smith actually licensed in my state?"
- **Hospital credentialing**: "Does this physician have any license suspensions or discipline?"
- **Insurance verification**: "Can this doctor bill insurance in this state?"
- **Compliance**: "We need to verify all 500 providers in our network every quarter."
- **Regulatory reporting**: "Show all physicians with recent disciplinary actions."

#### Cost
**$9 per physician for standard profile lookups** (one-time or recurring).

For **platform API integration**:
- Contact pdc@fsmb.org for custom pricing
- Likely $5K–15K/year for unlimited queries
- Possible tiered pricing: $0.50–2.00 per query depending on volume

#### Step-by-Step Signup

**Step 1: Review API Documentation**
1. Visit https://www.fsmb.org/PDC/ (main page)
2. GitHub API spec: https://github.com/fsmb/pdc-api (public documentation!)
3. Additional search API: https://github.com/fsmb/med-api
4. Read the README thoroughly — FSMB has done excellent work documenting this

**Step 2: Email FSMB for Integration Access**
Email: **pdc@fsmb.org**

**Subject Line**: `API Integration Request – Healthcare Knowledge Garden Platform`

**Email Template**:
```
Dear FSMB PDC Team,

We are requesting API integration access for physician licensure verification 
in our healthcare credentialing platform, Healthcare Knowledge Garden (HKG).

Company: XRWorkers / Healthcare Knowledge Garden
Primary Contact: Charles Dahlgren (Chilly)
Email: [your email]
Phone: [your phone]

Product Description:
Healthcare Knowledge Garden is an AI-native platform that aggregates and verifies 
healthcare provider data. Our Doctor Lane provides physician credentialing, 
licensure verification, and discipline history checks. We currently manually verify 
physicians using state board websites, but we need FSMB PDC API to automate this 
at scale.

Use Case:
- Real-time physician licensure verification
- Nationwide multi-state search (our users work across 50 states)
- Integration into credentialing workflows
- Compliance and regulatory reporting

Expected Query Volume:
- Pilot phase (Month 1–3): 100 physicians/day = ~3K/month
- Scale phase (Month 4–12): 500 physicians/day = ~15K/month
- Year 2+: 1,000+ physicians/day = 30K+/month

Will we need:
- Real-time API access or batch processing?
- Sandbox environment for testing?
- Production credentials?

We are committed to responsible data use and FSMB mission (physician verification). 
We also plan to make HKG a platform that drives provider adoption and verification 
volume.

Please advise on next steps, pricing, and SLA.

Best regards,
Charles Dahlgren
Founder, XRWorkers
Healthcare Knowledge Garden
[email] [phone]
```

**Step 3: Sandbox Access**
- FSMB will provide **sandbox API credentials** (read-only, test data)
- Use this to test your integration before going live
- Test queries on known physicians in public data

**Step 4: Production Credentials**
- After successful sandbox testing, request **production access**
- You'll receive **API key and rate limits**
- Typical rate limit: 10–100 queries per second (depending on your tier)

**Step 5: API Integration Details**

| Aspect | Details |
|---|---|
| **Protocol** | REST API, JSON responses |
| **Authentication** | API key in headers |
| **Endpoints** | Search (by name, license number, state), Profile lookup |
| **Response Time** | 100–500ms per query |
| **Rate Limits** | 10–100 requests/sec (tiered) |
| **Data Freshness** | Near-real-time (state boards update daily, FSMB syncs 1–2x/day) |

**Example API Call**:
```bash
curl -X GET "https://pdc-api.fsmb.org/api/search?firstName=John&lastName=Smith&state=CA" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

**Example Response**:
```json
{
  "results": [
    {
      "id": "fsmb_12345",
      "firstName": "John",
      "lastName": "Smith",
      "npi": "1234567890",
      "state": "CA",
      "licenseStatus": "Active",
      "licenseNumber": "A12345",
      "licenseExpiration": "2027-12-31",
      "specialty": "Family Medicine",
      "boardCertification": true,
      "disciplineHistory": [],
      "lastUpdated": "2026-04-08"
    }
  ]
}
```

**Step 6: Integration Checklist**
- [ ] Sandbox testing complete (100+ test queries)
- [ ] Logging configured (audit trail)
- [ ] Error handling (rate limit, timeout, retry logic)
- [ ] Database schema updated (store physician_license_status)
- [ ] Deduplication logic (match FSMB IDs to NPI)
- [ ] Update frequency (daily cron job to refresh active physicians)
- [ ] UI integration (show license status in Doctor Lane search)

#### Expected Timeline
**1–3 weeks** from first contact to production API:
- Day 1–2: Email inquiry
- Day 2–5: FSMB responds with sandbox credentials
- Day 5–10: Sandbox integration + testing
- Day 10–14: Request production access
- Day 14–21: Production credentials + live integration

#### Negotiation Tips
1. **Emphasize mission alignment**: "HKG drives physician verification volume, which improves FSMB's data quality."
2. **Offer feedback**: "We'll report data discrepancies we discover to help FSMB improve state board accuracy."
3. **Long-term commitment**: "This is Year 1 of a 10-year platform; we plan to scale verification volume significantly."
4. **Public visibility**: "We'll credit FSMB as the source of truth for physician licensure in our platform."

---

### 4. ABMS Board Certification Verification

#### What It Gives You
Definitive **board certification status** for 1M+ physicians across **24 specialty boards**. This includes:
- **Certification status** (certified, initial certification, not certified)
- **Board name** (American Board of Internal Medicine, Pediatrics, etc.)
- **Specialty** (Cardiology, Orthopedic Surgery, etc.)
- **Certification date** (issued, renewed)
- **Expiration date** (when cert expires, if applicable)
- **Historical records** (lapsed certifications, recertification status)

#### Why Buy in 30 Days
Board certification is one of **the 3 critical verification points** (peer-reviewed literature, clinical guidelines, regulatory databases). Without ABMS, you're missing a critical signal.

Use cases:
- **Patient search**: "Is Dr. Smith board certified in Cardiology?"
- **Hospital credentialing**: "All cardiologists must be ABMS certified."
- **Insurance credentialing**: "We only credential board-certified physicians in this specialty."
- **Patient trust**: "Display board certification badge on Doctor Lane profile."
- **Compliance**: "Our hospital requires board certification verification for all providers."

#### Cost
**Integration-based pricing through ABMS Solutions** (abmssolutions.com). Expect:
- **Per-query**: $0.50–5.00 per verification (depending on volume)
- **Monthly subscription**: $500–5,000/month (depending on query volume)
- **Custom enterprise**: $5K–15K+/year

#### Step-by-Step Signup

**Option 1: Direct ABMS Solutions Partnership** (Recommended)

**Step 1: Review Integration Partners**
ABMS Solutions already integrates with:
- Axuall
- HealthStream
- MD Staff
- symplr
- Verifiable
- Healthgrades

This proves there's a clear integration path.

**Step 2: Contact ABMS Solutions**
Visit: https://www.abmssolutions.com/

Look for:
- **"Contact Us"** or **"Request a Demo"**
- **"Provider Directory"** or **"Credentialing Integration"** solutions

Email contact (if not on site): Check ABMS main website (https://www.abms.org/) for solutions contact

**Email Template**:
```
Dear ABMS Solutions,

We are requesting API integration for board certification verification 
in our healthcare credentialing platform, Healthcare Knowledge Garden (HKG).

Company: XRWorkers / Healthcare Knowledge Garden
Primary Contact: Charles Dahlgren (Chilly)
Use Case: AI-native credentialing platform for hospital systems

Product: Healthcare Knowledge Garden is building the "Doctor Lane" — 
a comprehensive physician credentialing and verification system. We need 
ABMS board certification data to verify physician qualifications across 
24 specialty boards.

Expected Use:
- Real-time certification status lookup
- Batch verification (500–1,000 physicians/month)
- Display certification status in credentialing profiles
- Compliance reporting for hospitals and health plans

Projected Volume: 10K–50K lookups/month (scaling over 12 months)

We are particularly interested in:
1. **ABMS Direct Connect Select** — Integration via existing credentialing software
2. **ABMS Certification Profile Service** — Direct query access
3. Pricing and SLA

Please advise on the best integration path for our platform.

Best regards,
Charles Dahlgren
Founder, XRWorkers
Healthcare Knowledge Garden
[email] [phone]
```

**Step 3: Integration Options**

| Option | Best For | Cost |
|---|---|---|
| **ABMS Direct Connect Select** | Integrating with existing EHR/credentialing software | $1K–5K/yr |
| **ABMS Certification Profile Service** | Direct API access to HKG | $5K–15K/yr |
| **Custom Integration** | Embedded in a specific workflow | $10K–50K/yr |

**Step 4: Expected Response**
- ABMS Solutions will schedule a demo
- They'll ask about your query volume, use case, and timeline
- Pricing discussion (they'll likely request a pilot)

**Step 5: Integration Details**
- Protocol: REST API or SFTP for batch uploads
- Authentication: API key or OAuth
- Response: JSON with certification status, board name, dates
- Rate limits: Depends on your tier

**Option 2: Free Interim Solution** (While Negotiating)

If ABMS Solutions integration takes too long, use the free **"Is My Doctor Certified?" tool**:
- Visit: https://www.certificationmatters.org/
- Search for physicians by name
- Verify board certification manually
- Use this for pilot/launch phase, then migrate to API

#### Expected Timeline
**2–4 weeks** for API negotiation; **free option available immediately**

#### Why This Matters
Board certification is a major credibility signal. Hospitals and patients both need to know:
- "Is this doctor actually certified?"
- "When does the cert expire?"
- "Is recertification required?"

Without this, your Doctor Lane is missing a critical data point.

---

## TIER 3: BUY WITHIN 90 DAYS (Expands Coverage)

### 5. NPDB (National Practitioner Data Bank) — Authorized Query Access

#### What It Gives You
**Individual practitioner malpractice payment and adverse action reports**. This includes:
- **Malpractice payments** (settlements, judgments against the provider)
- **Adverse actions**: License suspensions, revocations, voluntary surrenders
- **Clinical privilege actions** (hospital credentialing denials, reductions)
- **Moral/ethical violations** (drug issues, fraud)
- **Reporting entity** (who reported the action and why)

#### Why 90 Days (Not Now)
The **public NPDB data** (statistics/aggregates) is already free and available. You can use this for:
- Public statistics: "X malpractice cases per specialty"
- General trends: "Malpractice claims increasing by Y% per year"

Full **individual query access** (the complete file) requires:
- You to be an "authorized user" (hospitals, health plans, credentialing organizations)
- HKG to either qualify directly OR partner with an authorized hospital

**Timeline**: This is longer because federal authorization is involved.

#### Cost
- **Public NPDB data**: FREE (statistics only)
- **Individual query access**: Per-query fees (typically $0.50–2.00 per provider)
- **Authorized user setup**: One-time fees ($500–5K)

#### Step-by-Step Signup

**Step 1: Determine Authorized User Status**
Review: https://www.npdb.hrsa.gov/

Check: "Who can query the NPDB?"
- Hospitals
- Health plans/insurers
- Credentialing organizations
- State medical boards
- Self-employed practitioners (limited)

**Step 2: Option A: Apply Directly (If HKG Qualifies)**
Contact HRSA: https://www.npdb.hrsa.gov/contact-us
- Request information on "Credentialing Organization" status
- Ask if HKG qualifies as an authorized entity
- If yes, apply for organizational credentials

**Step 3: Option B: Partner with a Hospital** (Easier Short-term)
- Ask your first hospital client to sponsor NPDB access
- They have authorized credentials; you query through them
- Formalize in your credentialing contract

**Step 4: Expected Setup**
- Federal authorization process (8–12 weeks if applying directly)
- Once approved, you get NPDB access portal credentials
- Able to run individual provider queries
- Data is restricted (cannot export or redistribute)

**Step 5: Integration**
- Link NPDB query results to physician profiles in Doctor Lane
- Display malpractice history (if any) in credentialing review
- Alert on adverse actions (automatic flag for credentialing committee)

#### Expected Timeline
**4–8 weeks** for federal authorization (or immediate if partnering with hospital)

#### Why It Matters
Malpractice history is a **non-negotiable** credentialing data point. Every hospital is required to check NPDB as part of credentialing. Having this in HKG makes credentialing faster and more thorough.

---

### 6. Nursys Institutional e-Notify (Already Free — Formalize Now)

#### What It Gives You
**Real-time nursing license monitoring** via JSON API. Track licensing changes for registered nurses (RNs) and practical nurses (LPNs) across all US states and territories.

This is the **gold standard** for nursing license verification (like FSMB for physicians, but for nurses).

#### Why Buy in 30 Days (It's Free!)
Nursys is **already free**. But formalizing the institutional account gives you:
- Production-grade API access
- Higher rate limits
- 24/7 support
- SLA guarantees

#### Cost
**FREE** (This is the rare exception!)

#### Step-by-Step Signup

**Step 1: Create Nursys Account**
1. Visit https://www.nursys.com/
2. Click **"Register"** or **"Sign Up"**
3. Create your institutional account (not individual nurse search)

**Step 2: Provide Institution Details**
- **Institution Name**: XRWorkers / Healthcare Knowledge Garden
- **Use Case**: Nursing credentialing platform for hospital systems
- **User Count**: Estimate 50–500 users (hospital admins)
- **Query Volume**: 500–1,000 nurse verifications/month

**Step 3: Request API Credentials**
Once your account is created:
- Email the Nursys customer experience team (email provided on your dashboard)
- Request: **"JSON API credentials for our nursing credentialing platform"**
- Ask for: API documentation, rate limits, sandbox endpoint

**Step 4: Set Up API Access**
Expected details:
- **Protocol**: REST API, JSON responses
- **Authentication**: API key in headers
- **Endpoint**: Search by name, license number, state
- **Response**: License status, expiration, discipline history
- **Rate Limits**: 10–100 requests/sec (typically generous for institutional accounts)

**Example API Call**:
```bash
curl -X GET "https://api.nursys.com/search?firstName=Jane&lastName=Doe&state=TX&licenseType=RN" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

**Step 5: Password Management (Important)**
⚠️ **Nursys requires password resets every 90 days**. Set a calendar reminder to avoid account lockouts.

**Step 6: Integration into HKG**
- Add nursing license verification to your Doctor Lane (nurses are part of credentialing)
- Verify RN/LPN status alongside MD/DO verification
- Check for license suspensions or discipline
- Display on nurse profiles in credentialing UI

#### Expected Timeline
**1–2 weeks** to get API credentials

#### Why It Matters
Nurse credentialing is as important as physician credentialing for hospitals. Nurses conduct a huge percentage of patient care, and hospitals need real-time license verification (especially across states for traveling nurses).

---

## TIER 4: FUTURE (Enterprise Scale) — Don't Buy Yet

### 7. Veridoc (Inter-State Verification Service)
- **Cost**: $67 per formal verification
- **What it does**: Legally defensible verification documents for credentialing
- **Buy when**: You need formal, audit-trail verification (typically when hospitals demand it)
- **Use case**: Comply with state regulations requiring documented verification

### 8. NCQA Credentialing Standards
- **Cost**: $5K–15K/year
- **What it does**: NCQA certification standards for credentialing organizations
- **Buy when**: You're ready for enterprise customers who require NCQA-accredited partners
- **Use case**: Become a formally accredited credentialing organization

### 9. Lexis/Westlaw (Legal/Malpractice Deep Dive)
- **Cost**: $5K–20K/year
- **What it does**: Detailed case histories, appeals, settlements for healthcare litigation
- **Buy when**: Hospitals request deeper due diligence on high-risk providers
- **Use case**: Enhanced malpractice history beyond NPDB

---

## RECOMMENDED PURCHASE ORDER & TIMELINE

| Phase | Source | Cost | Timeline | Impact | Action |
|---|---|---|---|---|---|
| **NOW** | CAQH ProView API | $10–25K/yr | 2–4 weeks | Admin Lane credentialing engine | Email CAQH sales |
| **NOW** | AMA CPT License | $1–5K/yr | 2–6 weeks | Billing code search engine | Email amalicensing@ama-assn.org |
| **Within 30 days** | FSMB PDC API | $5–15K/yr | 1–3 weeks | Physician licensure verification | Email pdc@fsmb.org |
| **Within 30 days** | ABMS Board Cert | $5–10K/yr | 2–4 weeks | Board certification verification | Contact ABMS Solutions |
| **Within 90 days** | NPDB Access | $2–5K/yr | 4–8 weeks | Malpractice/adverse actions | Partner with hospital OR apply to HRSA |
| **FREE (do now)** | Nursys e-Notify API | $0 | 1–2 weeks | Nursing license monitoring | Register at nursys.com |

**Year 1 Budget: $25–60K** (depending on CAQH and ABMS final pricing)

---

## IMMEDIATE ACTION ITEMS (This Week)

### ✅ ACTION 1: Email CAQH Sales

**Email To**: sales@caqh.org (or use contact form at https://www.caqh.org/contact-us)

**Subject**: `CPT License Request for Healthcare Knowledge Garden Platform`

**Body** (use template from CAQH section above)

**Owner**: Chilly  
**Deadline**: Today

---

### ✅ ACTION 2: Email AMA Licensing

**Email To**: amalicensing@ama-assn.org

**Subject**: `CPT License Request for Healthcare Knowledge Garden Platform`

**Body** (use template from AMA section above)

**Owner**: Chilly  
**Deadline**: Today

---

### ✅ ACTION 3: Email FSMB PDC

**Email To**: pdc@fsmb.org

**Subject**: `API Integration Request – Healthcare Knowledge Garden Platform`

**Body** (use template from FSMB section above)

**Owner**: Chilly  
**Deadline**: Today

---

### ✅ ACTION 4: Create Nursys Institutional Account

**Website**: https://www.nursys.com/

**Steps**:
1. Click "Register"
2. Select "Institution" account type
3. Fill in XRWorkers / Healthcare Knowledge Garden details
4. Create account
5. Email Nursys for API credentials

**Owner**: Chilly (or delegate)  
**Deadline**: Today (takes 15 minutes)

---

### ✅ ACTION 5: Request ABMS Solutions Demo

**Website**: https://www.abmssolutions.com/

**Steps**:
1. Find contact form or "Request Demo"
2. Submit inquiry (use template from ABMS section)
3. Schedule initial conversation

**Owner**: Chilly  
**Deadline**: Tomorrow (if contact form doesn't auto-respond today)

---

## EMAIL TEMPLATES (Copy-Paste Ready)

### Template 1: CAQH Sales Outreach

```
Subject: Demo Request – Healthcare Knowledge Garden Credentialing Platform

Dear CAQH Solutions Team,

I'm reaching out to request a demo of CAQH ProView API access for our 
healthcare credentialing platform, Healthcare Knowledge Garden (HKG).

Company: XRWorkers / Healthcare Knowledge Garden
Contact: Charles Dahlgren (Chilly)
Website: [your domain, if live]

About HKG:
Healthcare Knowledge Garden is an AI-native platform for hospital credentialing, 
provider verification, and medical billing. We're launching our Admin Lane 
(credentialing engine) in Q2 2026 and need real-time access to comprehensive 
provider data at scale.

Why CAQH:
CAQH ProView is the credentialing data standard. We plan to make CAQH our primary 
source of truth for provider demographics, licensure, board certification, and 
malpractice history. By integrating CAQH API, we'll eliminate the need for 
hospitals to manually verify providers across 50 state boards.

Expected Volume:
- Pilot phase: 10K queries/month
- Scale phase: 100K+ queries/month
- Multi-hospital network (20+ hospital systems by Year 1)

Next Steps:
I'd like to schedule a 30-minute demo to discuss:
1. API capabilities and data coverage
2. Pricing structure for platform integrations
3. Sandbox and production timelines
4. Possible pilot programs

Available: [Your availability this week]

Looking forward to discussing how HKG can expand CAQH's reach into 
AI-driven credentialing.

Best regards,
Charles Dahlgren
Founder, XRWorkers
Phone: [Your phone]
Email: [Your email]
```

---

### Template 2: AMA Licensing Outreach

```
Subject: CPT License Application – Healthcare Knowledge Garden

Dear AMA Licensing Team,

We're requesting a CPT license for our SaaS credentialing platform, 
Healthcare Knowledge Garden (HKG).

Company: XRWorkers / Healthcare Knowledge Garden
Primary Contact: Charles Dahlgren (Chilly)
License Type: Digital Products (SaaS platform)

Product:
Healthcare Knowledge Garden is an AI-native platform for hospital credentialing, 
provider verification, and medical billing. Our Admin Lane includes:
- Real-time provider credentialing workflows
- Medical billing code search and verification
- Insurance contract compliance checks
- Fraud detection and billing anomaly alerts

We need CPT code descriptions displayed alongside code numbers in our 
billing code search interface to help hospital admins and billers:
1. Verify procedure code accuracy
2. Check insurance coverage by code
3. Detect billing anomalies (e.g., high-complexity billing patterns)
4. Support prior authorization workflows

Expected Users:
- Pilot: 1,000 users (10 hospital systems)
- Year 1: 5,000+ users (20+ hospital systems)
- Distribution: Cloud-based, web-only access (no downloads or mobile apps initially)

Use Case Details:
- Billing code search in admin dashboard
- Real-time code lookups during credentialing
- Integration into API for partner EHR systems
- No code download or redistribution

Could you please provide:
1. Pricing for "Digital Products" SaaS licensing
2. License duration and renewal terms
3. Data update frequency (CPT codes change annually)
4. Integration options (API, file format, database)
5. CMS licensing requirements
6. Compliance and audit procedures

We're excited to integrate CPT into HKG and ensure proper licensing.

Best regards,
Charles Dahlgren
Founder, XRWorkers
Phone: [Your phone]
Email: [Your email]
```

---

### Template 3: FSMB PDC Outreach

```
Subject: API Integration Request – Healthcare Knowledge Garden

Dear FSMB PDC Team,

We're requesting API integration for physician licensure verification in 
our credentialing platform, Healthcare Knowledge Garden (HKG).

Company: XRWorkers / Healthcare Knowledge Garden
Primary Contact: Charles Dahlgren (Chilly)

Product Overview:
Healthcare Knowledge Garden is an AI-native platform that aggregates and verifies 
healthcare provider data. Our Doctor Lane helps hospitals verify physician 
qualifications in real-time, including licensure status, discipline history, 
and board certifications. Currently, we manually verify physicians using state 
board websites, which is slow and error-prone. We need FSMB PDC API to automate 
this process at scale.

Use Case:
- Real-time physician licensure verification
- Multi-state search across all 70 state medical boards
- Integration into hospital credentialing workflows
- Compliance and regulatory reporting
- Patient-facing search (transparency)

Expected Volume:
- Month 1–3: 100 physicians/day (~3K/month)
- Month 4–12: 500 physicians/day (~15K/month)
- Year 2+: 1,000+ physicians/day (30K+/month)

Our Goal:
We're building HKG as a market leader in physician credentialing. By having 
FSMB PDC as our authoritative source for licensure data, we'll drive volume 
and verification quality, which benefits FSMB's mission and the medical boards.

We're interested in:
1. Sandbox API credentials for testing
2. Production API access and rate limits
3. Pricing structure for our expected volume
4. SLA and support options
5. Data freshness and update frequency

Please advise on next steps.

Best regards,
Charles Dahlgren
Founder, XRWorkers
Phone: [Your phone]
Email: [Your email]
```

---

### Template 4: ABMS Solutions Outreach

```
Subject: API Integration Request – Board Certification Verification

Dear ABMS Solutions,

We're requesting API integration for board certification verification in 
our healthcare credentialing platform, Healthcare Knowledge Garden (HKG).

Company: XRWorkers / Healthcare Knowledge Garden
Primary Contact: Charles Dahlgren (Chilly)

Product:
Healthcare Knowledge Garden is an AI-native credentialing platform for hospital 
systems and health plans. Our Doctor Lane verifies physician qualifications in 
real-time, including licensure (via FSMB), malpractice history (via NPDB), and 
board certification status (via ABMS).

Board Certification Need:
Every hospital requires board certification verification as part of credentialing. 
Currently, we manually look up physicians on certificationmatters.org. We need 
ABMS API integration to automate this and display certification status directly 
in our credentialing interface.

Expected Usage:
- Initial: 500 lookups/month
- Scale: 5,000–10,000 lookups/month
- Scope: All 24 ABMS specialty boards

Questions:
1. What's the best integration path for a healthcare platform?
   - ABMS Direct Connect Select?
   - ABMS Certification Profile Service?
   - Custom integration?
2. Pricing for our expected volume
3. API documentation and SLA
4. Timeline for sandbox and production access

We see ABMS as a critical component of our 3-point verification system 
(peer-reviewed lit, clinical guidelines, regulatory databases). Board 
certification is a key signal of physician quality.

Please advise on next steps.

Best regards,
Charles Dahlgren
Founder, XRWorkers
Phone: [Your phone]
Email: [Your email]
```

---

### Template 5: Nursys Account Setup (Self-Service)

No email needed — register directly at https://www.nursys.com/

After account creation, email Nursys customer support:

```
Subject: API Credentials Request – Healthcare Knowledge Garden

Dear Nursys Support,

I've created an institutional account for XRWorkers / Healthcare Knowledge Garden.

Account Name: Healthcare Knowledge Garden
Institution Type: Healthcare Technology Platform
Use Case: Nursing credentialing and license verification for hospital systems

We're building a comprehensive credentialing platform for hospitals and would 
like to integrate Nursys API for real-time nursing license verification (RN/LPN).

Could you please provide:
1. JSON API credentials and documentation
2. Endpoint URL and authentication details
3. Rate limits and SLA
4. Sandbox environment (for testing)
5. Support contact for technical issues

Expected volume: 500–1,000 nursing license verifications per month, scaling to 
5,000+/month as we onboard more hospital systems.

Thank you!

Best regards,
[Your name]
XRWorkers / Healthcare Knowledge Garden
[Your email] [Your phone]
```

---

## TRACKING & INTEGRATION CHECKLIST

Use this checklist to track procurement progress:

### Tier 1 (BUY NOW)

- [ ] **CAQH ProView API**
  - [ ] Initial inquiry sent (date: ___)
  - [ ] Sales rep assigned (name: ___)
  - [ ] Sandbox credentials received (date: ___)
  - [ ] Pilot testing complete
  - [ ] Production contract signed (date: ___)
  - [ ] Production API live (date: ___)
  - [ ] Integrated into Admin Lane credentialing engine
  - [ ] Logging and audit trail configured

- [ ] **AMA CPT License**
  - [ ] Inquiry sent (date: ___)
  - [ ] Application questionnaire received
  - [ ] Application submitted (date: ___)
  - [ ] Contract signed (date: ___)
  - [ ] CPT data files received (date: ___)
  - [ ] Data imported into Supabase `medical_codes` table
  - [ ] Billing code search integrated
  - [ ] Compliance audit completed

### Tier 2 (BUY WITHIN 30 DAYS)

- [ ] **FSMB PDC API**
  - [ ] Inquiry sent (date: ___)
  - [ ] Sandbox credentials received (date: ___)
  - [ ] Sandbox testing complete (# test queries: ___)
  - [ ] Production credentials received (date: ___)
  - [ ] API integrated into Doctor Lane
  - [ ] Multi-state search working
  - [ ] Discipline history displays correctly

- [ ] **ABMS Board Certification**
  - [ ] Inquiry sent (date: ___)
  - [ ] Demo scheduled (date: ___)
  - [ ] Pricing discussion (price estimate: $__/yr)
  - [ ] Sandbox or free lookup verified
  - [ ] Production API contract signed (date: ___)
  - [ ] API integrated into Doctor Lane physician profiles

### Tier 3 (BUY WITHIN 90 DAYS)

- [ ] **NPDB Authorized Access**
  - [ ] Authorization path determined (direct or via hospital partner)
  - [ ] Application submitted (date: ___)
  - [ ] Authorization approved (date: ___)
  - [ ] Query access tested
  - [ ] Integration into Doctor Lane malpractice history

- [ ] **Nursys e-Notify API**
  - [ ] Account created (date: ___)
  - [ ] API credentials received (date: ___)
  - [ ] RN/LPN verification integrated
  - [ ] Production testing complete

---

## KEY CONTACTS & DEADLINES

| Organization | Contact Method | Email | Expected Response | Deadline |
|---|---|---|---|---|
| **CAQH** | Contact form + sales | sales@caqh.org | 1–2 days | TODAY |
| **AMA Licensing** | Email | amalicensing@ama-assn.org | 3–5 days | TODAY |
| **FSMB PDC** | Email | pdc@fsmb.org | 2–3 days | TODAY |
| **ABMS Solutions** | Contact form | Check website | 1–2 days | TODAY |
| **Nursys** | Self-service registration | support@nursys.com (after account) | Immediate | TODAY |

---

## SUCCESS METRICS

Once all data sources are integrated, HKG will have:

✅ **Complete credentialing data** (CAQH + FSMB + ABMS + NPDB + Nursys)  
✅ **Billing code engine** (AMA CPT + ICD-10)  
✅ **3-point verification** (peer-reviewed lit ✅, clinical guidelines ✅, regulatory databases ✅)  
✅ **Nationwide coverage** (all 50 states + territories)  
✅ **Real-time updates** (physician licenses, discipline, board certs)  
✅ **Competitive moat** (API integrations + data aggregation)

This positions HKG as the **definitive credentialing and provider verification platform** for hospital systems and health plans.

---

## APPENDIX: Regulatory & Compliance Notes

### HIPAA Considerations
- All provider data is non-PHI (not patient health information)
- But credentialing records may include sensitive information (malpractice history)
- Ensure audit logging for access control
- Encrypt data at rest (Supabase encryption)

### Data Licensing & Redistribution
- ✅ CAQH: Can use for credentialing, cannot redistribute
- ✅ AMA CPT: Can display descriptions, cannot download/export
- ✅ FSMB: Can query and store, attribution required
- ✅ ABMS: Can display, cannot bulk export
- ✅ NPDB: Federal data, limited authorization
- ✅ Nursys: Can query, audit trail maintained

### Federal Compliance
- NPDB: If querying malpractice data, you may be required to report back to NPDB (depends on your role)
- State Boards: Some states require credentialing organizations to be registered
- DEA: If storing DEA numbers, certain safeguards apply

---

## Questions?

For questions about this guide, specific integrations, or prioritization, reach out to Chilly (Charles Dahlgren).

This guide is a **living document**. As integrations complete and new data sources emerge, it will be updated with real-world learnings.

**Last Updated**: April 9, 2026  
**Next Review**: May 9, 2026
