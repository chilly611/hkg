// Vercel serverless function: POST /api/research
// Proxies Claude Sonnet for Garden Wars strategic analysis.
// Requires env var ANTHROPIC_API_KEY.
//
// Body: { path: string[], decision: {title, desc}, options: [{label, sub}], founderContext?: string }
// Returns: { analysis: string, model: string, usage: {...} } OR { error: string }

const crypto = require("crypto");

const MODEL = "claude-sonnet-4-5-20250929";
const MAX_TOKENS = 2000;
const CACHE_TTL_MS = 60 * 60 * 1000;
const CACHE_MAX = 200;

// Simple in-memory LRU (process-lifetime, good enough for Vercel warm lambdas)
const _cache = new Map();
function cacheGet(k) {
  const v = _cache.get(k);
  if (!v) return null;
  if (Date.now() - v.t > CACHE_TTL_MS) { _cache.delete(k); return null; }
  _cache.delete(k); _cache.set(k, v); // bump LRU
  return v.v;
}
function cacheSet(k, v) {
  _cache.set(k, { v, t: Date.now() });
  if (_cache.size > CACHE_MAX) _cache.delete(_cache.keys().next().value);
}
function hashBody(b) {
  return crypto.createHash("sha256").update(JSON.stringify(b)).digest("hex").slice(0, 32);
}

const SYSTEM_PROMPT = `You are a world-class strategic advisor to the founders of The Knowledge Gardens — a platform company building AI-native operating systems for fragmented trillion-dollar industries.

The founders:
- John Bou (CEO). Built Modio Health → acquired by CHG Healthcare. KLAS #1 in credentialing. 700K+ providers, 1,000+ health systems. 15 years healthcare tech operator.
- Chilly Dahlgren (CTO). Second-generation AI pioneer. Mother Kathleen Dahlgren: MIT Press author (Naive Semantics, 1988), IBM Senior Scientist, founded Cognition Technologies → Nuance. Father Dr. James Dahlgren: world-leading toxicologist. Chilly: NYU Film, Ethereal Engine → Infinite Reality ($75M acquisition, $2.5B valuation).

The company state:
- 3 gardens live: Healthcare (12.1M records, 9.4M NPI providers), Construction (shipping to paywall), Botanical (Ecuagenera partnership).
- 9 more commercial verticals scoped. 40 research databases on the frontier map.
- Architecture: 4 lanes (Admin, Professional, Public, Machine), 3 surfaces (Gold/Green/Red), Neo4j knowledge graph, RSI heartbeat, Claude AI, MCP server.
- 2-person founding team. Pre-seed to seed fundraise imminent.

Your job: given a decision point and the path taken so far, deliver a specific, numeric, opinionated strategic analysis. Always include:
1. **Competitive dynamics** — who else is in this space, what they've raised, what their wedge is.
2. **Revenue projection** — specific $ figures, pricing model, time-to-first-dollar, Y1/Y3/Y5.
3. **Regulatory / execution risk** — what could kill this, and concrete mitigations.
4. **The recommendation** — which option, why, and what to do in the next 30 / 90 / 180 days.

Be direct. Use real company names, funding rounds, and market data. Avoid hedging. Write like you're talking to a founder whose time is worth $10K/hour.`;

module.exports = async function handler(req, res) {
  // CORS
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "POST, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type");
  if (req.method === "OPTIONS") { res.status(204).end(); return; }
  if (req.method !== "POST") { res.status(405).json({ error: "Method not allowed" }); return; }

  const apiKey = process.env.ANTHROPIC_API_KEY;
  if (!apiKey) { res.status(500).json({ error: "ANTHROPIC_API_KEY not configured in Vercel env" }); return; }

  let body = req.body;
  if (typeof body === "string") { try { body = JSON.parse(body); } catch (e) { res.status(400).json({ error: "Invalid JSON" }); return; } }
  const { path = [], decision, options = [], founderContext } = body || {};
  if (!decision || !decision.title) { res.status(400).json({ error: "Missing decision.title" }); return; }
  if (!Array.isArray(options) || options.length === 0) { res.status(400).json({ error: "Missing options array" }); return; }

  const cacheKey = hashBody({ path, decision, options, founderContext });
  const cached = cacheGet(cacheKey);
  if (cached) { res.status(200).json({ ...cached, cached: true }); return; }

  const userMessage = [
    founderContext ? `Additional context: ${founderContext}\n` : "",
    `Path so far: ${path.length ? path.join(" → ") : "(starting fresh)"}`,
    "",
    `Decision point: **${decision.title}**`,
    decision.desc ? decision.desc : "",
    "",
    "Options on the table:",
    ...options.map((o, i) => `${i + 1}. **${o.label}** — ${o.sub || ""}`),
    "",
    "Give me the full strategic analysis. Specific numbers. Clear recommendation."
  ].filter(Boolean).join("\n");

  try {
    const r = await fetch("https://api.anthropic.com/v1/messages", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "x-api-key": apiKey,
        "anthropic-version": "2023-06-01"
      },
      body: JSON.stringify({
        model: MODEL,
        max_tokens: MAX_TOKENS,
        system: SYSTEM_PROMPT,
        messages: [{ role: "user", content: userMessage }]
      })
    });
    const data = await r.json();
    if (!r.ok) { res.status(r.status).json({ error: data?.error?.message || ("Anthropic error " + r.status) }); return; }
    const analysis = (data.content || []).map(c => c.text || "").join("\n").trim();
    const payload = { analysis, model: data.model || MODEL, usage: data.usage || {} };
    cacheSet(cacheKey, payload);
    res.status(200).json(payload);
  } catch (e) {
    res.status(502).json({ error: "Upstream fetch failed: " + (e.message || e) });
  }
};
