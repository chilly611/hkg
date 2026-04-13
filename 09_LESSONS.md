# 09 · LESSONS — Mistakes We've Made and Rules We Enforce

**Purpose:** Every time we or a collaborator makes a mistake, add the pattern here with a rule for next time. Read at session start. Never repeat a mistake twice.

---

## Brand / design lessons (from OKG build)

### L-001 — The parchment background is sacred
Multiple prior sessions tried to make the Species Experience "cinematic" by using dark backgrounds, space themes, nebulae. All rejected. **Rule: Light parchment (#f5f0e8) on every public surface of the platform brand. Dark is never the answer. If a session is drifting cinematic-dark, stop and re-read `02_BRANDING.md`.**

### L-002 — Tabs, not scrolling
The Species Experience is a 4-tab interface (Photo / Blueprint / Intelligence / Compare). Not a scrolling cinematic essay. Prior sessions regressed to scroll-based cinematic sections. **Rule: Knowledge Gardens interfaces are tab-based unless the information genuinely benefits from vertical narrative (long-form articles, documentation). The Species Experience is a reference instrument, not a scroll essay.**

### L-003 — Read the golden reference first
Every new session risks reimagining the Species Experience from scratch. Every time it does, the result is a regression. **Rule: Before touching any OKG UI, read `species-experience-preview.html` (the golden reference) + this lessons file. Enhance; don't reimagine.**

### L-004 — Flat card layouts are a regression
The Species Experience is rich and interactive (tabs, sliders, SVG blueprints, radial Care Ring). Prior sessions regressed to flat card layouts. **Rule: Every species-level experience must include at least: (a) tabs, (b) a blueprint/schematic visual, (c) a comparative view, (d) an intelligence/data panel.**

### L-005 — Victorian engineering signature per surface
Every public surface needs at least one of: dimension-line annotation, hand-drawn botanical/mechanical flourish, gear/compass ornament, source-citation footer, graph visualization texture. If a surface has none, it has drifted from the brand. **Rule: Before shipping, count the Victorian engineering signatures. Less than one = not ready.**

---

## Platform / technical lessons

### L-006 — `output: "export"` is sacred
Removing Next.js static export mode once broke the entire orchids site with site-wide 404s. **Rule: `output: "export"` in `next.config.ts` is never removed. Any change to `next.config.ts` requires a deploy verification before committing to master.**

### L-007 — Morph animation architecture
`requestAnimationFrame` with direct `stroke-dashoffset` control and `getTotalLength()` is the correct approach (V21+) for the photo→blueprint morph. SVG `animateMotion` and CSS keyframe dasharray approaches were both rejected after trial. **Rule: Use the V21 rAF approach. Don't re-litigate this unless there's a concrete performance or compatibility reason.**

### L-008 — Foreground segmentation, not edge detection
For clean flower silhouette contours, Canny edge detection captures texture noise. **Rule: Use foreground/background segmentation approaches for silhouette extraction, not edge detection.**

### L-009 — Compass hover positioning
The universal compass hover must use `bottom:100%` with negative margin overlap, not absolute pixel offsets. JS `onmouseenter`/`onmouseleave` is more reliable than CSS `:hover` for this element. **Rule: Don't rewrite the compass hover behavior without understanding why the current approach exists.**

### L-010 — Filesystem tool discipline (Windows + Desktop Commander)
Never attempt Chrome-based filesystem workarounds. Desktop Commander is the correct tool for filesystem operations on Chilly's Windows machine. **Rule: For Windows filesystem work, Desktop Commander is the only correct tool.**

### L-011 — PowerShell multi-step commands
Use semicolons between commands in PowerShell, or wrap with `cmd /c "..."` for multi-step shell operations. **Rule: Know the shell you're running in before writing a command.**

### L-012 — `npx next build` timeout
Requires `timeout_ms:120000` minimum — default timeouts kill the build mid-run. **Rule: Any `next build` call gets a 120-second timeout.**

---

## Process / workflow lessons

### L-013 — One deliverable per session
Each working session produces exactly one deliverable file with a clear name, saved to the desktop folder, with `PROJECT_STATE.md` updated. Multi-deliverable sessions cause context bloat and half-finished work. **Rule: Scope each session to one deliverable unless explicitly multi-part.**

### L-014 — Read PROJECT_STATE.md first, every time
Every session, the very first action is reading `PROJECT_STATE.md` and the lessons file. Skipping this step causes repeated mistakes. **Rule: Session start = read state + lessons, always.**

### L-015 — Enhance, don't replace
When an approved file exists (the golden reference, the live production file), modify and extend. Never start from scratch. **Rule: Copy the existing approved file as the starting point. If you feel the urge to start fresh, that is the signal to stop and re-read the existing file.**

### L-016 — Build → push → verify, then next chunk
Work in small, deployable increments because context windows are limited and sessions get interrupted. **Rule: Fix one thing → build → git push → update state → prompt for next chunk.**

### L-017 — Match what's visible on Chilly's screen
When Chilly provides an annotated screenshot, the screenshot is the spec. Don't argue with what's visible. **Rule: If the description doesn't match what Chilly sees, Chilly's screen wins. Ask what they're seeing before proposing changes.**

---

## Strategic lessons (self-imposed from reading the case studies)

### L-018 — Dominate density before spreading
Every case study in `05_RESEARCH_NICHE_TO_EMPIRE.md` won by picking a niche so narrow it looked like a toy, then dominating it absolutely. **Rule: Before expanding any garden, confirm we are the undisputed #1 in our defined niche. Spreading early is how good companies die.**

### L-019 — The pattern is the product, not the gardens
Multi-vertical is a story for investors and a hiring plan. It is not a quarterly product plan. We ship one garden well, then the next, then the next. **Rule: Never ship two gardens in parallel unless the pattern is fully productized and each can be delivered by a separate team.**

### L-020 — RSI heartbeat is non-negotiable
Every garden must have a defined recursive self-improvement heartbeat at scoping time. Snapshots die; compounding systems don't. **Rule: No garden scoping document is approved without an RSI heartbeat definition.**

### L-021 — Beauty is an economic moat
In a world where AI can generate infinite mediocre content, craft is a moat. MLPs over MVPs. Every pixel is a trust signal. **Rule: Before shipping any public surface, ask "would a Royal Botanic Gardens curator AND a Stripe staff engineer both respect this?" If no, back to the drawing board.**

### L-022 — Gravity over promotion
If users would shrug when a tool disappeared, it's marketing, not gravity. **Rule: Every Gravity Well tool must pass the "would users be upset if this vanished?" test before it ships.**

### L-023 — The commercial gardens fund the meaning gardens
No Frontier 40 garden is built before HKG and BKG are generating real MRR. The meaning gardens (Extinction, Sound, Mind, Fossil) are what the team and the brand need, but they cannot come before the cash engines are running. **Rule: Commercial gardens first, always. Meaning gardens are dessert.**

---

## How to add a lesson

When something goes wrong, append here in this format:

```
### L-NNN — [One-line pattern name]
[1–3 sentence description of what happened.] **Rule: [Concrete, enforceable rule for next time, written as a command.]**
```

If the same lesson appears twice, that's a process failure. The goal of this file is that L-NNN never happens a second time.
