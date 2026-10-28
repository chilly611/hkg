# Source terms: the eight live sources

Read 2026-10-28, filed 2026-10-28. For each live source: the publisher's own terms of use, data use agreement, license or dissemination notice, with the clauses on redistribution, commercial use, attribution and derived works quoted verbatim.

**This is a reading, not legal advice.** The "Reading" line under each source says what the quoted text appears to allow and forbid. It has not been reviewed by a lawyer. No rights field was set anywhere from this document.

## Summary

| Source | Terms page on the publisher's site? | Fee | Registration | Reading, in one line |
|---|---|---|---|---|
| OIG LEIE | No. Download page and website disclaimers only | None stated | None (direct CSV link) | No stated limits on reuse |
| SAM.gov exclusions extract | Yes: SAM.gov Terms of Use | None stated | Not needed to list the public folders; API keys are tied to accounts | Public data free to share; D&B strings on pre-2022-04-04 records |
| NPPES data dissemination | No license. CMS dissemination page and Federal Register notice CMS-6060-N | "No charge" | None | FOIA-required release, no stated limits |
| Texas Medical Board licensure file | No terms on the open-data dataset (license field empty). TMB site policy | None (open data) | None | "Public domain" per TMB; notice requested before publication |
| Florida MQA licensee download | No terms found on public pages. User guide and site disclaimer | None stated | Account sign-in required | Chapter 119 public records, no stated limits |
| California DCA public information file | No file-specific terms. DCA page plus CA.gov Conditions of Use | None | None (public Box link) | Public domain by default, "as permitted by law" |
| CMS Medicare opt-out affidavits | No terms page on data.cms.gov. Catalog license field | "Public Use File (Free)" | None | Federal government work, no CMS-specific limits |
| CMS PECOS public provider enrollment | Same as opt-out | "Public Use File (Free)" | None | Same as opt-out |

## Method

- Pages were fetched on 2026-10-28 from the publisher's own domain, or a state portal the publisher uses. JS-rendered pages (data.cms.gov, data.texas.gov, sam.gov/data-services) were read in a browser.
- Quotes are copied from the fetched text and kept under 40 words. "…" marks a cut inside a quote.
- "None stated" means no page read here addresses the point. It does not mean the point is settled.
- No data files were downloaded, no accounts were created and no forms were sent.

## 1. OIG LEIE (List of Excluded Individuals/Entities)

Publisher: HHS Office of Inspector General.

URLs read 2026-10-28:
- https://oig.hhs.gov/exclusions/leie-database-supplement-downloads/ (where `https://oig.hhs.gov/exclusions/exclusions_list.asp` now redirects; "Last Update 10-09-2026")
- https://oig.hhs.gov/oig-policies/web-site-disclaimers/ ("Last updated May 7, 2026")
- https://oig.hhs.gov/oig-policies/ (index)
- https://oig.hhs.gov/faqs/exclusions-faq/

**No terms page.** OIG publishes no terms of use, license or data use agreement for the LEIE. The OIG policies index lists accessibility, guidance practices, privacy, official site, plain writing, service of process and website disclaimers; none covers reuse or copyright. Nearest statements:

- Redistribution: none stated. The download page describes the purpose: "HHS-OIG offers a CSV download of active OIG exclusions that can be used on your local computer or to populate the database program of your choice."
- The only distribution limit stated concerns SSNs: "The Privacy Act prohibits the distribution of SSNs so regardless of your exact process, you'll need to use the Online Search to verify specific individuals and entities." The FAQ adds: "Note: The Downloadable Database does not contain SSNs or EINs."
- Commercial use: none stated. The disclaimer covers endorsement only: "Reference in this website to any specific commercial products, process, service, manufacturer, or company does not constitute its endorsement or recommendation by the U.S. Government or HHS-OIG."
- Attribution: none stated.
- Derived works: none stated. Nearest: "The information provided using this website is only intended to be general summary information to the public. It is not intended to take the place of either the written law or regulations."
- Federal public-domain notice: none on OIG's site. The file is a U.S. government work (17 U.S.C. § 105), but OIG does not say so.

Fee: none stated. Registration: none; the CSV is a direct link (`https://oig.hhs.gov/exclusions/downloadables/UPDATED.csv`).

**Reading (not legal advice):** nothing in OIG's text limits copying, redistribution, commercial use or derived works. OIG offers the file for loading into your own database. The one stated constraint, on SSNs, does not bite because the file carries none. OIG also says verifying a specific person needs its online search.

## 2. SAM.gov exclusions extract

Publisher: General Services Administration (GSA).

URLs read 2026-10-28:
- https://sam.gov/about/terms-of-use (sections Data Access, Sensitive Data, Privacy Policy with "Reuse and Copyright", and Restricted Data Use)
- https://sam.gov/data-services/Exclusions?privacy=Public (folder listing: "Public - Historical", "Public V2 FASCSA Orders", "Public V2")

**Terms page: yes.** The page says the terms bind anyone who uses the site: "SAM.gov is a federal government website. When you use this site, you must follow these terms. If you do not, you may lose access to SAM.gov and we may take other legal action."

- Redistribution: "Most material on our site is free of copyright and may be copied and distributed without permission." Also: "If you want to share data publicly, only share data from public versions of APIs."
- Federal public-domain notice: "Works produced by federal government employees in the course of their employment are generally not protected by copyright and are in the public domain in the U.S."
- Third-party data in exclusion records: "D&B Open Data may be in entity registration records last updated before April 4, 2022, and exclusion records created before April 4, 2022." D&B Open Data is legal business name and address fields (name, street, city, state, county code, ZIP, country).
- Redistribution limit on that D&B data: "You may not share D&B Open Data in bulk (that is, enough records that someone could use them as an original data source or a substitute for getting data from D&B)."
- Commercial use: "You may not use D&B data (except for D&B Open Data) for commercial, resale, or marketing purposes." The SAM Non-Disclosure Agreement's commercial-use bar applies to federal "Data Receivers" of non-public data, not to public extracts.
- Attribution: "Citation of the GSA site and a link back is much appreciated." For D&B Open Data, attribution is a condition: "You must state in writing that D&B is the data source."
- Derived works: none stated for public data. For non-public data: "You may not use any sensitive API to build out a public view of any SAM data. You must use the public version of any API if you wish to display or disseminate the public-facing data."
- Access method: "Automated data gathering, web scraping tools are prohibited and, if detected, will result in the associated account(s) being denied access to SAM.gov via Login.gov." The terms point to the sanctioned routes: "SAM.gov makes certain data available via APIs and extracts with URLs “https://open.gsa.gov/api/” and “https://sam.gov/data-services.”"

Fee: none stated. Registration: the public exclusions folders were listed without sign-in on 2026-10-28; no file was downloaded. API keys belong to accounts: "Do not share your individual account API key with anyone."

**Reading (not legal advice):** public exclusion data appears free to copy, redistribute and reuse, commercially too, with a "much appreciated" (not required) credit to GSA. Two strings attach to exclusion records created before 2022-04-04, whose name and address fields may be D&B Open Data: crediting D&B in writing is required, and sharing those fields "in bulk" is forbidden. Scraping is forbidden; use the extracts or APIs. Whether republishing the full public extract counts as sharing D&B Open Data "in bulk" is the open question for this source.

## 3. NPPES data dissemination (NPI downloadable file)

Publisher: Centers for Medicare & Medicaid Services (CMS).

URLs read 2026-10-28:
- https://www.cms.gov/medicare/regulations-guidance/administrative-simplification/data-dissemination ("Page Last Modified: 09/10/2024")
- https://www.cms.gov/regulations-and-guidance/administrative-simplification/nationalprovidentstand/downloads/datadisseminationnpi.pdf (notice CMS-6060-N, 72 FR 30011, May 30, 2007)
- https://download.cms.gov/nppes/NPI_Files.html. On 2026-10-28 this page showed only: "Important Information: This site will be down for maintance until further notice" [sic].

**No license or terms page.** CMS releases the file under FOIA. The dissemination page and the Federal Register notice are the governing statements.

- Basis: "The information disclosed on the NPI Registry and in the downloadable files are FOIA-disclosable and are required to be disclosed under the FOIA and the eFOIA amendments to the FOIA."
- Redistribution: no limit stated. One request, worded as a suggestion: "For those users who download the file and share the downloaded data on their own website(s), CMS suggests that only the same data be displayed for those deactivated NPIs (i.e., deactivated NPI and date of deactivation ONLY)."
- Commercial use: none stated. The notice says who may ask: "Anyone may request NPIs and other NPPES health care provider data from HHS under the FOIA."
- Attribution: none stated.
- Derived works: none stated. Nearest: "It is intended that the file be downloaded and the data be imported into a relational database, or otherwise manipulated, by individuals with the requisite technical expertise."
- Providers cannot withdraw: "There is no way to ‘opt out’ or ‘suppress’ the NPPES record data for health care providers with active NPIs."

Fee: "There is no charge to download the data." The notice says the same: "There will be no charge to download the files." Registration: none. Support: "There is no Help Desk or other technical support available from CMS, the NPI Enumerator, or any other CMS contractor for downloading, manipulating, or using the file."

**Reading (not legal advice):** a FOIA-required public release with no license, no fee and no stated limit on redistribution, commercial use or derived works. CMS's one ask, a suggestion and not a condition, is to show only the NPI and deactivation date for deactivated NPIs. Operational note: the download page said "down for maintenance" on the day of reading.

## 4. Texas Medical Board licensure file

Publisher: Texas Medical Board (TMB). The file the repo loads is the Texas Open Data Portal dataset "DataSet-01-All Licenses" (`tm3v-pfq9`), which names TMB as its provider.

URLs read 2026-10-28:
- https://data.texas.gov/d/tm3v-pfq9 (dataset page; "Last Updated October 28, 2026", "Data Provided By Texas Medical Board")
- https://data.texas.gov/api/views/tm3v-pfq9.json (dataset metadata)
- https://www.tmb.texas.gov/about-us/policies (TMB Site Policies)
- https://www.tmb.texas.gov/laws-rules/open-records

**No terms on the dataset.** The dataset page shows no license or terms link. Its metadata reads `"license": null`, `"attribution": "Texas Medical Board"`, `"provenance": "official"`. Nearest statement, TMB's site policy:

- Redistribution and derived works: "The content of our site is considered "public domain" and therefore can be used without permission". It continues: "prior to publication, we request notification from the public detailing the specific content being used and the location where the content will be published."
- Commercial use: none stated for content. The policy limits only fee-charging links: "we have no restrictions on linking to our site, as long as a fee is not charged to access the site."
- Attribution: none required. The portal's metadata attribution field names "Texas Medical Board".
- Conflicting line: the TMB site footer reads "© 2025 Texas Medical Board. All rights reserved."

Fee: none for the open-data download. Registration: none. Copies requested under the Texas Public Information Act are a separate route with charges (the open records page: "Receive a statement of estimated charges, when charges exceed $40, in advance of work being started").

**Reading (not legal advice):** TMB calls its site content public domain, usable without permission, and asks (does not require) notice before publication. The open-data copy carries no license, which leaves TMB's policy as the nearest statement. Two caveats: the policy speaks of "content of our site" while the file sits on data.texas.gov, and the footer's "All rights reserved" contradicts "public domain". Sending TMB the requested notice would answer both.

## 5. Florida MQA licensee download

Publisher: Florida Department of Health, Division of Medical Quality Assurance (MQA).

URLs read 2026-10-28:
- https://flhealthsource.gov/data-portal/ (links to the portal and its guides)
- https://data-download.mqa.flhealthsource.gov/ (redirects to an Azure B2C sign-in page at `mqab2c.b2clogin.com`)
- https://mqa-internet.doh.state.fl.us/MQASearchServices/Content/HelpFile/MQA%20SearchServices%20and%20DataDownload%20UserGuide.pdf ("Revised 1.27.2025", "Version 1.0")
- https://flhealthsource.gov/disclaimer/
- The older URL `https://mqa-internet.doh.state.fl.us/downloadnet/Licensure.aspx` returned HTTP 401.

**No terms found on public pages.** No terms of use, license or data use agreement appears on any public MQA page read. The sign-in or sign-up screens may show terms; they were not reached because no account was created. Nearest statements:

- Basis: "Here, you’ll find general information about accessing public data provided by the Florida Department of Health, in compliance with Chapter 119, Florida Statutes." (user guide, section 3.2)
- Exclusions and support: "Some information, such as financial or medical records and Social Security numbers, is confidential and excluded. Users are responsible for managing downloads, as technical support is not provided."
- Why sign-on exists: "Sign-on is a critical feature of the Data Download Portal and ensures that our data team can better understand how users interact with the platform and utilize the available data."
- Disclaimer: "Content provided by the Florida Department of Health presented herein is for informational purposes only." It also limits reproduction of images only: "These images are for viewing purposes only. Any reproduction may be prohibited under federal/state copyright or trade secret laws."
- Redistribution, commercial use, attribution, derived works: none stated.

Fee: none stated. Registration: required; an account sign-in, which the guide says is for tracking use and sending notices.

**Reading (not legal advice):** public records released under Chapter 119, with no stated limit on redistribution, commercial use or derived works, no attribution requirement and no fee. Not read: whatever the sign-up screen asks a new user to accept.

## 6. California DCA public information file

Publisher: California Department of Consumer Affairs (DCA), covering the Medical Board of California and the Osteopathic Medical Board of California among others.

URLs read 2026-10-28:
- https://www.dca.ca.gov/consumers/public_info/index.shtml ("Public Information – Licensee Lists Overview")
- https://www.ca.gov/legal/conditions-of-use/ (linked from the DCA page footer as "Conditions of use")
- The files sit in a public Box folder linked from the DCA page (`https://dca.box.com/s/oss6hf8jys2bmgxqd2gdz7w4oepm2il9`); the folder was not opened today.

**No file-specific terms.** The DCA page gives the legal basis and no reuse terms; the state's site-wide Conditions of Use are the nearest statement.

- Basis: "The Department of Consumer Affairs (DCA) provides information to the public regarding over 150 professional license types … in accordance with the Information Practices Act, Civil Code § 1798.61, and Business and Professions Code § 161."
- Scope: "Each Agency has a folder above from which you can access licensee data suitable for disclosure."
- Redistribution and derived works: "In general, information presented on this website, unless otherwise indicated, is considered in the public domain. It may be distributed or copied as permitted by law."
- Third-party material: "In order to use any information on this website not owned or created by the State, you must seek permission directly from the owning (or holding) sources."
- Commercial use, attribution: none stated.
- Disclaimer: "The State makes no claims, promises, or guarantees about the absolute accuracy, completeness, or adequacy of the contents of this website".

Fee: none. Registration: none; the Box link is public. The board survey (`docs/board_survey_2026-10-28.md`) records a second route, the Medical Board of California's own Access database, whose request form has a terms checkbox with unpublished terms. It was not read again here.

**Reading (not legal advice):** licensee data DCA deems disclosable, presented as public domain by default and copyable and distributable "as permitted by law", with no attribution requirement and no commercial limit. Caveat: the Conditions of Use speak of "this website" (CA.gov), DCA links them from its own footer, and the files are served from Box, a third-party host.

## 7. CMS Medicare opt-out affidavits

Publisher: Centers for Medicare & Medicaid Services (CMS), on data.cms.gov.

URLs read 2026-10-28:
- https://data.cms.gov/provider-characteristics/medicare-provider-supplier-enrollment/opt-out-affidavits ("Page last modified October 26, 2026"; latest data September 2026)
- https://data.cms.gov/data.json (DCAT-US v3 catalog; entry "Opt Out Affidavits : 2026-09-01")
- https://www.usa.gov/government-works (the catalog's license URL; redirects to https://www.usa.gov/government-copyright)

**No terms page.** data.cms.gov's footer links Contact, Get Email Updates, Site Map, Information Governance, Freedom of Information Act, No Fear Act, Privacy Policy and Vulnerability Disclosure Policy. None is a terms of use or license page. Nearest statements:

- Landing page: "Privacy level" is shown as "Public Use File (Free)".
- Catalog license, on each monthly distribution: `"license": "https://www.usa.gov/government-works"`. Across the whole catalog, every license value found is this URL (6,719 occurrences). The series-level record carries no license field.
- The page that URL leads to: "Text, images, and logos you see on federal websites may be subject to copyright or other restrictions. Learn the rules before using materials from government websites."
- Endorsement (usa.gov): "You cannot use government materials in a way that implies endorsement by a government agency, official, or employee."
- Privacy rights (usa.gov): "On federal websites, other people may have rights to the work itself or how people use it. This includes publicity or privacy rights under state law."
- Attribution (usa.gov): "In some cases, agencies will have specific language that they request you include with the materials they allow you to use." CMS's pages request none.
- Redistribution, commercial use, derived works: none stated by CMS.

Fee: free ("Public Use File (Free)"). Registration: none.

**Reading (not legal advice):** a free public-use file tagged as a U.S. government work. No CMS text limits redistribution, commercial use or derived works and none requires attribution. The general federal rules on usa.gov apply: do not imply CMS endorsement, and keep in mind that people named in the data may have state-law publicity or privacy rights.

## 8. CMS PECOS public provider enrollment

Publisher: CMS, on data.cms.gov. Dataset "Medicare Fee-For-Service Public Provider Enrollment".

URLs read 2026-10-28:
- https://data.cms.gov/provider-characteristics/medicare-provider-supplier-enrollment/medicare-fee-for-service-public-provider-enrollment ("Page last modified October 19, 2026"; latest data Q4 2026)
- https://data.cms.gov/data.json (entry "Medicare Fee-For-Service Public Provider Enrollment : 2026-10-01")
- https://www.usa.gov/government-copyright (as for source 7)

**No terms page.** The same site, footer and catalog as source 7. Nearest statements:

- Landing page: "Privacy level" is shown as "Public Use File (Free)".
- Catalog license, on the Q4 2026 distribution: `"license": "https://www.usa.gov/government-works"`.
- Redaction: "Information is redacted where necessary to protect Medicare provider privacy."
- Fitness for use: "They are not intended to be used as real time reporting as the data changes from day to day and the files are updated only on a quarterly basis."
- usa.gov endorsement, privacy-rights and attribution statements: as quoted under source 7.
- Redistribution, commercial use, derived works: none stated by CMS.

Fee: free ("Public Use File (Free)"). Registration: none.

**Reading (not legal advice):** the same as source 7: a free public-use federal work with no CMS-specific limits. CMS warns that the files are quarterly snapshots, not real-time.

## Open questions

1. **SAM.gov and D&B.** Does republishing the public exclusions extract, which still holds pre-2022-04-04 records, count as sharing D&B Open Data "in bulk"? If so, the name and address fields of those records need either removal or a different route. The terms give D&B's contact for permissible-use questions: datause_govt@dnb.com.
2. **Texas.** TMB asks for notice before publication and its footer says "All rights reserved". A notice to TMB naming the dataset and where it will appear would follow the policy and could settle which statement governs.
3. **Florida.** The terms (if any) shown at account sign-up were not read. Whoever holds the MQA account should record them.
4. **California.** The CA.gov Conditions of Use cover "this website"; the files are on Box. Whether DCA considers the Box files covered is not stated.
5. **CMS (opt-out, PECOS).** The only license statement is a metadata field in the catalog, not a page a user sees. It is consistent with the landing pages' "Public Use File (Free)".
6. **NPPES.** The download page was showing a maintenance notice on 2026-10-28; the next monthly file may be late.
