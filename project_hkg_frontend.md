---
name: HKG Frontend Architecture
description: Healthcare Knowledge Garden single-page React 18 app — card-based data explorer, SVG relationship maps, 4 lanes, deployed to health.theknowledgegardens.com via GitHub Pages
type: project
---

The HKG frontend is a single HTML file (`index.html` in `chilly611/hkg` repo) deployed to GitHub Pages at `health.theknowledgegardens.com`.

**Stack:** React 18.2.0 UMD production builds from cdnjs. Zero JSX, zero Babel — all code uses `React.createElement()` aliased as `h`. Single-file architecture, no build step.

**CDN paths (MUST use `/umd/` segment):**
- `https://cdnjs.cloudflare.com/ajax/libs/react/18.2.0/umd/react.production.min.js`
- `https://cdnjs.cloudflare.com/ajax/libs/react-dom/18.2.0/umd/react-dom.production.min.js`

**Key components:**
- **Landing/ScaleDashboard** — Shows all 10 federal data source tables with live counts from Supabase HEAD requests, relationship multiplier panel showing how connections scale
- **4 Lanes** — Clinician, Patient, Operations, Explorer — each with search + card results + SVG relationship map
- **BrowseTable** — Paginated data browser (20 rows/page, prev/next) across 7 tables with tab switching
- **RelationshipMap** — SVG circular node layout with bezier edge curves showing entity relationships
- **Search** — Debounced 250ms queries across 7 tables with PostgREST `ilike` filtering

**View modes:** "Cards + Map", "Relationship Map", "Browse Data"

**Visual design:** Dark theme, glassmorphism, hex logo (`assets/hex-logo-200.png`), CSS animations (fadeSlideUp, logoFloat, livePulse, rotateBg), ambient glow effects.

**Assets in repo (`assets/` directory):**
- hex-logo-full.png, hex-logo-200.png, hex-logo-64.png (brand hex logos)
- tree-hero.png, tree-300.png (tree with roots imagery)
- heart-hero.png (orchid root heart)
- og-image-new.png (1200x630 OG social image)

**Deployment:**
- GitHub Pages from `chilly611/hkg` repo, main branch
- CNAME file contains `health.theknowledgegardens.com`
- Deploy via: `gh api repos/chilly611/hkg/contents/index.html -X PUT` with base64 content
- GitHub Pages shows `status: "errored"` transiently for 15-30s after deploy — recheck and it becomes `"built"`

**Why:** This is the primary investor demo for HKG, showing the scale and depth of healthcare data relationships.
**How to apply:** When modifying, maintain the single-file UMD architecture. Always test Supabase queries with curl first before putting them in code. The canvas force-directed graph was abandoned — use SVG/HTML cards instead.
