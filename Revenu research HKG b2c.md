# Revenue architecture for a healthcare knowledge graph platform

A healthcare knowledge graph with **9.4M+ NPI records** sits atop a revenue opportunity spanning three interconnected markets worth a combined **$250B+ in addressable spend** — from mandatory insurer compliance budgets to the exploding consumer healthspan economy to high-margin clinical service referrals. The most immediate revenue comes from insurance companies legally forced to maintain accurate provider directories (Area 1), the largest volume from consumer monetization through affiliate and subscription models (Area 2), and the highest per-transaction value from clinical trial matching and regenerative medicine referrals where a single conversion can generate $1,000–$10,000 (Area 3). What follows is a detailed breakdown of pricing models, commission structures, regulatory drivers, and market sizing across all three areas.

---

## Area 1: Insurance companies must pay for provider data — and penalties are rising

### The regulatory hammer creating mandatory demand

The No Surprises Act (effective January 2022) requires health plans to **verify and update provider directory data every 90 days**, update online directories within **48 hours** of receiving changes, and respond to patient inquiries about network status within **one business day**. Violations carry fines of **up to $10,000 per violation**, and CMS can halt a plan's ability to enroll new members for an entire plan year — a sanction worth millions in lost premium revenue.

Yet enforcement has been strikingly weak. A ProPublica investigation (November 2024) found that **86% of listed mental health providers** in New York were unreachable, not in-network, or not accepting new patients. Arizona regulators couldn't schedule visits with nearly **2 out of every 5 providers** called. California, despite enacting ghost network regulation in 2016, has issued only a single fine — **$7,500** — for inaccurate mental health listings. Fewer than a dozen fines are issued nationally in an average year. Insurers treat penalties as a rounding error against billions in profits.

That's changing. The bipartisan **REAL Health Providers Act** would require Medicare Advantage plans to update provider directories annually starting 2026. Starting 2025, payers in state-based exchanges using HealthCare.gov must meet network adequacy standards, expanding to **all state-based exchange plans by 2026**. Massachusetts announced it "will consider penalties" against materially noncompliant insurers. The regulatory trajectory is unmistakably toward stricter enforcement, creating growing mandatory demand for provider data accuracy solutions.

### A $1.5–5.8 billion market with room for new entrants

The provider data management market is valued at approximately **$1.5–2.5 billion in 2025** for the core directory accuracy segment, within a broader healthcare payer network management market of **$4.7–5.8 billion** growing at 9–15% CAGR. The CAQH 2025 Index (released February 2026) found the healthcare industry still spends **$83 billion annually** on administrative transactions between providers and plans, with a remaining **$21 billion savings opportunity** through full automation. CAQH estimates administrative savings of **$90 million for every 1 million providers** using centralized data solutions.

The competitive landscape reveals a striking range in scale and monetization success:

| Company | Revenue | Model | Key metric |
|---------|---------|-------|------------|
| **Kyruus Health** | ~$125M (2024) | Enterprise SaaS | 1B+ provider searches; acquired by RevSpring Q4 2025 |
| **Verato** | $35.5M (2024, +101% YoY) | Master data management | 75%+ of U.S. population flows through platform |
| **CAQH DirectAssure** | Industry utility | $1.68/provider/year | 4M+ provider records, 1,000+ health plans |
| **Ribbon Health** | $4.2M (2024) | API per-query | Acquired by H1 January 2025; $55M+ raised |
| **LexisNexis Health Care** | Undisclosed (part of $3B+ RELX segment) | Enterprise contracts | 8.5M+ practitioner records |
| **Optum** | Undisclosed (part of $200B+ Optum) | Enterprise | Leader in Everest Group PEAK Matrix 2025 |

Ribbon Health's modest **$4.2M revenue** against $55M+ in funding is notable — it signals that the provider data API market has been difficult to monetize at scale, though the H1 acquisition suggests strategic value in the data asset itself. Kyruus at **$125M with 30% growth** but sub-5% EBITDA margins demonstrates that enterprise SaaS is the proven path to scale, even if profitability remains elusive.

### Pricing models and what a 9.4M-record platform could charge

Five pricing architectures dominate this market. **Per-provider-per-year (PPPY)** is the simplest: CAQH DirectAssure charges **$1.68/provider/year**, meaning 9.4M NPI records priced equivalently would generate ~$15.8M annually — though premium verification services could command **$3–10/provider/year**. **API per-query pricing** typically runs **$0.01–$0.50 per query** depending on data richness. **Enterprise SaaS licenses** range from **$100K–$5M+ annually** — Verato averages ~$400K per client across 90+ customers. **PMPM (per-member-per-month)** pricing for health plan data services runs **$0.05–$0.50 PMPM**; a plan with 1M members at $0.25 PMPM generates $3M annually per client. **Compliance modules** for CMS/NSA audit readiness sell as $50K–$250K/year add-ons.

A realistic near-term revenue model: 10 enterprise health plan clients at $1M average ($10M), 50 mid-market plans at $300K ($15M), plus API/data feed revenue from digital health companies ($5M) = **$25–30M ARR within 3–5 years** for a well-positioned entrant with genuine data differentiation.

### Telehealth economics favor access fees, not per-referral payments

Insurers do not typically pay per-referral for patient-provider matching. The dominant model is **network steering** through cost-sharing differentials, tiered networks, and narrow networks. Teladoc Health — with **$2.53 billion in 2025 revenue** across 17.1 million visits — generates **83% of revenue from recurring PMPM/PEPM access fees**, not per-visit payments. Amwell generated **$249.3 million** with a similar subscription-heavy split ($132.4M subscriptions, $94.3M visit revenue).

Telehealth parity has advanced but isn't universal: **23–24 states** now mandate payment parity (same reimbursement for telehealth as in-person), with 5 additional states having parity with caveats. CMS has made codes like psychiatric diagnostic evaluations and 45-minute psychotherapy sessions **permanently reimbursable** for telehealth. Consumer-facing visit prices run **$29–$79** (Sesame/Costco partnership) to **$49** (Amazon One Medical), while blended insurer reimbursement averages approximately **~$140/visit** across Teladoc's network.

---

## Area 2: The healthspan economy is a $600B+ monetization surface

### Market sizing reveals enormous, fast-growing adjacent markets

The consumer healthspan economy is not one market but a constellation of rapidly expanding segments that a trusted health platform can monetize through its "gravity well" of free tools:

The **GLP-1 weight loss drug market** alone reached **$53–66 billion in 2025** and is projected to hit $133–315 billion by 2034-2035, with semaglutide holding 53% market share. J.P. Morgan estimates **30M+ Americans** will be on GLP-1 treatment by 2030. Semaglutide loses U.S. patent exclusivity **March 20, 2026**, meaning generics will dramatically expand the addressable patient population — and the demand for information, comparison, and provider matching.

The broader **wearable health technology market** hit **$82.3 billion in 2025** (growing to $256B by 2034). Oura expects ~$500M in 2024 revenue with a **$5B valuation**, while WHOOP launched its 5.0 device with ECG and blood pressure monitoring. The **biohacking market** reached **$24.5–33 billion** and is growing at 18–19% CAGR. **Anti-aging supplements** represent a $4.9 billion market, with the **NAD+ products segment** alone at $3.45 billion growing at 15.1% CAGR. The **NMN market** ($339–373M in 2025) accounts for 45% of NAD precursor supplement revenue.

Additional segments include the **regenerative medicine market** ($35–41B), **precision medicine** ($100–119B), **mHealth apps** ($36.7B), and the **cold plunge market** ($330–352M). The total **global wellness economy exceeds $6 trillion**, with the longevity-specific slice estimated at **$610 billion by 2026**.

### Affiliate commissions range from 2% to 50% across categories

Affiliate economics vary dramatically by product category, and a health knowledge platform would be positioned to capture the highest-paying tiers due to its trusted, health-intent audience:

**Supplements** offer the richest commissions. Wolfson Brands (NooCube) pays **40–50%** with recurring commissions on repeat orders. Thorne pays **20%** with a 30-day cookie. Seed probiotics pays **$25 per subscription** plus bonuses. Athletic Greens (AG1) pays **5–10%**, Onnit **15%**, and the industry range spans **5–30%** with an average around 15–20%.

**Wearables and devices** pay less but on higher price points. Oura Ring pays **2.2–6%** on a $299+ device. Levels Health (CGM) pays **$50–100 per member**. Muse meditation devices pay ~**10%** (~$40/sale). Red light therapy brands like BonCharge pay **15%** on $300 average orders ($45/sale), while Therasage and Red Light Rising pay **10%** on $310–372 AOVs.

**High-ticket wellness** delivers the largest per-sale payouts. Wellness retreat platform Rythmia pays **$1,500 per booking** with a 365-day cookie. Tripaneer pays **up to 50%** on retreats costing $1,000+. Online therapy platforms pay **$150 per conversion**. Cold plunge brands (Plunge) pay **5–15%** on $3,000–8,000+ units, yielding $150–800+ per sale.

**Water filtration and clean-living products** maintain meaningful programs: Epic Water Filters pays **15%** (60-day cookie), Crystal Quest **10%**, and Pure Air Pure Water **up to 30%**. These map directly to the health-conscious audience a medical knowledge platform attracts.

### Proven revenue models from health content platforms

The economics of health content monetization are well-established through public and semi-public data from comparable platforms. **GoodRx** demonstrates the power of free tools with transactional monetization: **$792.3 million in 2024 revenue** from ~30M annual consumers, yielding roughly **$26 revenue per active user per year** primarily through PBM/pharmacy commissions, with a **28.6% adjusted EBITDA margin**. GoodRx Gold subscriptions ($9.99–$19.99/month) add a premium layer.

**Hims & Hers Health** proves the subscription DTC model at scale: **$1.48 billion in 2024 revenue** (69% YoY growth) from 2.4M subscribers at **$73–84 monthly ARPU**. The company targets **$6.5B revenue and $1.3B EBITDA by 2030**. Noom reached **~$1B ARR** with ~1.5M paying subscribers, charging $17–70/month for weight coaching and $99/month for its GLP-1 program (which hit $100M revenue run-rate within 4 months of launch).

Health content advertising commands premium rates. **Health content RPMs run $15–50+ per thousand pageviews** with direct pharma buys, compared to $2–8 for entertainment content. U.S. healthcare digital ad spending reached **$24.77 billion in 2025** (+13.3% YoY), with 72.2% of healthcare ad spend now digital. Pharma CPMs for targeted physician audiences reach **$30–100+**.

### Customer acquisition economics favor trusted platforms

Wellness brands face escalating acquisition costs that make trusted platform partnerships increasingly attractive. **Premium wellness supplement brands** spend an average of **$210 per customer acquisition**. Clinical skincare/dermatology brands spend **$380**. Even mass-market personal care averages **$76**. The average healthcare cost per lead is **$320**. Noom's trajectory illustrates the arms race: ad spend grew from $5M to $330M (2017-2021) to scale revenue from $12M to $600M.

Brands spending $40–380 per customer would readily pay **$5–50+ per qualified lead** from a trusted medical platform with verified health-intent signals. A platform generating 10M monthly health-intent users represents an extraordinarily valuable audience in a market where digital health ad budgets exceed $24 billion annually.

### Freemium conversion benchmarks and subscription potential

Conversion rates for health apps show a wide but instructive range. The industry median for **freemium app conversion is 2.18%**, but health and fitness apps achieve **12.1% download-to-paying conversion** at the 90th percentile. **Opt-out free trials convert at 48.8%**, opt-in trials at **18.2%**. Annual plans reduce churn by **51%** compared to monthly, and annual subscribers are **2.4x more profitable**. "Super-users" (top 20%) generate **72% of revenue**.

For a healthcare knowledge platform, a realistic model assumes 2–5% freemium conversion at $10–$49/month for premium features (personalized AI health assistant, advanced drug interaction checking, concierge provider matching). With 5M free users and a 3% conversion rate, that's 150,000 paid subscribers generating **$18M–$88M annually** at the $10–$49 price range. The Hims model ($73–84/month ARPU) demonstrates that health-motivated consumers will pay substantially more when receiving tangible value.

---

## Area 3: High-value medical services offer $1,000+ per conversion

### Clinical trial matching is the highest-value referral opportunity

Pharma companies spend **$15,000–50,000 per recruited patient** for clinical trials, with patient recruitment accounting for **32% of total trial costs** — the single largest cost driver. Total per-patient clinical trial costs reach a **$41,117 median**, climbing to $113,000–136,000 for Phase III studies. With **80% of trials delayed** due to recruitment challenges and over 512,000 ongoing trials worldwide, the demand for patient matching is acute.

Companies like **Antidote Technologies** use a pay-per-randomized-patient model where sponsors pay only when patients actually enroll. **SubjectWell** operates similarly, launching its OneView recruitment portal in February 2025. The clinical trial recruitment services market spans **$3.5–11.8 billion in 2025**, projected to reach $26 billion+ by 2035. A knowledge graph platform matching patients to appropriate trials could capture **$1,000–10,000+ per successfully enrolled patient**, or sell SaaS licensing at **$50K–500K+ annually** to pharma sponsors.

### Regenerative medicine and longevity clinics offer the easiest referral economics

Cash-pay longevity treatments face minimal regulatory friction for referral fees (no insurance anti-kickback constraints) and carry high per-patient values. **NAD+ IV therapy** runs **$250–1,500 per session**, with multi-session packages at $1,500–6,000. **Stem cell therapy** costs **$5,000–50,000 per treatment** (most commonly $5,001–10,000). **Comprehensive longevity programs** range from $10,000–150,000 annually — Fountain Life packages start at $20,000, Human Longevity assessments run ~$25,000.

These clinics rely heavily on digital marketing and influencer partnerships for patient acquisition, with estimated acquisition costs of **$500–3,000+ per patient**. A platform connecting health-conscious users to vetted longevity providers could charge **$200–2,000 per converted patient** through referral fees, or $500–5,000/month for premium clinic listings. This segment represents one of the **highest monetization opportunities per transaction** due to the cash-pay nature and high treatment margins.

### Concierge medicine pays handsomely for members with long retention

The **concierge medicine market reached $20.4–23.6 billion in 2025**, projected to reach $39–48 billion by 2033. **MDVIP** — the largest concierge network with 1,300+ physicians and 400,000+ patients — charges annual membership fees of **$1,800–5,000/year** and retains 90% of patients. Physicians pay roughly one-third of membership fees as a royalty ($800–1,667/patient/year). Executive health programs command **$10,000–50,000+ annually**.

Patient lifetime value is substantial: at $2,400–5,000/year with 90% retention, **5-year LTV reaches $10,800–22,500**. For premium executive programs, LTV can reach **$45,000–225,000**. A referral fee of **$200–2,000 per converted member** (4–10% of first-year value) would be economically rational for practices that limit panels to 400–600 patients and need every slot filled with committed members.

### Medical tourism and telehealth marketplaces round out the revenue stack

Medical tourism facilitators earn **10–40% commissions** from international hospitals on procedures costing $5,000–50,000+, translating to **$500–10,000 per referral**. The global market spans $34–91 billion depending on definition, with 1.4 million U.S. patients traveling annually, 60% motivated by domestic cost differentials of 50–65%.

Telehealth marketplaces demonstrate volume-based economics. **Zocdoc** charges **$35–110 per new patient booking** depending on specialty, with an effective patient acquisition cost of ~$84 per new patient. Typical healthcare marketplace take rates run **15–25%** of transaction value. **Sesame** offers virtual primary care from $29 through its Costco partnership, demonstrating consumer price sensitivity and willingness to use marketplace platforms for healthcare access.

---

## Conclusion: Three revenue engines with distinct economics

This analysis reveals three fundamentally different revenue architectures for a healthcare knowledge graph platform, each with distinct economics and timelines:

**Insurer B2B revenue** ($25–30M ARR potential within 3–5 years) is driven by regulatory mandates that create non-discretionary spending. The No Surprises Act's 90-day verification requirement and expanding state ghost network legislation mean insurers *must* maintain accurate directories — and current enforcement, while weak, is tightening. The pricing model here is enterprise SaaS (PMPM or per-provider-per-year), and the competitive moat comes from data freshness and NPI record completeness. Kyruus's $125M revenue validates enterprise willingness to pay; Ribbon Health's $4.2M revenue signals that API-only approaches struggle without deep integration.

**Consumer healthspan revenue** offers the largest TAM ($600B+ longevity economy) but requires scale. The "gravity well" model — free tools attracting millions, monetized through affiliate commissions (10–20% average), premium subscriptions (2–12% conversion at $10–79/month), and health advertising ($15–50 RPM) — is proven by GoodRx ($792M from free tools), Hims ($1.48B from subscriptions), and Noom (~$1B from behavioral coaching). The critical insight is that **GLP-1 patent expiration in March 2026** will create an enormous information-seeking wave among tens of millions of new potential users.

**High-value medical service referrals** generate the largest per-transaction revenue. Clinical trial matching ($1,000–10,000 per enrolled patient), longevity clinic referrals ($200–5,000 per patient), concierge medicine leads ($200–2,000 per member), and medical tourism commissions ($500–10,000 per referral) all exploit the knowledge graph's unique ability to connect patients with specialized, high-margin services. The cash-pay nature of regenerative medicine and longevity clinics makes these referral relationships the simplest to structure legally, while clinical trial matching represents the single highest willingness-to-pay at $15,000–50,000 per recruited patient from pharma sponsors.

The strategic sequence matters: build the insurer B2B base for credibility and recurring revenue, use the free patient tools to build consumer scale, then layer high-value medical service referrals on top of the resulting user base. Each layer reinforces the others — insurer data accuracy improves the consumer experience, consumer scale attracts premium service providers, and the knowledge graph's comprehensiveness (drug interactions, clinical trials, NPI records, PubMed citations) creates a defensible moat that point solutions cannot replicate.