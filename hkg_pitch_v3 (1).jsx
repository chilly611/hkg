import { useState, useEffect, useRef } from "react";

const GOLD = "#D4A853";
const GREEN = "#34D399";
const RED = "#EF4444";
const AMETHYST = "#A78BFA";
const ORANGE = "#F97316";
const BG = "#06060B";
const BG_CARD = "rgba(13,13,20,0.85)";

function useCounter(end, dur = 2200, trigger = false) {
  const [c, setC] = useState(0);
  useEffect(() => { if (!trigger) return; let s = 0; const step = end / (dur / 16); const t = setInterval(() => { s += step; if (s >= end) { setC(end); clearInterval(t); } else setC(Math.floor(s)); }, 16); return () => clearInterval(t); }, [trigger, end, dur]);
  return c;
}
function useInView(th = 0.15) {
  const ref = useRef(null); const [v, setV] = useState(false);
  useEffect(() => { const el = ref.current; if (!el) return; const o = new IntersectionObserver(([e]) => { if (e.isIntersecting) setV(true); }, { threshold: th }); o.observe(el); return () => o.disconnect(); }, [th]);
  return [ref, v];
}
function useScrollProgress() {
  const [p, setP] = useState(0);
  useEffect(() => { const f = () => { const h = document.documentElement.scrollHeight - window.innerHeight; setP(h > 0 ? window.scrollY / h : 0); }; window.addEventListener("scroll", f, { passive: true }); return () => window.removeEventListener("scroll", f); }, []);
  return p;
}
function LiveCounter() {
  const [c, setC] = useState(10247831);
  useEffect(() => { const t = setInterval(() => { setC(v => v + Math.floor(Math.random() * 4) + 1); }, 600); return () => clearInterval(t); }, []);
  return c.toLocaleString();
}
function MorphWords({ words, color = GOLD, interval = 2800 }) {
  const [idx, setIdx] = useState(0); const [fade, setFade] = useState(true);
  useEffect(() => { const t = setInterval(() => { setFade(false); setTimeout(() => { setIdx(i => (i + 1) % words.length); setFade(true); }, 400); }, interval); return () => clearInterval(t); }, [words.length, interval]);
  return <span style={{ color, display: "inline-block", minWidth: "3ch", opacity: fade ? 1 : 0, transform: fade ? "translateY(0)" : "translateY(12px)", transition: "all .4s cubic-bezier(.22,1,.36,1)", fontStyle: "italic" }}>{words[idx]}</span>;
}
function CountUp({ end, duration = 2000 }) {
  const [c, setC] = useState(0); const ref = useRef(null); const [go, setGo] = useState(false);
  useEffect(() => { const el = ref.current; if (!el) return; const o = new IntersectionObserver(([e]) => { if (e.isIntersecting) setGo(true); }, { threshold: .1 }); o.observe(el); return () => o.disconnect(); }, []);
  useEffect(() => { if (!go) return; let s = 0; const step = end / (duration / 16); const t = setInterval(() => { s += step; if (s >= end) { setC(end); clearInterval(t); } else setC(Math.floor(s)); }, 16); return () => clearInterval(t); }, [go, end, duration]);
  return <span ref={ref}>{c.toLocaleString()}</span>;
}

function GraphBackground() {
  const canvasRef = useRef(null); const nodesRef = useRef([]); const animRef = useRef(null); const mouseRef = useRef({ x: -1e3, y: -1e3 });
  useEffect(() => {
    const canvas = canvasRef.current; if (!canvas) return; const ctx = canvas.getContext("2d"); let w, h;
    const resize = () => { w = canvas.width = window.innerWidth; h = canvas.height = window.innerHeight; }; resize(); window.addEventListener("resize", resize);
    const onMouse = (e) => { mouseRef.current = { x: e.clientX, y: e.clientY }; }; window.addEventListener("mousemove", onMouse, { passive: true });
    const colors = [GOLD, GREEN, AMETHYST, ORANGE, "#ffffff"];
    if (!nodesRef.current.length) { for (let i = 0; i < 80; i++) nodesRef.current.push({ x: Math.random() * 3000, y: Math.random() * 12000, vx: (Math.random() - .5) * .35, vy: (Math.random() - .5) * .35, r: Math.random() * 2.5 + .5, color: colors[Math.floor(Math.random() * colors.length)], opacity: Math.random() * .3 + .06 }); }
    const nodes = nodesRef.current;
    const draw = () => {
      ctx.clearRect(0, 0, w, h); const sy = window.scrollY || 0; const mx = mouseRef.current.x, my = mouseRef.current.y;
      for (let i = 0; i < nodes.length; i++) {
        const a = nodes[i]; a.x += a.vx; a.y += a.vy; if (a.x < 0 || a.x > w) a.vx *= -1; if (a.y < 0 || a.y > 12000) a.vy *= -1;
        const ax = a.x, ay = a.y - sy * .3; if (ay < -200 || ay > h + 200) continue;
        let dx2 = ax - mx, dy2 = ay - my, md = Math.sqrt(dx2 * dx2 + dy2 * dy2); let drawX = ax, drawY = ay;
        if (md < 140 && md > 0) { const push = (1 - md / 140) * 18; drawX += (dx2 / md) * push; drawY += (dy2 / md) * push; }
        for (let j = i + 1; j < nodes.length; j++) { const b = nodes[j]; const bx = b.x, by = b.y - sy * .3; if (by < -200 || by > h + 200) continue; const dx = drawX - bx, dy = drawY - by, dist = Math.sqrt(dx * dx + dy * dy); if (dist < 150) { ctx.beginPath(); ctx.moveTo(drawX, drawY); ctx.lineTo(bx, by); ctx.strokeStyle = `rgba(212,168,83,${.06 * (1 - dist / 150)})`; ctx.lineWidth = .5; ctx.stroke(); } }
        const hex = a.color; const r2 = parseInt(hex.slice(1, 3), 16), g = parseInt(hex.slice(3, 5), 16), b2 = parseInt(hex.slice(5, 7), 16);
        ctx.beginPath(); ctx.arc(drawX, drawY, a.r, 0, Math.PI * 2); ctx.fillStyle = `rgba(${r2},${g},${b2},${a.opacity})`; ctx.fill();
      }
      animRef.current = requestAnimationFrame(draw);
    }; draw();
    return () => { window.removeEventListener("resize", resize); window.removeEventListener("mousemove", onMouse); cancelAnimationFrame(animRef.current); };
  }, []);
  return <canvas ref={canvasRef} style={{ position: "fixed", top: 0, left: 0, width: "100%", height: "100%", zIndex: 0, pointerEvents: "none" }} />;
}

const ease = "cubic-bezier(.22,1,.36,1)";
function Section({ children, style = {}, id }) {
  const [ref, inView] = useInView(.08);
  return <section ref={ref} id={id} style={{ opacity: inView ? 1 : 0, transform: inView ? "translateY(0)" : "translateY(50px)", transition: `opacity .9s ${ease}, transform .9s ${ease}`, position: "relative", zIndex: 1, padding: "clamp(80px,12vw,140px) clamp(16px,4vw,24px)", maxWidth: 1100, margin: "0 auto", ...style }}>{children}</section>;
}
function Stat({ number, suffix = "", label, color = GOLD, delay = 0, trigger }) {
  const c = useCounter(number, 2200, trigger);
  return <div style={{ textAlign: "center", padding: "clamp(16px,3vw,28px) 12px", opacity: trigger ? 1 : 0, transform: trigger ? "scale(1)" : "scale(.9)", transition: `all .7s ${ease} ${delay}ms` }}><div style={{ fontFamily: "'Instrument Serif',Georgia,serif", fontSize: "clamp(28px,5vw,56px)", color, lineHeight: 1 }}>{c.toLocaleString()}{suffix}</div><div style={{ fontSize: "clamp(10px,1.4vw,12px)", color: "rgba(255,255,255,.45)", marginTop: 10, letterSpacing: ".1em", textTransform: "uppercase" }}>{label}</div></div>;
}
function NavDot({ active, label, onClick }) {
  return <button onClick={onClick} title={label} aria-label={label} style={{ width: active ? 28 : 8, height: 8, borderRadius: 4, border: "none", cursor: "pointer", background: active ? GOLD : "rgba(255,255,255,.15)", transition: `all .4s ${ease}`, padding: 0, margin: "4px 0" }} />;
}

export default function App() {
  const [activeSection, setActiveSection] = useState(0);
  const scrollProgress = useScrollProgress();
  const ids = ["hero", "problem", "insight", "force", "mission", "moat", "model", "pattern", "traction", "opportunity", "cta"];
  const labels = ["Home", "Problem", "Solution", "Scale", "Mission", "Moat", "Economics", "Pattern", "Built", "Window", "Join"];

  useEffect(() => { const h = ids.map((id, i) => { const el = document.getElementById(id); if (!el) return null; const o = new IntersectionObserver(([e]) => { if (e.isIntersecting) setActiveSection(i); }, { threshold: .25 }); o.observe(el); return o; }); return () => h.forEach(o => o?.disconnect()); }, []);
  const scrollTo = (id) => document.getElementById(id)?.scrollIntoView({ behavior: "smooth" });

  const [moatRef, moatIn] = useInView(.1);
  const [trRef, trIn] = useInView(.1);
  const [modRef, modIn] = useInView(.1);
  const [oppRef, oppIn] = useInView(.1);
  const [misRef, misIn] = useInView(.1);
  const [forRef, forIn] = useInView(.1);

  return (
    <div style={{ background: BG, color: "#fff", minHeight: "100vh", fontFamily: "'DM Sans',sans-serif", overflowX: "hidden" }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=DM+Sans:ital,wght@0,300;0,400;0,500;0,600;0,700;1,400&display=swap');
        @keyframes pulse{0%,100%{opacity:.35}50%{opacity:1}}
        @keyframes slideUp{from{opacity:0;transform:translateY(40px)}to{opacity:1;transform:translateY(0)}}
        @keyframes fadeGlow{0%,100%{text-shadow:0 0 60px rgba(212,168,83,.15)}50%{text-shadow:0 0 120px rgba(212,168,83,.35)}}
        @keyframes gradientMove{0%{background-position:0% 50%}50%{background-position:100% 50%}100%{background-position:0% 50%}}
        @keyframes breathe{0%,100%{transform:scale(1);opacity:.5}50%{transform:scale(1.05);opacity:.8}}
        @keyframes orbFloat{0%,100%{transform:translate(0,0)}33%{transform:translate(30px,-20px)}66%{transform:translate(-20px,15px)}}
        @keyframes tickerSlide{0%{transform:translateX(0)}100%{transform:translateX(-50%)}}
        @keyframes ringPulse{0%{transform:scale(.8);opacity:.5}50%{transform:scale(1.3);opacity:0}100%{transform:scale(.8);opacity:0}}
        .h1{animation:slideUp 1s ${ease} .1s both}.h2{animation:slideUp 1s ${ease} .35s both}
        .h3{animation:slideUp 1s ${ease} .6s both}.h4{animation:slideUp 1s ${ease} .85s both}
        .h5{animation:slideUp 1s ${ease} 1.1s both}.live-dot{animation:pulse 2s ease infinite}
        a{color:${GOLD};text-decoration:none}a:hover{text-decoration:underline}
        @media(max-width:600px){.hide-m{display:none!important}}
      `}</style>
      <GraphBackground />
      <div style={{ position: "fixed", top: 0, left: 0, height: 2, zIndex: 200, width: `${scrollProgress * 100}%`, background: `linear-gradient(90deg,${GOLD},${GREEN},${AMETHYST})`, transition: "width .1s linear" }} />
      <nav className="hide-m" style={{ position: "fixed", right: 16, top: "50%", transform: "translateY(-50%)", display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 4, zIndex: 100 }}>
        {ids.map((id, i) => <NavDot key={id} active={activeSection === i} label={labels[i]} onClick={() => scrollTo(id)} />)}
      </nav>

      {/* ═══ HERO ═══ */}
      <section id="hero" style={{ minHeight: "100dvh", display: "flex", flexDirection: "column", justifyContent: "center", alignItems: "center", textAlign: "center", padding: "40px clamp(16px,4vw,24px)", position: "relative", zIndex: 1 }}>
        <div style={{ position: "absolute", top: "20%", left: "10%", width: 300, height: 300, borderRadius: "50%", background: `radial-gradient(circle,rgba(212,168,83,.04),transparent 70%)`, animation: "orbFloat 12s ease infinite", pointerEvents: "none" }} />
        <div style={{ position: "absolute", bottom: "15%", right: "8%", width: 250, height: 250, borderRadius: "50%", background: `radial-gradient(circle,rgba(52,211,153,.03),transparent 70%)`, animation: "orbFloat 15s ease infinite 3s", pointerEvents: "none" }} />

        <div className="h1" style={{ display: "inline-flex", alignItems: "center", gap: 8, padding: "8px 20px", borderRadius: 100, border: "1px solid rgba(212,168,83,.25)", marginBottom: 36, background: "rgba(212,168,83,.06)", fontSize: "clamp(11px,1.5vw,13px)", color: GOLD, letterSpacing: ".05em", flexWrap: "wrap", justifyContent: "center" }}>
          <span className="live-dot" style={{ width: 6, height: 6, borderRadius: "50%", background: GREEN, display: "inline-block" }} />
          <span style={{ fontFamily: "monospace", fontWeight: 600 }}><LiveCounter /></span>
          <span style={{ opacity: .6 }}>RECORDS · 3 VERTICALS · 30+ SOURCES</span>
        </div>

        <h1 className="h2" style={{ fontFamily: "'Instrument Serif',Georgia,serif", fontSize: "clamp(36px,7.5vw,92px)", fontWeight: 400, lineHeight: 1.02, maxWidth: 950, letterSpacing: "-.025em", padding: "0 8px" }}>
          The knowledge graph for{" "}
          <span style={{ background: `linear-gradient(135deg,${GOLD},${GREEN},${AMETHYST},${ORANGE},${GOLD})`, backgroundSize: "400% 400%", animation: "gradientMove 8s ease infinite", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
            trillion-dollar industries
          </span>
        </h1>

        <p className="h3" style={{ fontSize: "clamp(15px,2.2vw,22px)", color: "rgba(255,255,255,.5)", maxWidth: 640, lineHeight: 1.65, marginTop: 24, fontWeight: 300, padding: "0 12px" }}>
          One architecture. Three verticals. $29 trillion in combined markets.<br />10 million records. One founder. AI as the ultimate force multiplier.
        </p>

        <button className="h4" onClick={() => scrollTo("problem")} style={{ marginTop: 40, padding: "16px 40px", borderRadius: 100, border: `1px solid ${GOLD}`, background: "transparent", color: GOLD, fontSize: 14, fontWeight: 500, cursor: "pointer", letterSpacing: ".06em", transition: `all .4s ${ease}`, fontFamily: "'DM Sans',sans-serif" }}
          onMouseEnter={e => { e.target.style.background = GOLD; e.target.style.color = BG; e.target.style.transform = "scale(1.04)"; e.target.style.boxShadow = `0 0 50px rgba(212,168,83,.25)`; }}
          onMouseLeave={e => { e.target.style.background = "transparent"; e.target.style.color = GOLD; e.target.style.transform = "scale(1)"; e.target.style.boxShadow = "none"; }}
        >SEE THE THESIS ↓</button>

        <div className="h5" style={{ marginTop: 48, overflow: "hidden", width: "100%", maxWidth: 700, maskImage: "linear-gradient(90deg,transparent,black 15%,black 85%,transparent)", WebkitMaskImage: "linear-gradient(90deg,transparent,black 15%,black 85%,transparent)" }}>
          <div style={{ display: "flex", gap: 32, animation: "tickerSlide 25s linear infinite", width: "max-content" }}>
            {[...Array(2)].flatMap(() => ["CMS", "NLM", "FDA", "HHS-OIG", "NPPES", "ClinicalTrials.gov", "PubMed", "RxNorm", "NPI Registry", "ICD-10", "NDC", "ICC Codes", "OSHA", "Ecuagenera", "WCSP", "USDA"]).map((s, i) => (
              <span key={i} style={{ fontSize: 11, color: "rgba(255,255,255,.18)", letterSpacing: ".12em", whiteSpace: "nowrap" }}>{s}</span>
            ))}
          </div>
        </div>
      </section>

      {/* ═══ PROBLEM ═══ */}
      <Section id="problem">
        <div style={{ textAlign: "center", marginBottom: 56 }}>
          <div style={{ fontSize: 12, color: RED, letterSpacing: ".15em", textTransform: "uppercase", marginBottom: 16 }}>THE PROBLEM</div>
          <h2 style={{ fontFamily: "'Instrument Serif',Georgia,serif", fontSize: "clamp(26px,5vw,56px)", fontWeight: 400, lineHeight: 1.12, maxWidth: 850, margin: "0 auto" }}>
            The world's biggest industries have <span style={{ fontStyle: "italic", color: RED }}>no shared knowledge layer</span>
          </h2>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(min(100%,280px),1fr))", gap: 16, maxWidth: 920, margin: "0 auto" }}>
          {[
            { num: "$29T+", label: "in industries running on fragmented data", sub: "Healthcare ($12T) + Construction ($17T) + and more coming." },
            { num: "150+", label: "days to credential a single provider", sub: "Every day a doctor waits = $7K–$10K in lost revenue." },
            { num: "0", label: "AI-native knowledge graphs for these industries", sub: "Everyone bolts AI onto old architecture. We built native." },
          ].map((item, i) => (
            <div key={i} style={{ padding: "clamp(24px,4vw,36px) clamp(20px,3vw,28px)", background: BG_CARD, borderRadius: 16, border: "1px solid rgba(255,255,255,.06)", backdropFilter: "blur(20px)", position: "relative", overflow: "hidden" }}>
              <div style={{ position: "absolute", top: -1, left: 0, right: 0, height: 1, background: `linear-gradient(90deg,transparent,${RED}44,transparent)` }} />
              <div style={{ fontFamily: "'Instrument Serif',Georgia,serif", fontSize: "clamp(32px,4.5vw,44px)", color: RED, marginBottom: 8 }}>{item.num}</div>
              <div style={{ fontSize: "clamp(13px,1.6vw,15px)", fontWeight: 600, color: "rgba(255,255,255,.85)", marginBottom: 10 }}>{item.label}</div>
              <div style={{ fontSize: 13, color: "rgba(255,255,255,.4)", lineHeight: 1.65 }}>{item.sub}</div>
            </div>
          ))}
        </div>
      </Section>

      {/* ═══ SOLUTION ═══ */}
      <Section id="insight">
        <div style={{ textAlign: "center", marginBottom: 56 }}>
          <div style={{ fontSize: 12, color: GREEN, letterSpacing: ".15em", textTransform: "uppercase", marginBottom: 16 }}>THE SOLUTION</div>
          <h2 style={{ fontFamily: "'Instrument Serif',Georgia,serif", fontSize: "clamp(26px,5vw,56px)", fontWeight: 400, lineHeight: 1.12, maxWidth: 880, margin: "0 auto" }}>
            One AI-native graph that connects{" "}
            <MorphWords words={["every provider", "every drug", "every diagnosis", "every building code", "every species", "every regulation"]} color={GREEN} />
          </h2>
          <p style={{ fontSize: "clamp(14px,1.8vw,17px)", color: "rgba(255,255,255,.42)", maxWidth: 580, margin: "24px auto 0", lineHeight: 1.7 }}>
            One architecture, deployable to any knowledge-intensive vertical. Self-updating. AI-native. Already live across healthcare, construction, and botanical sciences.
          </p>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(min(48%,160px),1fr))", gap: 2, background: "rgba(255,255,255,.04)", borderRadius: 20, overflow: "hidden", maxWidth: 920, margin: "0 auto" }}>
          {[
            { emoji: "🏥", label: "Providers", count: "9.4M", sub: "Every licensed US provider" },
            { emoji: "💊", label: "Drugs", count: "83K+", sub: "NDC + interactions" },
            { emoji: "🔬", label: "Trials", count: "34K+", sub: "ClinicalTrials.gov" },
            { emoji: "📋", label: "Diagnoses", count: "97K+", sub: "Complete ICD-10" },
            { emoji: "📄", label: "Literature", count: "60K+", sub: "PubMed citations" },
            { emoji: "⚖️", label: "Regulatory", count: "83K+", sub: "OIG + board actions" },
          ].map((item, i) => (
            <div key={i} style={{ padding: "clamp(16px,3vw,24px) 14px", background: BG_CARD, textAlign: "center" }}>
              <div style={{ fontSize: 20, marginBottom: 4 }}>{item.emoji}</div>
              <div style={{ fontSize: "clamp(18px,2.5vw,22px)", fontFamily: "'Instrument Serif',Georgia,serif", color: GREEN }}>{item.count}</div>
              <div style={{ fontSize: 12, fontWeight: 600, color: "rgba(255,255,255,.65)", marginTop: 3 }}>{item.label}</div>
              <div style={{ fontSize: 10, color: "rgba(255,255,255,.3)", marginTop: 2 }}>{item.sub}</div>
            </div>
          ))}
        </div>
        <div style={{ textAlign: "center", marginTop: 32, padding: "16px 24px", background: "rgba(52,211,153,.05)", borderRadius: 12, border: `1px solid ${GREEN}18`, maxWidth: 520, margin: "32px auto 0" }}>
          <div style={{ fontSize: 14, color: GREEN, fontWeight: 500 }}>Healthcare alone: 17 federal sources. Zero licensing cost at any scale.</div>
        </div>
      </Section>

      {/* ═══ FORCE MULTIPLIER ═══ */}
      <section id="force" style={{ position: "relative", zIndex: 1, padding: "clamp(80px,12vw,140px) clamp(16px,4vw,24px)", overflow: "hidden" }}>
        <div style={{ position: "absolute", top: "50%", left: "50%", transform: "translate(-50%,-50%)", width: "min(900px,100vw)", height: "min(900px,100vw)", borderRadius: "50%", background: `radial-gradient(circle,rgba(212,168,83,.04),rgba(167,139,250,.03) 30%,rgba(52,211,153,.02) 60%,transparent 70%)`, animation: "breathe 10s ease infinite", pointerEvents: "none" }} />
        <div ref={forRef} style={{ maxWidth: 900, margin: "0 auto", textAlign: "center", position: "relative" }}>
          <div style={{ fontSize: 12, color: AMETHYST, letterSpacing: ".15em", textTransform: "uppercase", marginBottom: 20, opacity: forIn ? 1 : 0, transition: "opacity .6s ease" }}>THE FORCE MULTIPLIER</div>
          <h2 style={{ fontFamily: "'Instrument Serif',Georgia,serif", fontSize: "clamp(28px,5.5vw,64px)", fontWeight: 400, lineHeight: 1.1, marginBottom: 24, opacity: forIn ? 1 : 0, transform: forIn ? "translateY(0)" : "translateY(30px)", transition: `all .8s ${ease} .1s` }}>
            Not <span style={{ color: "rgba(255,255,255,.35)" }}>10 million records.</span>
          </h2>

          {/* Giant relationship number */}
          <div style={{ marginBottom: 16, opacity: forIn ? 1 : 0, transform: forIn ? "scale(1)" : "scale(0.85)", transition: `all 1s ${ease} .3s` }}>
            <div style={{ fontFamily: "'Instrument Serif',Georgia,serif", fontSize: "clamp(56px,10vw,120px)", lineHeight: 1, background: `linear-gradient(135deg,${GOLD},${GREEN},${AMETHYST})`, backgroundSize: "200% 200%", animation: "gradientMove 4s ease infinite", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
              <CountUp end={500} />M+
            </div>
            <div style={{ fontSize: "clamp(16px,2.5vw,24px)", color: "rgba(255,255,255,.7)", marginTop: 8, fontWeight: 300, letterSpacing: ".02em" }}>
              queryable <span style={{ color: GOLD, fontWeight: 600 }}>relationships</span>
            </div>
          </div>

          <p style={{ fontSize: "clamp(14px,1.8vw,18px)", color: "rgba(255,255,255,.4)", maxWidth: 600, margin: "0 auto 48px", lineHeight: 1.7 }}>
            Every entity connects to dozens of others. That's what makes a knowledge graph
            <span style={{ color: GREEN }}> fundamentally different</span> from a database — and what no one else has built.
          </p>

          {/* Animated connection chains */}
          <div style={{ maxWidth: 760, margin: "0 auto 48px", display: "flex", flexDirection: "column", gap: 12 }}>
            {[
              { chain: ["Dr. Sarah Chen", "Board Certified", "Internal Medicine", "Treats", "Type 2 Diabetes", "First-line Drug", "Metformin", "Interacts With", "Warfarin"], colors: [GREEN, "rgba(255,255,255,.3)", GREEN, "rgba(255,255,255,.3)", RED, "rgba(255,255,255,.3)", GOLD, "rgba(255,255,255,.3)", RED], label: "One provider → 8 verified relationships in one traversal" },
              { chain: ["Metformin", "83K NDC Codes", "5,500 Interactions", "34K Trials", "9.4M Prescribers", "97K Diagnoses"], colors: [GOLD, AMETHYST, RED, GREEN, GREEN, RED], label: "One drug → connections across the entire knowledge graph" },
              { chain: ["NPI Verified", "OIG Clear", "State Licensed", "Board Certified", "CME Current", "✓ Credentialed"], colors: [GREEN, GREEN, GREEN, GREEN, GREEN, GOLD], label: "One verification → six data sources checked in milliseconds" },
            ].map((row, ri) => (
              <div key={ri} style={{ opacity: forIn ? 1 : 0, transform: forIn ? "translateX(0)" : "translateX(-40px)", transition: `all .7s ${ease} ${ri * 200 + 500}ms` }}>
                <div style={{ display: "flex", alignItems: "center", gap: 0, overflowX: "auto", padding: "12px 0", maskImage: "linear-gradient(90deg,transparent,black 3%,black 97%,transparent)", WebkitMaskImage: "linear-gradient(90deg,transparent,black 3%,black 97%,transparent)" }}>
                  {row.chain.map((node, ni) => (
                    <div key={ni} style={{ display: "flex", alignItems: "center", flexShrink: 0 }}>
                      <span style={{ padding: "6px 12px", borderRadius: 8, fontSize: "clamp(10px,1.3vw,13px)", background: `${row.colors[ni]}12`, border: `1px solid ${row.colors[ni]}25`, color: row.colors[ni], whiteSpace: "nowrap", fontWeight: 500 }}>
                        {node}
                      </span>
                      {ni < row.chain.length - 1 && (
                        <span style={{ color: "rgba(255,255,255,.15)", fontSize: 14, margin: "0 4px", flexShrink: 0 }}>→</span>
                      )}
                    </div>
                  ))}
                </div>
                <div style={{ fontSize: 11, color: "rgba(255,255,255,.3)", textAlign: "left", marginTop: 4, paddingLeft: 4 }}>{row.label}</div>
              </div>
            ))}
          </div>

          {/* Stat cards */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(min(48%,200px),1fr))", gap: 14, maxWidth: 820, margin: "0 auto" }}>
            {[
              { end: 10, suffix: "M+", label: "Total Entities", sub: "Across 3 Knowledge Gardens", color: GOLD, delay: 900 },
              { end: 30, suffix: "+", label: "Data Sources", sub: "Federal · scientific · commercial", color: GREEN, delay: 1050 },
              { end: 3, suffix: "", label: "Industry Verticals", sub: "Healthcare · Construction · Botanical", color: AMETHYST, delay: 1200 },
              { end: 29, suffix: "T+", label: "Combined Markets", sub: "One architecture serves them all", color: ORANGE, delay: 1350 },
            ].map((item, i) => (
              <div key={i} style={{ padding: "clamp(20px,3vw,32px) 16px", borderRadius: 16, background: BG_CARD, border: `1px solid ${item.color}15`, backdropFilter: "blur(20px)", textAlign: "center", opacity: forIn ? 1 : 0, transform: forIn ? "translateY(0)" : "translateY(30px)", transition: `all .7s ${ease} ${item.delay}ms` }}>
                <div style={{ fontFamily: "'Instrument Serif',Georgia,serif", fontSize: "clamp(28px,4vw,48px)", color: item.color, lineHeight: 1 }}>
                  {item.end === 29 ? "$" : ""}<CountUp end={item.end} />{item.suffix}
                </div>
                <div style={{ fontSize: 13, fontWeight: 600, color: "rgba(255,255,255,.7)", marginTop: 8 }}>{item.label}</div>
                <div style={{ fontSize: 11, color: "rgba(255,255,255,.35)", marginTop: 4 }}>{item.sub}</div>
              </div>
            ))}
          </div>

          {/* The punchline */}
          <div style={{ marginTop: 40, padding: "20px 28px", borderRadius: 16, background: `linear-gradient(135deg,${AMETHYST}06,${GOLD}06)`, border: "1px solid rgba(255,255,255,.05)", maxWidth: 700, margin: "40px auto 0", opacity: forIn ? 1 : 0, transition: `all .8s ${ease} 1.5s` }}>
            <div style={{ fontSize: "clamp(15px,1.8vw,18px)", color: "rgba(255,255,255,.75)", lineHeight: 1.8, fontWeight: 300 }}>
              A database stores <span style={{ color: "rgba(255,255,255,.4)" }}>rows</span>. A knowledge graph stores <span style={{ color: GOLD, fontWeight: 600 }}>meaning</span>.
              <br />Every relationship is a question the system can answer, a verification it can perform, a connection no one else can see.
              <br /><span style={{ color: GREEN, fontWeight: 500 }}>This is what $29 trillion in industries have never had.</span>
            </div>
          </div>
        </div>
      </section>

      {/* ═══ MISSION ═══ */}
      <section id="mission" style={{ position: "relative", zIndex: 1, padding: "clamp(80px,14vw,140px) clamp(16px,4vw,24px)", overflow: "hidden" }}>
        <div style={{ position: "absolute", top: "50%", left: "50%", transform: "translate(-50%,-50%)", width: "min(800px,100vw)", height: "min(800px,100vw)", borderRadius: "50%", background: `radial-gradient(circle,rgba(212,168,83,.05),rgba(52,211,153,.03) 40%,transparent 70%)`, animation: "breathe 8s ease infinite", pointerEvents: "none" }} />
        <div ref={misRef} style={{ maxWidth: 800, margin: "0 auto", textAlign: "center", position: "relative" }}>
          <div style={{ fontSize: 12, color: GOLD, letterSpacing: ".15em", textTransform: "uppercase", marginBottom: 20, opacity: misIn ? 1 : 0, transition: "opacity .6s ease" }}>WHY THIS MATTERS</div>
          <h2 style={{ fontFamily: "'Instrument Serif',Georgia,serif", fontSize: "clamp(28px,5.5vw,64px)", fontWeight: 400, lineHeight: 1.1, marginBottom: 48, opacity: misIn ? 1 : 0, transform: misIn ? "translateY(0)" : "translateY(30px)", transition: `all .8s ${ease} .1s` }}>
            This isn't about software.<br />It's about what happens when<br />
            <span style={{ color: GOLD, animation: "fadeGlow 4s ease infinite" }}>the right people get their time back.</span>
          </h2>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(min(100%,200px),1fr))", gap: 16, maxWidth: 700, margin: "0 auto 40px" }}>
            {[
              { word: "Healthier", sub: "Patients find the right provider, trial, and answer instantly. Doctors practice medicine instead of paperwork.", color: GREEN, delay: 200 },
              { word: "Wealthier", sub: "Doctors earn instead of wait. Hospitals save millions. Builders find materials in seconds, not weeks.", color: GOLD, delay: 400 },
              { word: "Freer", sub: "AI handles the bureaucracy across every industry. Humans do what they do best — care, create, build.", color: AMETHYST, delay: 600 },
            ].map((item, i) => (
              <div key={i} style={{ padding: "clamp(20px,3vw,32px) clamp(16px,2.5vw,24px)", borderRadius: 16, background: BG_CARD, border: `1px solid ${item.color}15`, backdropFilter: "blur(20px)", opacity: misIn ? 1 : 0, transform: misIn ? "translateY(0)" : "translateY(30px)", transition: `all .7s ${ease} ${item.delay}ms` }}>
                <div style={{ fontFamily: "'Instrument Serif',Georgia,serif", fontSize: "clamp(24px,3.5vw,32px)", color: item.color, marginBottom: 10, fontStyle: "italic" }}>{item.word}</div>
                <div style={{ fontSize: 13, color: "rgba(255,255,255,.5)", lineHeight: 1.7 }}>{item.sub}</div>
              </div>
            ))}
          </div>
          <div style={{ padding: "clamp(16px,3vw,24px) clamp(20px,4vw,36px)", borderRadius: 16, maxWidth: 660, margin: "0 auto", background: `linear-gradient(135deg,rgba(212,168,83,.04),transparent)`, border: "1px solid rgba(212,168,83,.1)", opacity: misIn ? 1 : 0, transform: misIn ? "translateY(0)" : "translateY(20px)", transition: `all .8s ${ease} .8s` }}>
            <div style={{ fontSize: "clamp(14px,1.8vw,17px)", color: "rgba(255,255,255,.7)", lineHeight: 1.8, fontWeight: 300 }}>
              Every AI pitch says <span style={{ fontStyle: "italic", opacity: .5 }}>"we'll make people more productive."</span>
              <br />This is the <span style={{ color: GOLD, fontWeight: 500 }}>living proof</span>.
              One founder. Three industries. 10 million records. Tonight.
              <br /><span style={{ color: GREEN, fontWeight: 500 }}>AI doesn't replace people. It gives them superpowers.</span>
            </div>
          </div>
        </div>
      </section>

      {/* ═══ MOAT ═══ */}
      <Section id="moat">
        <div ref={moatRef} style={{ textAlign: "center", marginBottom: 56 }}>
          <div style={{ fontSize: 12, color: AMETHYST, letterSpacing: ".15em", textTransform: "uppercase", marginBottom: 16 }}>THE MOAT</div>
          <h2 style={{ fontFamily: "'Instrument Serif',Georgia,serif", fontSize: "clamp(26px,5vw,56px)", fontWeight: 400, lineHeight: 1.12, maxWidth: 850, margin: "0 auto" }}>
            Every AI agent on earth will cite <span style={{ fontStyle: "italic", color: AMETHYST }}>us</span>
          </h2>
          <p style={{ fontSize: "clamp(14px,1.8vw,17px)", color: "rgba(255,255,255,.42)", maxWidth: 620, margin: "24px auto 0", lineHeight: 1.7 }}>
            Every entity URL serves structured JSON-LD + llms.txt. When AI answers a question about healthcare, construction, or botany — we're the source it cites. A moat that compounds with every query.
          </p>
        </div>
        <div style={{ maxWidth: 700, margin: "0 auto", background: BG_CARD, borderRadius: 16, border: `1px solid ${AMETHYST}18`, padding: "clamp(24px,4vw,36px) clamp(20px,3.5vw,32px)", position: "relative", overflow: "hidden", backdropFilter: "blur(20px)" }}>
          <div style={{ position: "absolute", top: 0, left: 0, right: 0, height: 2, background: `linear-gradient(90deg,transparent,${AMETHYST},transparent)` }} />
          <div style={{ fontSize: 12, color: AMETHYST, letterSpacing: ".08em", marginBottom: 24, fontFamily: "monospace" }}>{'>'} THE FLYWHEEL</div>
          {[
            { step: "01", text: "Someone asks AI about metformin, building codes, or orchid care", icon: "🔍" },
            { step: "02", text: "AI finds our structured data — the most citable source on the web", icon: "🧠" },
            { step: "03", text: "AI cites the Knowledge Garden → organic traffic → zero cost", icon: "📈" },
            { step: "04", text: "More traffic → more authority → more citations → permanent loop", icon: "♾️" },
          ].map((item, i) => (
            <div key={i} style={{ display: "flex", alignItems: "center", gap: "clamp(8px,2vw,16px)", padding: "12px 0", borderBottom: i < 3 ? "1px solid rgba(255,255,255,.04)" : "none", opacity: moatIn ? 1 : 0, transform: moatIn ? "translateX(0)" : "translateX(-30px)", transition: `all .6s ${ease} ${i * 120}ms` }}>
              <span style={{ fontSize: 18, width: 32, textAlign: "center", flexShrink: 0 }}>{item.icon}</span>
              <span style={{ fontFamily: "monospace", color: AMETHYST, fontSize: 11, opacity: .4, flexShrink: 0 }}>{item.step}</span>
              <span style={{ fontSize: "clamp(13px,1.6vw,15px)", color: "rgba(255,255,255,.75)", lineHeight: 1.5 }}>{item.text}</span>
            </div>
          ))}
          <div style={{ marginTop: 20, padding: "14px 18px", background: "rgba(167,139,250,.04)", borderRadius: 10, border: "1px solid rgba(167,139,250,.08)" }}>
            <div style={{ fontSize: 14, fontWeight: 600, color: AMETHYST }}>Zero marginal distribution cost. Every vertical multiplies it.</div>
          </div>
        </div>
      </Section>

      {/* ═══ ECONOMICS ═══ */}
      <Section id="model">
        <div ref={modRef} style={{ textAlign: "center", marginBottom: 56 }}>
          <div style={{ fontSize: 12, color: GOLD, letterSpacing: ".15em", textTransform: "uppercase", marginBottom: 16 }}>THE ECONOMIC ENGINE</div>
          <h2 style={{ fontFamily: "'Instrument Serif',Georgia,serif", fontSize: "clamp(26px,5vw,56px)", fontWeight: 400, lineHeight: 1.12, maxWidth: 900, margin: "0 auto" }}>
            Four revenue layers.<br /><span style={{ fontStyle: "italic", color: GOLD }}>Each one funds the next.</span>
          </h2>
        </div>
        <div style={{ maxWidth: 800, margin: "0 auto", display: "flex", flexDirection: "column", gap: 12 }}>
          {[
            { layer: "01", color: RED, label: "Verification & Credentialing", who: "Hospitals · Insurers · Staffing", how: "$0.50–$2/query · $15–50/provider/mo · $50K–150K/yr enterprise", why: "Regulatory mandate. Hospitals cannot legally operate without it.", tag: "MANDATORY" },
            { layer: "02", color: GREEN, label: "Professional Platform", who: "Doctors · Builders · Specialists", how: "CME affiliate (15–25%) · Recruiter fees · Premium portfolios", why: "Every professional recertifies on a cycle. Permanent lifecycle revenue.", tag: "RECURRING" },
            { layer: "03", color: AMETHYST, label: "Machine Lane / API", who: "AI companies · EHR/BIM vendors · Startups", how: "$99–$2,499/mo usage-based · MCP server · Enterprise feeds", why: "Every AI product needs structured, citable data. We're the source.", tag: "SCALES WITH AI" },
            { layer: "04", color: GOLD, label: "Intelligence & Analytics", who: "Pharma · Government · Enterprise", how: "$50K–$500K/yr enterprise · Workforce · Market intelligence", why: "The graph reveals relationships no flat database can. Pure margin.", tag: "HIGH MARGIN" },
          ].map((item, i) => (
            <div key={i} style={{ background: BG_CARD, borderRadius: 16, padding: "clamp(18px,3vw,26px) clamp(18px,3vw,28px)", border: `1px solid ${item.color}15`, position: "relative", overflow: "hidden", backdropFilter: "blur(20px)", opacity: modIn ? 1 : 0, transform: modIn ? "translateX(0)" : "translateX(-30px)", transition: `all .6s ${ease} ${i * 120}ms` }}>
              <div style={{ position: "absolute", top: 0, left: 0, bottom: 0, width: 3, background: item.color, opacity: .5 }} />
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 8, marginBottom: 8 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <span style={{ fontFamily: "monospace", fontSize: 11, color: item.color, opacity: .4 }}>{item.layer}</span>
                  <span style={{ fontSize: "clamp(14px,1.8vw,17px)", fontWeight: 600, color: item.color }}>{item.label}</span>
                </div>
                <span style={{ fontSize: 9, letterSpacing: ".1em", color: item.color, padding: "3px 10px", borderRadius: 100, border: `1px solid ${item.color}28`, background: `${item.color}06` }}>{item.tag}</span>
              </div>
              <div style={{ fontSize: 12, color: "rgba(255,255,255,.4)", marginBottom: 4 }}>{item.who}</div>
              <div style={{ fontSize: "clamp(11px,1.4vw,13px)", color: "rgba(255,255,255,.7)", fontFamily: "monospace", marginBottom: 6, lineHeight: 1.6 }}>{item.how}</div>
              <div style={{ fontSize: 13, color: "rgba(255,255,255,.42)", fontStyle: "italic" }}>{item.why}</div>
            </div>
          ))}
        </div>
        <div style={{ maxWidth: 800, margin: "32px auto 0", padding: "clamp(18px,3vw,24px) clamp(20px,3vw,28px)", borderRadius: 16, background: `linear-gradient(135deg,rgba(52,211,153,.03),rgba(212,168,83,.03))`, border: "1px solid rgba(255,255,255,.05)", opacity: modIn ? 1 : 0, transition: "all .8s ease .6s", position: "relative", overflow: "hidden" }}>
          <div style={{ position: "absolute", top: 0, left: 0, right: 0, height: 1, background: `linear-gradient(90deg,${GREEN}33,${GOLD}33)` }} />
          <div style={{ display: "flex", alignItems: "flex-start", gap: "clamp(12px,3vw,20px)", flexWrap: "wrap" }}>
            <div><div style={{ fontFamily: "'Instrument Serif',Georgia,serif", fontSize: "clamp(36px,5vw,48px)", color: GREEN, lineHeight: 1 }}>0</div><div style={{ fontSize: 10, color: "rgba(255,255,255,.35)", marginTop: 4, letterSpacing: ".05em" }}>TIMES HEALTHCARE<br />CONTRACTED Y/Y</div></div>
            <div style={{ flex: 1, minWidth: 200 }}>
              <div style={{ fontSize: 15, fontWeight: 600, color: "rgba(255,255,255,.8)", marginBottom: 6 }}>Recession-proof by design.</div>
              <div style={{ fontSize: 13, color: "rgba(255,255,255,.42)", lineHeight: 1.7 }}>Healthcare is 18% of GDP and has never contracted. Downturns <span style={{ color: GREEN }}>accelerate</span> our model: hospitals cut headcount → buy automation. AI adoption rises → more API queries. Same dynamics across construction compliance.</div>
            </div>
          </div>
        </div>
      </Section>

      {/* ═══ PATTERN ═══ */}
      <Section id="pattern">
        <div style={{ textAlign: "center", marginBottom: 56 }}>
          <div style={{ fontSize: 12, color: GREEN, letterSpacing: ".15em", textTransform: "uppercase", marginBottom: 16 }}>THE PATTERN</div>
          <h2 style={{ fontFamily: "'Instrument Serif',Georgia,serif", fontSize: "clamp(26px,5vw,52px)", fontWeight: 400, lineHeight: 1.12 }}>
            Third vertical. <span style={{ fontStyle: "italic", color: GREEN }}>Same playbook. Every time it works.</span>
          </h2>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(min(100%,260px),1fr))", gap: 14, maxWidth: 900, margin: "0 auto" }}>
          {[
            { name: "BKG", full: "Builder's Knowledge Garden", market: "$17T Construction", status: "DEPLOYED", color: ORANGE, records: "Materials · Codes · Contractors" },
            { name: "OKG", full: "Orchid Knowledge Garden", market: "Botanical / Ecuagenera", status: "DEPLOYED", color: GREEN, records: "Species · Taxonomy · Care" },
            { name: "HKG", full: "Healthcare Knowledge Garden", market: "$12T+ Healthcare", status: "9.4M RECORDS LIVE", color: GOLD, records: "Providers · Drugs · Trials · Dx" },
          ].map((v, i) => (
            <div key={i} style={{ padding: "clamp(24px,4vw,36px) clamp(20px,3vw,28px)", background: BG_CARD, borderRadius: 16, border: `1px solid ${v.color}18`, position: "relative", overflow: "hidden", backdropFilter: "blur(20px)" }}>
              {v.name === "HKG" && <><div style={{ position: "absolute", top: 0, left: 0, right: 0, height: 2, background: `linear-gradient(90deg,transparent,${v.color},transparent)`, animation: "gradientMove 3s ease infinite" }} /><div style={{ position: "absolute", top: 16, right: 16, width: 36, height: 36, borderRadius: "50%", border: `1px solid ${GOLD}33`, animation: "ringPulse 3s ease infinite" }} /></>}
              <div style={{ fontSize: 11, letterSpacing: ".12em", color: v.color, marginBottom: 12, display: "flex", alignItems: "center", gap: 8 }}>
                {v.name === "HKG" && <span className="live-dot" style={{ width: 6, height: 6, borderRadius: "50%", background: v.color, display: "inline-block" }} />}
                {v.status}
              </div>
              <div style={{ fontFamily: "'Instrument Serif',Georgia,serif", fontSize: "clamp(28px,4vw,40px)", color: v.color }}>{v.name}</div>
              <div style={{ fontSize: 14, color: "rgba(255,255,255,.55)", marginTop: 6 }}>{v.full}</div>
              <div style={{ fontSize: 12, color: "rgba(255,255,255,.3)", marginTop: 6, fontFamily: "monospace" }}>{v.records}</div>
              <div style={{ fontSize: 13, color: "rgba(255,255,255,.3)", marginTop: 4 }}>{v.market}</div>
            </div>
          ))}
        </div>
        <div style={{ textAlign: "center", marginTop: 32 }}>
          <div style={{ fontSize: 14, color: "rgba(255,255,255,.4)", fontStyle: "italic", maxWidth: 500, margin: "0 auto", lineHeight: 1.7 }}>
            Same architecture. Same surfaces. Same RSI flywheel. <span style={{ color: "rgba(255,255,255,.6)" }}>Deploy to a new vertical in weeks, not years.</span>
            <br /><span style={{ color: GOLD }}>The next vertical is already being planned.</span>
          </div>
        </div>
      </Section>

      {/* ═══ TRACTION ═══ */}
      <Section id="traction">
        <div ref={trRef} style={{ textAlign: "center", marginBottom: 44 }}>
          <div style={{ fontSize: 12, color: GOLD, letterSpacing: ".15em", textTransform: "uppercase", marginBottom: 16 }}>WHAT'S BUILT</div>
          <h2 style={{ fontFamily: "'Instrument Serif',Georgia,serif", fontSize: "clamp(26px,5vw,52px)", fontWeight: 400, lineHeight: 1.12 }}>
            This is not a <span style={{ fontStyle: "italic", color: GOLD }}>pitch.</span><br />It's a progress report.
          </h2>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(min(48%,180px),1fr))", gap: 8, maxWidth: 900, margin: "0 auto" }}>
          <Stat trigger={trIn} number={10200000} suffix="+" label="Total Records" color={GOLD} delay={0} />
          <Stat trigger={trIn} number={30} suffix="+" label="Data Sources" color={GREEN} delay={100} />
          <Stat trigger={trIn} number={3} label="Industry Verticals" color={AMETHYST} delay={200} />
          <Stat trigger={trIn} number={1} label="Founder" color={RED} delay={300} />
        </div>
        <div style={{ maxWidth: 700, margin: "40px auto 0", padding: "24px 28px", borderRadius: 16, background: BG_CARD, border: "1px solid rgba(255,255,255,.05)", backdropFilter: "blur(20px)" }}>
          <div style={{ fontSize: 12, color: "rgba(255,255,255,.25)", letterSpacing: ".1em", marginBottom: 14 }}>TECH STACK</div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
            {["Neo4j", "Supabase", "Claude API", "MCP", "Next.js", "React", "Three.js", "Python", "JSON-LD", "llms.txt"].map(t => (
              <span key={t} style={{ padding: "5px 13px", borderRadius: 100, fontSize: 12, background: "rgba(255,255,255,.03)", border: "1px solid rgba(255,255,255,.07)", color: "rgba(255,255,255,.45)" }}>{t}</span>
            ))}
          </div>
        </div>
        <div style={{ textAlign: "center", marginTop: 28 }}>
          <div style={{ fontSize: 14, color: "rgba(255,255,255,.35)", fontStyle: "italic" }}>
            One founder. Zero external capital. 10M+ records across three industries.
            <br /><span style={{ color: GOLD }}>Imagine what a funded team does with this in 6 months.</span>
          </div>
        </div>
      </Section>

      {/* ═══ OPPORTUNITY ═══ */}
      <Section id="opportunity">
        <div ref={oppRef} style={{ textAlign: "center", marginBottom: 56 }}>
          <div style={{ fontSize: 12, color: GOLD, letterSpacing: ".15em", textTransform: "uppercase", marginBottom: 16 }}>THE WINDOW</div>
          <h2 style={{ fontFamily: "'Instrument Serif',Georgia,serif", fontSize: "clamp(26px,5vw,56px)", fontWeight: 400, lineHeight: 1.12 }}>
            The timing is <span style={{ fontStyle: "italic", color: RED }}>closing</span>
          </h2>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(min(48%,200px),1fr))", gap: 12, maxWidth: 900, margin: "0 auto" }}>
          {[
            { value: "$29T+", label: "Combined Market Coverage", color: GOLD },
            { value: "$394B", label: "Healthcare IT by 2027", color: GREEN },
            { value: "$75B", label: "Health Data Analytics by 2030", color: AMETHYST },
            { value: "∞", label: "Verticals This Architecture Enters", color: ORANGE },
          ].map((m, i) => (
            <div key={i} style={{ textAlign: "center", padding: "clamp(20px,4vw,32px) 14px", borderRadius: 16, background: BG_CARD, border: `1px solid ${m.color}10`, backdropFilter: "blur(20px)", opacity: oppIn ? 1 : 0, transform: oppIn ? "scale(1)" : "scale(.92)", transition: `all .6s ${ease} ${i * 100}ms` }}>
              <div style={{ fontFamily: "'Instrument Serif',Georgia,serif", fontSize: "clamp(28px,4.5vw,38px)", color: m.color }}>{m.value}</div>
              <div style={{ fontSize: 12, color: "rgba(255,255,255,.4)", marginTop: 8, lineHeight: 1.5 }}>{m.label}</div>
            </div>
          ))}
        </div>
        <div style={{ textAlign: "center", marginTop: 44, maxWidth: 600, margin: "44px auto 0" }}>
          <p style={{ fontSize: "clamp(14px,1.8vw,17px)", color: "rgba(255,255,255,.48)", lineHeight: 1.8 }}>
            AI is becoming the primary interface for professional knowledge. The platform that becomes the <span style={{ color: GOLD, fontWeight: 500 }}>canonical source of truth</span> across industries captures a position that <span style={{ color: GREEN, fontWeight: 500 }}>compounds permanently</span>.
          </p>
          <p style={{ fontSize: 16, color: RED, fontWeight: 500, marginTop: 18 }}>That window doesn't stay open.</p>
        </div>
      </Section>

      {/* ═══ CTA ═══ */}
      <section id="cta" style={{ minHeight: "85dvh", display: "flex", flexDirection: "column", justifyContent: "center", alignItems: "center", textAlign: "center", padding: "80px clamp(16px,4vw,24px)", position: "relative", zIndex: 1 }}>
        <div style={{ position: "absolute", top: "50%", left: "50%", transform: "translate(-50%,-50%)", width: "min(600px,90vw)", height: "min(600px,90vw)", borderRadius: "50%", background: `radial-gradient(circle,rgba(212,168,83,.05),transparent 60%)`, animation: "breathe 6s ease infinite", pointerEvents: "none" }} />
        <div style={{ position: "absolute", top: "50%", left: "50%", transform: "translate(-50%,-50%)", width: "min(400px,70vw)", height: "min(400px,70vw)", borderRadius: "50%", border: "1px solid rgba(212,168,83,.06)", animation: "ringPulse 4s ease infinite", pointerEvents: "none" }} />
        <h2 style={{ fontFamily: "'Instrument Serif',Georgia,serif", fontSize: "clamp(30px,6vw,72px)", fontWeight: 400, lineHeight: 1.08, maxWidth: 750, position: "relative" }}>
          Three industries connected.<br />
          <span style={{ animation: "fadeGlow 4s ease infinite" }}>Dozens more waiting.</span>
        </h2>
        <p style={{ fontSize: "clamp(15px,2vw,18px)", color: "rgba(255,255,255,.4)", marginTop: 24, maxWidth: 440, lineHeight: 1.7 }}>
          We're looking for investors and builders who want to own the infrastructure layer for the world's most important industries.
        </p>
        <div style={{ display: "flex", gap: 14, marginTop: 40, flexWrap: "wrap", justifyContent: "center" }}>
          <a href="mailto:chilly@xrworkers.com" style={{ padding: "16px 40px", borderRadius: 100, background: GOLD, color: BG, fontSize: 15, fontWeight: 600, textDecoration: "none", letterSpacing: ".02em", transition: `all .4s ${ease}`, display: "inline-block" }}
            onMouseEnter={e => { e.target.style.transform = "scale(1.06)"; e.target.style.boxShadow = `0 0 60px rgba(212,168,83,.3)`; }}
            onMouseLeave={e => { e.target.style.transform = "scale(1)"; e.target.style.boxShadow = "none"; }}
          >LET'S TALK</a>
          <a href="#hero" style={{ padding: "16px 40px", borderRadius: 100, border: "1px solid rgba(255,255,255,.12)", color: "rgba(255,255,255,.5)", fontSize: 15, fontWeight: 500, textDecoration: "none", transition: "all .3s ease" }}
            onMouseEnter={e => { e.target.style.borderColor = "rgba(255,255,255,.35)"; e.target.style.color = "#fff"; }}
            onMouseLeave={e => { e.target.style.borderColor = "rgba(255,255,255,.12)"; e.target.style.color = "rgba(255,255,255,.5)"; }}
          >BACK TO TOP</a>
        </div>
        <div style={{ marginTop: 56, fontSize: 11, color: "rgba(255,255,255,.15)", letterSpacing: ".12em" }}>© 2026 XRWORKERS · THE KNOWLEDGE GARDENS</div>
      </section>
    </div>
  );
}
