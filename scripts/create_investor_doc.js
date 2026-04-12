#!/usr/bin/env node

/**
 * HKG Investor Briefing Document Generator
 * Creates a professional Word document for seed-stage fundraising
 * Output: HKG_Investor_Briefing_Apr2026.docx
 */

const { Document, Packer, PageBreak, Paragraph, Table, TableCell, TableRow, TextRun, ShadingType, BorderStyle, VerticalAlign, AlignmentType, HeadingLevel, PageOrientation, UnderlineType, WidthType, LevelFormat, convertInchesToTwip } = require('docx');
const fs = require('fs');
const path = require('path');

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

/**
 * Create a styled title paragraph
 */
function titleParagraph(text, centered = true) {
  return new Paragraph({
    text,
    style: 'Heading1',
    size: 72,
    bold: true,
    alignment: centered ? AlignmentType.CENTER : AlignmentType.LEFT,
    spacing: { line: 360, before: 240, after: 120 },
  });
}

/**
 * Create a heading 1 (24pt bold)
 */
function heading1(text) {
  return new Paragraph({
    text,
    heading: HeadingLevel.HEADING_1,
    style: 'Heading1',
    size: 48,
    bold: true,
    alignment: AlignmentType.LEFT,
    spacing: { before: 240, after: 120, line: 360 },
  });
}

/**
 * Create a heading 2 (18pt bold)
 */
function heading2(text) {
  return new Paragraph({
    text,
    heading: HeadingLevel.HEADING_2,
    style: 'Heading2',
    size: 36,
    bold: true,
    alignment: AlignmentType.LEFT,
    spacing: { before: 180, after: 100, line: 360 },
  });
}

/**
 * Create a body paragraph (11pt)
 */
function bodyParagraph(text, spacing = { before: 0, after: 120, line: 240 }) {
  return new Paragraph({
    text,
    size: 22,
    alignment: AlignmentType.LEFT,
    spacing,
  });
}

/**
 * Create a bullet point
 */
function bullet(text, level = 0) {
  return new Paragraph({
    text,
    size: 22,
    bullet: {
      level,
    },
    spacing: { before: 60, after: 60, line: 240 },
  });
}

/**
 * Create a table row with styling
 */
function tableRow(cells, isHeader = false, shading = false) {
  const rows = cells.map((cellText, idx) => {
    return new TableCell({
      children: [
        new Paragraph({
          text: cellText,
          bold: isHeader,
          size: 22,
          alignment: AlignmentType.CENTER,
        }),
      ],
      shading: isHeader || shading ? { type: ShadingType.CLEAR, color: 'E7E6E6' } : undefined,
      verticalAlign: VerticalAlign.CENTER,
      margins: { top: 80, bottom: 80, left: 80, right: 80 },
    });
  });

  return new TableRow({
    children: rows,
  });
}

/**
 * Create a professional table
 */
function createTable(headers, rows, columnWidths = null) {
  const numCols = headers.length;
  const defaultWidth = 9144; // DXA for roughly equal columns

  const headerRow = tableRow(headers, true);

  const dataRows = rows.map((row) =>
    tableRow(Array.isArray(row) ? row : row.cells, false, row.shaded || false)
  );

  const allRows = [headerRow, ...dataRows];

  return new Table({
    width: { size: 100, type: WidthType.PERCENTAGE },
    rows: allRows,
    borders: {
      top: { style: BorderStyle.SINGLE, size: 6, color: '000000' },
      bottom: { style: BorderStyle.SINGLE, size: 6, color: '000000' },
      left: { style: BorderStyle.SINGLE, size: 6, color: '000000' },
      right: { style: BorderStyle.SINGLE, size: 6, color: '000000' },
      insideHorizontal: { style: BorderStyle.SINGLE, size: 6, color: 'CCCCCC' },
      insideVertical: { style: BorderStyle.SINGLE, size: 6, color: 'CCCCCC' },
    },
  });
}

// ============================================================================
// SECTION BUILDERS
// ============================================================================

function coverPage() {
  return [
    new Paragraph({
      text: '',
      spacing: { before: 800 },
    }),
    new Paragraph({
      text: 'HEALTHCARE KNOWLEDGE GARDEN',
      size: 72,
      bold: true,
      alignment: AlignmentType.CENTER,
      spacing: { before: 400, after: 200, line: 360 },
    }),
    new Paragraph({
      text: 'The Operating System for the $12 Trillion Global Healthcare Ecosystem',
      size: 36,
      alignment: AlignmentType.CENTER,
      spacing: { before: 0, after: 400, line: 300 },
    }),
    new Paragraph({
      text: '',
      spacing: { before: 400 },
    }),
    new Paragraph({
      text: 'Investor Briefing — April 2026',
      size: 24,
      alignment: AlignmentType.CENTER,
      italic: true,
      spacing: { before: 0, after: 40 },
    }),
    new Paragraph({
      text: 'Confidential',
      size: 24,
      alignment: AlignmentType.CENTER,
      italic: true,
      spacing: { before: 0, after: 600 },
    }),
    new Paragraph({
      text: '',
      spacing: { before: 600 },
    }),
    new Paragraph({
      text: "Charles 'Chilly' Dahlgren",
      size: 24,
      bold: true,
      alignment: AlignmentType.CENTER,
      spacing: { before: 0, after: 60 },
    }),
    new Paragraph({
      text: 'Co-Founder & CTO',
      size: 22,
      alignment: AlignmentType.CENTER,
      spacing: { before: 0, after: 120 },
    }),
    new Paragraph({
      text: 'John Bou',
      size: 24,
      bold: true,
      alignment: AlignmentType.CENTER,
      spacing: { before: 0, after: 60 },
    }),
    new Paragraph({
      text: 'Co-Founder & CEO',
      size: 22,
      alignment: AlignmentType.CENTER,
      spacing: { before: 0, after: 600 },
    }),
    new Paragraph({
      text: '',
      spacing: { before: 600 },
    }),
    new Paragraph({
      text: 'The Knowledge Gardens',
      size: 22,
      alignment: AlignmentType.CENTER,
      spacing: { before: 0, after: 40 },
    }),
    new Paragraph({
      text: 'XRWorkers',
      size: 22,
      alignment: AlignmentType.CENTER,
      spacing: { before: 0, after: 0 },
    }),
    new PageBreak(),
  ];
}

function tableOfContents() {
  return [
    heading1('Table of Contents'),
    bullet('Executive Summary', 0),
    bullet('The Problem', 0),
    bullet('The Solution — Four Lanes, One Brain', 0),
    bullet('Market Opportunity', 0),
    bullet('Business Model & Revenue', 0),
    bullet('Traction & Product', 0),
    bullet('Technology & Architecture', 0),
    bullet('Competitive Landscape', 0),
    bullet('The Platform Pattern', 0),
    bullet('Go-to-Market', 0),
    bullet('The Team', 0),
    bullet('Financial Projections', 0),
    bullet('The Ask', 0),
    bullet('The Path to $1 Trillion', 0),
    new PageBreak(),
  ];
}

function executiveSummary() {
  return [
    heading1('1. Executive Summary'),
    bodyParagraph(
      'The Healthcare Knowledge Garden is an AI-native operating system connecting every participant in the $12 trillion global healthcare ecosystem through a unified knowledge graph. Four lanes serve administrators, clinicians, patients, and AI agents. Built on proven architecture deployed across two prior verticals (construction $17 trillion, botanical $100 billion+). 12.1 million+ records from 13 federal sources already loaded and live at health.theknowledgegardens.com.'
    ),
    bodyParagraph(
      'Key metrics: 9.4 million providers (full NPI registry), 140,000 adverse events, 98,000 diagnosis codes, 83,000 drug codes, 34,000 clinical trials, 60,000 PubMed citations. Provider Verification Engine and Drug Interaction Checker live. Machine Lane (llms.txt, JSON-LD) deployed.'
    ),
    bodyParagraph('Seeking $5–8 million seed at $25–40 million post-money valuation.'),
    new PageBreak(),
  ];
}

function theProblem() {
  return [
    heading1('2. The Problem'),
    heading2('The 9-Month Nightmare'),
    bodyParagraph('Hospital credentialing takes 120+ days using Excel spreadsheets and fragmented databases.'),
    heading2('The ChatGPT Liability Trap'),
    bodyParagraph('Doctors risk malpractice using unverified LLMs during patient appointments.'),
    heading2('The Non-Human Data Void'),
    bodyParagraph('AI agents lack a legally defensible, structured data layer for medical knowledge.'),
    heading2('The Fragmentation Reality'),
    bodyParagraph('$12 trillion industry running on a fragmented toolbelt: disparate EHRs, legacy credentialing systems, unlinked clinical databases, no native integration for AI agents.'),
    new PageBreak(),
  ];
}

function theSolution() {
  return [
    heading1('3. The Solution — Four Lanes, One Brain'),
    heading2('Administrator Lane (Red Surface)'),
    bodyParagraph(
      'Credentialing verification engine. Input NPI → instant cross-reference against OIG exclusions, state medical boards, DEA registrations, Medicare sanctions. Eliminates 90% of credentialing friction. Real-time 6-table verification with audit trail.'
    ),
    heading2('Doctor Lane (Green Surface)'),
    bodyParagraph(
      '3-Point Verification Shield. Every clinical claim cross-checked against (1) peer-reviewed literature via PubMed, (2) clinical practice guidelines, (3) regulatory/FDA databases. Life-extending knowledge physicians can trust during patient appointments.'
    ),
    heading2('Patient Lane (Gold Surface)'),
    bodyParagraph(
      'The Gravity Well. Free drug interaction checker, provider search, condition explorer, clinical trial finder. Democratizing access to biotech protocols, longevity science, and evidence-based medicine. Free tier pulls the entire ecosystem in.'
    ),
    heading2('Machine Lane (Purple Surface)'),
    bodyParagraph(
      'MCP server + llms.txt + JSON-LD. The "USB-C for AI." Every AI agent on Earth can natively query and cite HKG data. Recursive Self-Improvement (RSI) heartbeat ensures daily auto-ingestion of latest knowledge from 13 federal sources.'
    ),
    new PageBreak(),
  ];
}

function marketOpportunity() {
  return [
    heading1('4. Market Opportunity'),
    createTable(
      ['Market Segment', 'Total Addressable Market', 'Growth Rate'],
      [
        ['US Healthcare Spending (annual)', '$4.5 trillion', '3–5% CAGR'],
        ['Global Healthcare Spending', '$12+ trillion', '5–7% CAGR'],
        ['Healthcare Credentialing Market', '$2.3 billion', '8–10% CAGR'],
        ['Clinical Decision Support', '$1.8 billion', '12–15% CAGR'],
        ['Healthcare AI (projected 2030)', '$45 billion', '25%+ CAGR'],
        ['Healthcare IT Market', '$400+ billion', '15% CAGR'],
      ]
    ),
    bodyParagraph('HKG addresses all six segments simultaneously through the unified platform.'),
    new PageBreak(),
  ];
}

function businessModel() {
  return [
    heading1('5. Business Model & Revenue'),
    heading2('Four Revenue Streams'),
    createTable(
      ['Lane', 'Product', 'Revenue Model', 'Target Annual Revenue per Customer'],
      [
        ['Admin (Red)', 'Credentialing Engine', '$0.50–$2 per verification + $15–50/provider/mo + enterprise licenses', '$50K–$150K/yr'],
        ['Doctor (Green)', 'CME Marketplace + Credential Portfolios', '15–25% marketplace take + recruiter fees + premium tier', '$20K–$80K/yr'],
        ['Patient (Gold)', 'Free tier → Premium conversion + telehealth partnerships', 'Freemium conversion (5–10%), partnership revenue share', '$2–5M/yr at scale'],
        ['Machine (Purple)', 'MCP API + Enterprise feeds', 'Tiered API: $99–$2,499/mo + enterprise $50K–$500K/yr', '$100K–$500K/yr'],
      ]
    ),
    bodyParagraph('Blended unit economics: Free gravity well (patients) drives Admin/Doctor adoption (providers), which enables high-margin Machine lane (AI agents + enterprises).'),
    new PageBreak(),
  ];
}

function tractionProduct() {
  return [
    heading1('6. Traction & Product'),
    heading2('Platform Status: LIVE'),
    bullet('URL: health.theknowledgegardens.com', 0),
    bullet('Framework: Single-file React 18 app (zero build step)', 0),
    bullet('Backend: Supabase PostgreSQL with 28-table schema', 0),
    heading2('Data: 12.1M+ Records Loaded'),
    createTable(
      ['Data Category', 'Record Count', 'Source'],
      [
        ['Providers (NPI)', '9.4 million', 'NPPES NPI Registry (complete)'],
        ['Provider Addresses', '1.1 million', 'NPPES (bulk extraction)'],
        ['Provider Taxonomies', '778K', 'NPPES (bulk extraction)'],
        ['Adverse Events', '139K', 'FDA FAERS openFDA API'],
        ['Clinical Trials', '33K', 'ClinicalTrials.gov API v2'],
        ['Diagnosis Codes (ICD-10-CM)', '97K', 'CMS FY2025'],
        ['Drug Codes (NDC)', '82K', 'FDA openFDA'],
        ['Drug Interactions', '5.5K', 'RxNorm-linked'],
        ['PubMed Citations', '59K', 'NCBI E-Utilities'],
        ['Medicare Part D Prescribers', '70K', 'CMS Medicare Part D'],
        ['OIG Exclusions', '82K', 'HHS-OIG LEIE (Mar 2026)'],
      ]
    ),
    heading2('Live Features'),
    bullet('Provider Verification Engine: Real-time 6-table cross-reference (NPI → OIG/state boards/DEA)', 0),
    bullet('Drug Interaction Checker: 5,500 interactions + 140K adverse events', 0),
    bullet('Knowledge Graph Visualization: Force-directed canvas with entity detail drilling', 0),
    bullet('Federated Search: 13 data types, categorized dropdown, entity detail', 0),
    bullet('Machine Lane: llms.txt + robots.txt welcoming AI crawlers', 0),
    new PageBreak(),
  ];
}

function technology() {
  return [
    heading1('7. Technology & Architecture'),
    heading2('Frontend Stack'),
    bullet('React 18 (UMD build, zero build step)', 0),
    bullet('Force-directed knowledge graph (D3.js)', 0),
    bullet('Real-time search with Fuse.js', 0),
    bullet('Tailwind CSS + custom particle canvas background', 0),
    heading2('Backend Stack'),
    bullet('Supabase PostgreSQL: 28-table schema with RLS, triggers, GIN indexes', 0),
    bullet('PostgREST API: Direct browser queries (service_role key, RLS policies)', 0),
    bullet('Neo4j Knowledge Graph (planned): Relationship modeling for care pathways, credential chains', 0),
    heading2('AI & Intelligence'),
    bullet('Claude API: Morning Briefings, 3-Point Verification, RSI prompts', 0),
    bullet('MCP (Model Context Protocol): Native AI agent integration', 0),
    bullet('RSI Heartbeat: Recursive self-improvement with daily auto-ingestion from 13 federal sources', 0),
    heading2('Deployment & Scale'),
    bullet('GitHub Pages: health.theknowledgegardens.com', 0),
    bullet('Infrastructure: Zero-ops frontend, Supabase-managed backend', 0),
    bullet('Data Ingestion: Python scripts with stdlib only (no dependencies)', 0),
    new PageBreak(),
  ];
}

function competitive() {
  return [
    heading1('8. Competitive Landscape'),
    createTable(
      ['Competitor', 'Market Cap / Valuation', 'Focus', 'HKG Advantage'],
      [
        ['Open Evidence', '$1.2B', 'Doctors only (clinical decision support)', 'All 4 lanes + unified knowledge graph'],
        ['Doximity', '$6.5B', 'LinkedIn for doctors', 'Knowledge-first, not social'],
        ['Veeva Systems', '$35B', 'CRM for pharma only', 'Horizontal (all healthcare participants)'],
        ['MedV', '$1.6B exit (GLP-1 telehealth)', 'Telehealth only', 'Underlying knowledge layer (not just apps)'],
        ['Epic / Cerner', '$100B+ (estimated)', 'EHR incumbents', 'AI-native, interoperable, open data'],
      ]
    ),
    bodyParagraph('HKG is the data layer — the infrastructure on which all other healthcare AI is built.'),
    new PageBreak(),
  ];
}

function platformPattern() {
  return [
    heading1('9. The Platform Pattern'),
    heading2('"We Do Not Build Products. We Build the Pattern That Builds Products."'),
    bodyParagraph(
      'HKG is the third deployment of a proven architecture. Two verticals deployed at scale, four more scoped, nine more identified. Each vertical follows the same 4-lane, 3-surface, AI-native design.'
    ),
    heading2('Vertical Deployments'),
    createTable(
      ['Vertical', 'TAM', 'Status', 'Revenue', 'Partner'],
      [
        ['BKG (Construction)', '$17 trillion', 'LIVE', 'Growing', 'In discussion'],
        ['OKG (Botanical)', '$100 billion+', 'DEPLOYED', '$250K ARR', 'Ecuagenera partnership'],
        ['HKG (Healthcare)', '$12 trillion', 'BUILDING', '$1M target Y1', 'John Bou (Modio founder)'],
      ]
    ),
    heading2('9 More Verticals Identified'),
    bullet('Legal ($1.3T)', 0),
    bullet('Education ($1.8T)', 0),
    bullet('Finance ($100T+ assets under management)', 0),
    bullet('Agriculture ($1.3T)', 0),
    bullet('Energy ($2T+)', 0),
    bullet('Real Estate ($60T)', 0),
    bullet('Pharma (subset of healthcare)', 0),
    bullet('Insurance (subset of healthcare)', 0),
    bullet('Government ($8T spending)', 0),
    heading2('Platform Scale (All Verticals)'),
    createTable(
      ['Year', 'All Verticals ARR', 'HKG-Only ARR'],
      [
        ['Year 1', '$1.7M', '$1M'],
        ['Year 2', '$9M', '$5M'],
        ['Year 3', '$58M', '$25M'],
        ['Year 4', '$228M', '$80M'],
        ['Year 5', '$710M', '$200M'],
      ]
    ),
    new PageBreak(),
  ];
}

function goToMarket() {
  return [
    heading1('10. Go-to-Market'),
    heading2('Patient Gravity Well (Months 1–10)'),
    bullet('Free drug interaction checker, provider search, clinical trial finder', 0),
    bullet('Target: 500,000 monthly visitors by Month 10', 0),
    bullet('Drives organic awareness and provider credibility (network effects)', 0),
    heading2('AI Agent Discovery (Months 6–12)'),
    bullet('llms.txt + JSON-LD → AI citations at scale', 0),
    bullet('Every major AI model (Claude, GPT, Gemini) can cite HKG data natively', 0),
    bullet('Target: AI citation share tracking by Month 12', 0),
    heading2('Enterprise Sales (Months 3–12)'),
    bullet('John Bou\'s healthcare network: 1,000+ health systems, 700K+ managed providers', 0),
    bullet('Admin Lane sales: Credentialing engines, provider lifecycle management', 0),
    bullet('Target: 500+ enterprise customers by Month 12', 0),
    heading2('Press & Thought Leadership'),
    bullet('What My Mother Taught Me About AI - Chilly\'s mother (Kathleen Dahlgren, IBM, UCLA, MIT Press)', 0),
    bullet('Knowledge Garden pattern narrative — the horizontal platform play', 0),
    heading2('Developer Community'),
    bullet('Open Machine Lane API → 100+ API consumers by Month 9', 0),
    bullet('MCP server as industry standard for healthcare AI agents', 0),
    new PageBreak(),
  ];
}

function theTeam() {
  return [
    heading1('11. The Team'),
    heading2('Charles Chilly Dahlgren — Co-Founder & CTO'),
    bullet('Second-generation AI pioneer. Mother: Kathleen Dahlgren, IBM Senior Scientist, UCLA professor, MIT Press author of Naive Semantics for Natural Language Understanding', 0),
    bullet('NYU Film School, worked with Alex Kurtzman / Roberto Orci (Star Trek, Transformers)', 0),
    bullet('Won Magic Leap × Verizon 5G hackathon', 0),
    bullet('Ethereal Engine: Acquired by Infinite Reality, $75 million acquisition, $2.5 billion valuation', 0),
    bullet('Architected and deployed Knowledge Garden pattern across 3 verticals (BKG, OKG, HKG)', 0),
    heading2('John Bou — Co-Founder & CEO'),
    bullet('Co-founded Modio Health (2014), built to KLAS #1 credentialing platform (91/100 rating)', 0),
    bullet('Modio acquired by CHG Healthcare (2019)', 0),
    bullet('Currently President at CHG, managing 700,000+ providers for ~1,000 healthcare organizations', 0),
    bullet('15+ years healthcare IT experience', 0),
    bullet('Built and sold the market leader — now building the AI-native successor', 0),
    new PageBreak(),
  ];
}

function financialProjections() {
  return [
    heading1('12. Financial Projections'),
    heading2('HKG-Only Revenue (5-Year Roadmap)'),
    createTable(
      ['Year', 'Admin Lane', 'Doctor Lane', 'Patient Lane', 'Machine Lane', 'Total ARR'],
      [
        ['Year 1', '$100K', '$50K', '$250K', '$600K', '$1M'],
        ['Year 2', '$800K', '$400K', '$1.5M', '$2.3M', '$5M'],
        ['Year 3', '$6M', '$3M', '$8M', '$8M', '$25M'],
        ['Year 4', '$20M', '$15M', '$25M', '$20M', '$80M'],
        ['Year 5', '$60M', '$50M', '$60M', '$30M', '$200M'],
      ]
    ),
    heading2('All Verticals Combined (5-Year Roadmap)'),
    createTable(
      ['Year', 'Total ARR', 'Growth'],
      [
        ['Year 1', '$1.7M', 'N/A'],
        ['Year 2', '$9M', '429%'],
        ['Year 3', '$58M', '544%'],
        ['Year 4', '$228M', '293%'],
        ['Year 5', '$710M', '211%'],
      ]
    ),
    bodyParagraph('Assumptions: 3–4 new verticals in production by Year 3. Admin lane CLV: $200K–$500K. Machine lane becomes dominant revenue stream (50%+ by Year 5).'),
    new PageBreak(),
  ];
}

function theAsk() {
  return [
    heading1('13. The Ask'),
    heading2('Seed Round: $5–8 Million'),
    heading2('Valuation: $25–40 Million Post-Money'),
    heading2('Use of Funds'),
    createTable(
      ['Category', 'Amount', 'Purpose'],
      [
        ['Engineering', '$2M', 'VP Engineering hire, team expansion (3 senior engineers)'],
        ['Product & Admin Lane', '$1.5M', 'Complete Admin Lane MLP, go-to-market for enterprise'],
        ['Data & Machine Lane', '$1M', 'Complete LOINC load (108K), SAM.gov integration, API tier deployment'],
        ['Operations & BKG Revenue', '$0.8M', 'Operations team, close BKG revenue deals, platform operations'],
        ['New Verticals', '$0.7M', 'Scope and design Legal and Education verticals'],
      ]
    ),
    heading2('Priority Investors'),
    bullet('a16z Bio + AI (healthcare + AI thesis)', 0),
    bullet('General Catalyst (health fund + platform plays)', 0),
    bullet('Founders Fund (infrastructure + moonshots)', 0),
    bullet('Oak HC/FT (healthcare technology)', 0),
    bullet('Transformation Capital (data-first healthcare)', 0),
    bullet('SignalFire (knowledge graphs + AI)', 0),
    heading2('Strategic Investors'),
    bullet('Google Ventures (healthcare AI)', 0),
    bullet('Salesforce Ventures (platform CRM)', 0),
    bullet('Microsoft M12 (healthcare + cloud)', 0),
    new PageBreak(),
  ];
}

function pathToTrillionDollars() {
  return [
    heading1('14. The Path to $1 Trillion'),
    heading2('$1 Billion (Year 3)'),
    bodyParagraph('US healthcare dominance. 10,000+ enterprise customers. HKG recognized as the knowledge layer beneath all clinical AI.'),
    heading2('$10 Billion (Year 5)'),
    bodyParagraph('Multi-vertical scale (3–4 verticals at $100M+ ARR each). International expansion (EU, APAC, China).'),
    heading2('$100 Billion (Year 8)'),
    bodyParagraph('The data layer. Every EHR, insurance platform, pharma R&D pipeline, government health ministry connects to HKG as the reference knowledge graph.'),
    heading2('$1 Trillion (Year 12+)'),
    bodyParagraph('Invisible infrastructure. What Visa is to payments, Knowledge Gardens is to industry knowledge. Used by 1+ billion people daily.'),
    new PageBreak(),
  ];
}

// ============================================================================
// DOCUMENT ASSEMBLY
// ============================================================================

const doc = new Document({
  sections: [
    {
      properties: {
        page: {
          margins: {
            top: convertInchesToTwip(1),
            right: convertInchesToTwip(1),
            bottom: convertInchesToTwip(1),
            left: convertInchesToTwip(1),
          },
          size: {
            width: 12240,
            height: 15840,
          },
        },
        headers: {
          default: {
            children: [
              new Paragraph({
                text: 'Healthcare Knowledge Garden',
                size: 20,
                alignment: AlignmentType.LEFT,
              }),
              new Table({
                width: { size: 100, type: WidthType.PERCENTAGE },
                rows: [
                  new TableRow({
                    children: [
                      new TableCell({
                        children: [
                          new Paragraph({
                            text: 'Healthcare Knowledge Garden',
                            size: 20,
                          }),
                        ],
                        borders: {
                          bottom: { style: BorderStyle.NONE },
                          top: { style: BorderStyle.NONE },
                          left: { style: BorderStyle.NONE },
                          right: { style: BorderStyle.NONE },
                        },
                      }),
                      new TableCell({
                        children: [
                          new Paragraph({
                            text: 'CONFIDENTIAL',
                            size: 20,
                            alignment: AlignmentType.RIGHT,
                          }),
                        ],
                        borders: {
                          bottom: { style: BorderStyle.NONE },
                          top: { style: BorderStyle.NONE },
                          left: { style: BorderStyle.NONE },
                          right: { style: BorderStyle.NONE },
                        },
                      }),
                    ],
                  }),
                ],
              }),
            ],
          },
        },
        footers: {
          default: {
            children: [
              new Paragraph({
                text: '',
                border: {
                  top: { color: '000000', space: 1, style: BorderStyle.SINGLE, size: 6 },
                },
              }),
              new Paragraph({
                children: [
                  new TextRun({
                    text: 'Page ',
                  }),
                  new TextRun({
                    fieldCodes: 'PAGE',
                  }),
                ],
                alignment: AlignmentType.CENTER,
                size: 22,
              }),
            ],
          },
        },
      },
      children: [
        ...coverPage(),
        ...tableOfContents(),
        ...executiveSummary(),
        ...theProblem(),
        ...theSolution(),
        ...marketOpportunity(),
        ...businessModel(),
        ...tractionProduct(),
        ...technology(),
        ...competitive(),
        ...platformPattern(),
        ...goToMarket(),
        ...theTeam(),
        ...financialProjections(),
        ...theAsk(),
        ...pathToTrillionDollars(),
      ],
    },
  ],
});

// ============================================================================
// WRITE FILE
// ============================================================================

Packer.toBuffer(doc).then((buffer) => {
  const outputPath = path.join(
    __dirname,
    '..',
    'HKG_Investor_Briefing_Apr2026.docx'
  );

  fs.writeFileSync(outputPath, buffer);
  console.log(`✓ Document created: ${outputPath}`);
  console.log(`✓ File size: ${(buffer.length / 1024 / 1024).toFixed(2)} MB`);
  console.log('✓ Ready for distribution to investors');
});
