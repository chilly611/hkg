import { useState, useEffect, useRef } from "react";

const GOLD = "#D4A853";
const GREEN = "#34D399";
const RED = "#EF4444";
const AMETHYST = "#A78BFA";
const BG = "#06060B";
const BG_CARD = "rgba(13,13,20,0.85)";

/* ─── Hooks ─── */
function useCounter(end, duration = 2200, trigger = false) {
  const [count, setCount] = useState(0);
  useEffect(() => {
    if (!trigger) return;
    let start = 0;
    const step = end / (duration / 16);
    const timer = setInterval(() => {
      start += step;
      if (start >= end) { setCount(end); clearInterval(timer); }
      else setCount(Math.floor(start));
    }, 16);
    return () => clearInterval(timer);
  }, [trigger, end, duration]);
  return count;
}

function useInView(threshold = 0.15) {
  const ref = useRef(null);
  const [inView, setInView] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const obs = new IntersectionObserver(([e]) => { if (e.isIntersecting) setInView(true); }, { threshold });
    obs.observe(el);
    return () => obs.disconnect();
  }, [threshold]);
  return [ref, inView];
}

function useScrollProgress() {
  const [progress, setProgress] = useState(0);
  useEffect(() => {
    const onScroll = () => {
      const h = document.documentElement.scrollHeight - window.innerHeight;
      setProgress(h > 0 ? window.scrollY / h : 0);
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);
  return progress;
}

/* ─── Live counter — starts at ~4M, ticks toward 9.4M ─── */
function LiveCounter() {
  const [count, setCount] = useState(4127493);
  useEffect(() => {
    const timer = setInterval(() => {
      setCount(c => c + Math.floor(Math.random() * 4) + 1);
    }, 600);
    return () => clearInterval(timer);
  }, []);
  return count.toLocaleString();
}

/* ─── Morphing word cycle ─── */
function MorphWords({ words, color = GOLD, interval = 2800 }) {
  const [idx, setIdx] = useState(0);
  const [fade, setFade] = useState(true);
  useEffect(() => {
    const timer = setInterval(() => {
      setFade(false);
      setTimeout(() => { setIdx(i => (i + 1) % words.length); setFade(true); }, 400);
    }, interval);
    return () => clearInterval(timer);
  }, [words.length, interval]);
  return (
    <span style={{
      color, display: "inline-block", minWidth: "3ch",
      opacity: fade ? 1 : 0, transform: fade ? "translateY(0)" : "translateY(12px)",
      transition: "all 0.4s cubic-bezier(0.22, 1, 0.36, 1)", fontStyle: "italic",
    }}>
      {words[idx]}
    </span>
  );
}

/* ─── Knowledge graph background ─── */
function GraphBackground() {
  const canvasRef = useRef(null);
  const nodesRef = useRef([]);
  const animRef = useRef(null);
  const mouseRef = useRef({ x: -1000, y: -1000 });

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    let w, h;

    const resize = () => { w = canvas.width = window.innerWidth; h = canvas.height = window.innerHeight; };
    resize();
    window.addEventListener("resize", resize);
    const onMouse = (e) => { mouseRef.current = { x: e.clientX, y: e.clientY }; };
    window.addEventListener("mousemove", onMouse, { passive: true });

    const colors = [GOLD, GREEN, AMETHYST, "#ffffff"];
    if (nodesRef.current.length === 0) {
      for (let i = 0; i < 70; i++) {
        nodesRef.current.push({
          x: Math.random() * 3000, y: Math.random() * 9000,
          vx: (Math.random() - 0.5) * 0.35, vy: (Math.random() - 0.5) * 0.35,
          r: Math.random() * 2.5 + 0.5, color: colors[Math.floor(Math.random() * colors.length)],
          opacity: Math.random() * 0.3 + 0.06,
        });
      }
    }
    const nodes = nodesRef.current;

    const draw = () => {
      ctx.clearRect(0, 0, w, h);
      const sy = window.scrollY || 0;
      const mx = mouseRef.current.x, my = mouseRef.current.y;
      for (let i = 0; i < nodes.length; i++) {
        const a = nodes[i];
        a.x += a.vx; a.y += a.vy;
        if (a.x < 0 || a.x > w) a.vx *= -1;
        if (a.y < 0 || a.y > 9000) a.vy *= -1;
        const ax = a.x, ay = a.y - sy * 0.3;
        if (ay < -200 || ay > h + 200) continue;
        let drawX = ax, drawY = ay;
        const mdx = ax - mx, mdy = ay - my, md = Math.sqrt(mdx * mdx + mdy * mdy);
        if (md < 140 && md > 0) { const push = (1 - md / 140) * 18; drawX += (mdx / md) * push; drawY += (mdy / md) * push; }
        for (let j = i + 1; j < nodes.length; j++) {
          const b = nodes[j]; const bx = b.x, by = b.y - sy * 0.3;
          if (by < -200 || by > h + 200) continue;
          const dx = drawX - bx, dy = drawY - by, dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < 150) { ctx.beginPath(); ctx.moveTo(drawX, drawY); ctx.lineTo(bx, by); ctx.strokeStyle = `rgba(212,168,83,${0.06 * (1 - dist / 150)})`; ctx.lineWidth = 0.5; ctx.stroke(); }
        }
        const hex = a.color;
        const r2 = parseInt(hex.slice(1, 3), 16), g = parseInt(hex.slice(3, 5), 16), b2 = parseInt(hex.slice(5, 7), 16);
        ctx.beginPath(); ctx.arc(drawX, drawY, a.r, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(${r2},${g},${b2},${a.opacity})`; ctx.fill();
      }
      animRef.current = requestAnimationFrame(draw);
    };
    draw();
    return () => { window.removeEventListener("resize", resize); window.removeEventListener("mousemove", onMouse); cancelAnimationFrame(animRef.current); };
  }, []);

  return <canvas ref={canvasRef} style={{ position: "fixed", top: 0, left: 0, width: "100%", height: "100%", zIndex: 0, pointerEvents: "none" }} />;
}

/* ─── Section wrapper ─── */
function Section({ children, style = {}, id }) {
  const [ref, inView] = useInView(0.08);
  return (
    <section ref={ref} id={id} style={{
      opacity: inView ? 1 : 0, transform: inView ? "translateY(0)" : "translateY(50px)",
      transition: "opacity 0.9s cubic-bezier(0.22,1,0.36,1), transform 0.9s cubic-bezier(0.22,1,0.36,1)",
      position: "relative", zIndex: 1, padding: "clamp(80px, 12vw, 140px) clamp(16px, 4vw, 24px)",
      maxWidth: 1100, margin: "0 auto", ...style,
    }}>
      {children}
    </section>
  );
}

/* ─── Stat ─── */
function Stat({ number, suffix = "", label, color = GOLD, delay = 0, trigger }) {
  const count = useCounter(number, 2200, trigger);
  return (
    <div style={{
      textAlign: "center", padding: "clamp(16px, 3vw, 28px) 12px",
      opacity: trigger ? 1 : 0, transform: trigger ? "scale(1)" : "scale(0.9)",
      transition: `all 0.7s cubic-bezier(0.22,1,0.36,1) ${delay}ms`,
    }}>
      <div style={{ fontFamily: "'Instrument Serif', Georgia, serif", fontSize: "clamp(28px, 5vw, 56px)", color, lineHeight: 1 }}>
        {count.toLocaleString()}{suffix}
      </div>
      <div style={{ fontSize: "clamp(10px, 1.4vw, 12px)", color: "rgba(255,255,255,0.45)", marginTop: 10, letterSpacing: "0.1em", textTransform: "uppercase" }}>
        {label}
      </div>
    </div>
  );
}

/* ─── Nav dot ─── */
function NavDot({ active, label, onClick }) {
  return (
    <button onClick={onClick} title={label} aria-label={label} style={{
      width: active ? 28 : 8, height: 8, borderRadius: 4, border: "none", cursor: "pointer",
      background: active ? GOLD : "rgba(255,255,255,0.15)", transition: "all 0.4s cubic-bezier(0.22,1,0.36,1)",
      padding: 0, margin: "4px 0",
    }} />
  );
}

/* ═══════════════════════════════════════
   MAIN
   ═══════════════════════════════════════ */
export default function App() {
  const [activeSection, setActiveSection] = useState(0);
  const scrollProgress = useScrollProgress();
  const sectionIds = ["hero", "problem", "insight", "mission", "moat", "model", "pattern", "traction", "opportunity", "cta"];
  const sectionLabels = ["Home", "Problem", "Solution", "Mission", "Moat", "Economics", "Pattern", "Built", "Opportunity", "Join"];

  useEffect(() => {
    const handlers = sectionIds.map((id, i) => {
      const el = document.getElementById(id);
      if (!el) return null;
      const obs = new IntersectionObserver(([e]) => { if (e.isIntersecting) setActiveSection(i); }, { threshold: 0.25 });
      obs.observe(el);
      return obs;
    });
    return () => handlers.forEach(h => h?.disconnect());
  }, []);

  const scrollTo = (id) => document.getElementById(id)?.scrollIntoView({ behavior: "smooth" });

  const [moatRef, moatInView] = useInView(0.1);
  const [tractionRef, tractionInView] = useInView(0.1);
  const [modelRef, modelInView] = useInView(0.1);
  const [oppRef, oppInView] = useInView(0.1);
  const [missionRef, missionInView] = useInView(0.1);

  const ease = "cubic-bezier(0.22,1,0.36,1)";

  return (
    <div style={{ background: BG, color: "#fff", minHeight: "100vh", fontFamily: "'DM Sans', sans-serif", overflowX: "hidden" }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=DM+Sans:ital,wght@0,300;0,400;0,500;0,600;0,700;1,400&display=swap');
        @keyframes pulse { 0%,100%{opacity:.35} 50%{opacity:1} }
        @keyframes slideUp { from{opacity:0;transform:translateY(40px)} to{opacity:1;transform:translateY(0)} }
        @keyframes fadeGlow { 0%,100%{text-shadow:0 0 60px rgba(212,168,83,.15)} 50%{text-shadow:0 0 120px rgba(212,168,83,.35)} }
        @keyframes gradientMove { 0%{background-position:0% 50%} 50%{background-position:100% 50%} 100%{background-position:0% 50%} }
        @keyframes breathe { 0%,100%{transform:scale(1);opacity:.5} 50%{transform:scale(1.05);opacity:.8} }
        @keyframes orbFloat { 0%,100%{transform:translate(0,0)} 33%{transform:translate(30px,-20px)} 66%{transform:translate(-20px,15px)} }
        @keyframes tickerSlide { 0%{transform:translateX(0)} 100%{transform:translateX(-50%)} }
        @keyframes ringPulse { 0%{transform:scale(.8);opacity:.5} 50%{transform:scale(1.3);opacity:0} 100%{transform:scale(.8);opacity:0} }
        .hero-1{animation:slideUp 1s ${ease} .1s both}
        .hero-2{animation:slideUp 1s ${ease} .35s both}
        .hero-3{animation:slideUp 1s ${ease} .6s both}
        .hero-4{animation:slideUp 1s ${ease} .85s both}
        .hero-5{animation:slideUp 1s ${ease} 1.1s both}
        .live-dot{animation:pulse 2s ease infinite}
        a{color:${GOLD};text-decoration:none} a:hover{text-decoration:underline}
        @media(max-width:600px){
          .hide-mobile{display:none!important}
        }
      `}</style>

      <GraphBackground />

      {/* Scroll progress */}
      <div style={{ position:"fixed",top:0,left:0,height:2,zIndex:200,width:`${scrollProgress*100}%`,background:`linear-gradient(90deg,${GOLD},${GREEN},${AMETHYST})`,transition:"width .1s linear" }}/>

      {/* Side nav — hidden on small screens */}
      <nav className="hide-mobile" style={{ position:"fixed",right:16,top:"50%",transform:"translateY(-50%)",display:"flex",flexDirection:"column",alignItems:"flex-end",gap:4,zIndex:100 }}>
        {sectionIds.map((id,i)=><NavDot key={id} active={activeSection===i} label={sectionLabels[i]} onClick={()=>scrollTo(id)}/>)}
      </nav>

      {/* ═══════════ HERO ═══════════ */}
      <section id="hero" style={{ minHeight:"100vh",minHeight:"100dvh",display:"flex",flexDirection:"column",justifyContent:"center",alignItems:"center",textAlign:"center",padding:"40px clamp(16px,4vw,24px)",position:"relative",zIndex:1 }}>
        <div style={{ position:"absolute",top:"20%",left:"10%",width:300,height:300,borderRadius:"50%",background:`radial-gradient(circle,rgba(212,168,83,.04) 0%,transparent 70%)`,animation:"orbFloat 12s ease infinite",pointerEvents:"none" }}/>
        <div style={{ position:"absolute",bottom:"15%",right:"8%",width:250,height:250,borderRadius:"50%",background:`radial-gradient(circle,rgba(52,211,153,.03) 0%,transparent 70%)`,animation:"orbFloat 15s ease infinite 3s",pointerEvents:"none" }}/>

        <div className="hero-1" style={{ display:"inline-flex",alignItems:"center",gap:8,padding:"8px 20px",borderRadius:100,border:"1px solid rgba(212,168,83,.25)",marginBottom:36,background:"rgba(212,168,83,.06)",fontSize:"clamp(11px,1.5vw,13px)",color:GOLD,letterSpacing:".05em",flexWrap:"wrap",justifyContent:"center" }}>
          <span className="live-dot" style={{ width:6,height:6,borderRadius:"50%",background:GREEN,display:"inline-block" }}/>
          <span style={{ fontFamily:"monospace",fontWeight:600 }}><LiveCounter /></span>
          <span style={{ opacity:.6 }}>RECORDS INGESTING NOW</span>
        </div>

        <h1 className="hero-2" style={{ fontFamily:"'Instrument Serif',Georgia,serif",fontSize:"clamp(36px,7.5vw,92px)",fontWeight:400,lineHeight:1.02,maxWidth:950,letterSpacing:"-.025em",padding:"0 8px" }}>
          The infrastructure layer for{" "}
          <span style={{ background:`linear-gradient(135deg,${GOLD},${GREEN},${AMETHYST},${GOLD})`,backgroundSize:"300% 300%",animation:"gradientMove 6s ease infinite",WebkitBackgroundClip:"text",WebkitTextFillColor:"transparent" }}>
            a $12 trillion industry
          </span>
        </h1>

        <p className="hero-3" style={{ fontSize:"clamp(15px,2.2vw,22px)",color:"rgba(255,255,255,.5)",maxWidth:600,lineHeight:1.65,marginTop:24,fontWeight:300,padding:"0 12px" }}>
          Healthcare still runs on fax machines, phone calls, and siloed databases. We built the knowledge graph that replaces all of it.
        </p>

        <button className="hero-4" onClick={()=>scrollTo("problem")} style={{ marginTop:40,padding:"16px 40px",borderRadius:100,border:`1px solid ${GOLD}`,background:"transparent",color:GOLD,fontSize:14,fontWeight:500,cursor:"pointer",letterSpacing:".06em",transition:`all .4s ${ease}`,fontFamily:"'DM Sans',sans-serif" }}
          onMouseEnter={e=>{e.target.style.background=GOLD;e.target.style.color=BG;e.target.style.transform="scale(1.04)";e.target.style.boxShadow=`0 0 50px rgba(212,168,83,.25)`}}
          onMouseLeave={e=>{e.target.style.background="transparent";e.target.style.color=GOLD;e.target.style.transform="scale(1)";e.target.style.boxShadow="none"}}
        >SEE THE THESIS ↓</button>

        <div className="hero-5" style={{ marginTop:48,overflow:"hidden",width:"100%",maxWidth:660,maskImage:"linear-gradient(90deg,transparent,black 15%,black 85%,transparent)",WebkitMaskImage:"linear-gradient(90deg,transparent,black 15%,black 85%,transparent)" }}>
          <div style={{ display:"flex",gap:32,animation:"tickerSlide 22s linear infinite",width:"max-content" }}>
            {[...Array(2)].flatMap(()=>["CMS","NLM","FDA","HHS-OIG","NPPES","ClinicalTrials.gov","PubMed","RxNorm","NPI Registry","ICD-10","NDC","HCPCS"]).map((s,i)=>(
              <span key={i} style={{ fontSize:11,color:"rgba(255,255,255,.18)",letterSpacing:".12em",whiteSpace:"nowrap" }}>{s}</span>
            ))}
          </div>
        </div>
      </section>

      {/* ═══════════ THE PROBLEM ═══════════ */}
      <Section id="problem">
        <div style={{ textAlign:"center",marginBottom:56 }}>
          <div style={{ fontSize:12,color:RED,letterSpacing:".15em",textTransform:"uppercase",marginBottom:16 }}>THE PROBLEM</div>
          <h2 style={{ fontFamily:"'Instrument Serif',Georgia,serif",fontSize:"clamp(26px,5vw,56px)",fontWeight:400,lineHeight:1.12,maxWidth:800,margin:"0 auto" }}>
            A <span style={{ fontStyle:"italic",color:RED }}>broken</span> industry running on <span style={{ fontStyle:"italic",color:RED }}>broken</span> infrastructure
          </h2>
        </div>
        <div style={{ display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(min(100%,280px),1fr))",gap:16,maxWidth:920,margin:"0 auto" }}>
          {[
            { num:"$3.2B",label:"Spent on manual credentialing per year",sub:"Phone calls. Fax machines. Spreadsheets. In 2026." },
            { num:"150+",label:"Days to credential a single provider",sub:"Every day a doctor waits = $7K–$10K in lost revenue." },
            { num:"0",label:"Shared knowledge layers exist",sub:"Every hospital, insurer, and startup builds from scratch." },
          ].map((item,i)=>(
            <div key={i} style={{ padding:"clamp(24px,4vw,36px) clamp(20px,3vw,28px)",background:BG_CARD,borderRadius:16,border:"1px solid rgba(255,255,255,.06)",backdropFilter:"blur(20px)",position:"relative",overflow:"hidden" }}>
              <div style={{ position:"absolute",top:-1,left:0,right:0,height:1,background:`linear-gradient(90deg,transparent,${RED}44,transparent)` }}/>
              <div style={{ fontFamily:"'Instrument Serif',Georgia,serif",fontSize:"clamp(32px,4.5vw,44px)",color:RED,marginBottom:8 }}>{item.num}</div>
              <div style={{ fontSize:"clamp(13px,1.6vw,15px)",fontWeight:600,color:"rgba(255,255,255,.85)",marginBottom:10 }}>{item.label}</div>
              <div style={{ fontSize:13,color:"rgba(255,255,255,.4)",lineHeight:1.65 }}>{item.sub}</div>
            </div>
          ))}
        </div>
      </Section>

      {/* ═══════════ THE SOLUTION ═══════════ */}
      <Section id="insight">
        <div style={{ textAlign:"center",marginBottom:56 }}>
          <div style={{ fontSize:12,color:GREEN,letterSpacing:".15em",textTransform:"uppercase",marginBottom:16 }}>THE SOLUTION</div>
          <h2 style={{ fontFamily:"'Instrument Serif',Georgia,serif",fontSize:"clamp(26px,5vw,56px)",fontWeight:400,lineHeight:1.12,maxWidth:880,margin:"0 auto" }}>
            An AI-native knowledge graph that connects{" "}
            <MorphWords words={["every provider","every drug","every diagnosis","every trial","every regulation"]} color={GREEN} />
          </h2>
          <p style={{ fontSize:"clamp(14px,1.8vw,17px)",color:"rgba(255,255,255,.45)",maxWidth:560,margin:"24px auto 0",lineHeight:1.7 }}>
            A living graph that updates itself from 17 federal data sources — and makes every AI agent on earth smarter about healthcare.
          </p>
        </div>
        <div style={{ display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(min(48%,160px),1fr))",gap:2,background:"rgba(255,255,255,.04)",borderRadius:20,overflow:"hidden",maxWidth:920,margin:"0 auto" }}>
          {[
            { emoji:"🏥",label:"Providers",count:"9.4M",sub:"Every licensed US provider" },
            { emoji:"💊",label:"Drugs",count:"83K+",sub:"NDC + interactions" },
            { emoji:"🔬",label:"Trials",count:"34K+",sub:"ClinicalTrials.gov" },
            { emoji:"📋",label:"Diagnoses",count:"97K+",sub:"Complete ICD-10" },
            { emoji:"📄",label:"Literature",count:"60K+",sub:"PubMed citations" },
            { emoji:"⚖️",label:"Regulatory",count:"83K+",sub:"OIG + board actions" },
          ].map((item,i)=>(
            <div key={i} style={{ padding:"clamp(16px,3vw,24px) 14px",background:BG_CARD,textAlign:"center" }}>
              <div style={{ fontSize:20,marginBottom:4 }}>{item.emoji}</div>
              <div style={{ fontSize:"clamp(18px,2.5vw,22px)",fontFamily:"'Instrument Serif',Georgia,serif",color:GREEN }}>{item.count}</div>
              <div style={{ fontSize:12,fontWeight:600,color:"rgba(255,255,255,.65)",marginTop:3 }}>{item.label}</div>
              <div style={{ fontSize:10,color:"rgba(255,255,255,.3)",marginTop:2 }}>{item.sub}</div>
            </div>
          ))}
        </div>
        <div style={{ textAlign:"center",marginTop:32,padding:"16px 24px",background:"rgba(52,211,153,.05)",borderRadius:12,border:`1px solid ${GREEN}18`,maxWidth:480,margin:"32px auto 0" }}>
          <div style={{ fontSize:14,color:GREEN,fontWeight:500 }}>All from free federal data. Zero licensing cost at any scale.</div>
        </div>
      </Section>

      {/* ═══════════ MISSION ═══════════ */}
      <section id="mission" style={{ position:"relative",zIndex:1,padding:"clamp(80px,14vw,140px) clamp(16px,4vw,24px)",overflow:"hidden" }}>
        <div style={{ position:"absolute",top:"50%",left:"50%",transform:"translate(-50%,-50%)",width:"min(800px,100vw)",height:"min(800px,100vw)",borderRadius:"50%",background:`radial-gradient(circle,rgba(212,168,83,.05) 0%,rgba(52,211,153,.03) 40%,transparent 70%)`,animation:"breathe 8s ease infinite",pointerEvents:"none" }}/>
        <div ref={missionRef} style={{ maxWidth:800,margin:"0 auto",textAlign:"center",position:"relative" }}>
          <div style={{ fontSize:12,color:GOLD,letterSpacing:".15em",textTransform:"uppercase",marginBottom:20,opacity:missionInView?1:0,transition:"opacity .6s ease" }}>WHY THIS MATTERS</div>
          <h2 style={{
            fontFamily:"'Instrument Serif',Georgia,serif",fontSize:"clamp(28px,5.5vw,64px)",
            fontWeight:400,lineHeight:1.1,marginBottom:48,
            opacity:missionInView?1:0,transform:missionInView?"translateY(0)":"translateY(30px)",
            transition:`all .8s ${ease} .1s`,
          }}>
            This isn't about software.<br/>It's about what happens when<br/>
            <span style={{ color:GOLD,animation:"fadeGlow 4s ease infinite" }}>the right people get their time back.</span>
          </h2>
          <div style={{ display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(min(100%,200px),1fr))",gap:16,maxWidth:700,margin:"0 auto 40px" }}>
            {[
              { word:"Healthier",sub:"Patients find the right provider, the right trial, the right answer — instantly.",color:GREEN,delay:200 },
              { word:"Wealthier",sub:"Doctors earn instead of wait. Hospitals save millions on credentialing overhead.",color:GOLD,delay:400 },
              { word:"Freer",sub:"AI handles the bureaucracy. Humans do the caring. Everyone gets their time back.",color:AMETHYST,delay:600 },
            ].map((item,i)=>(
              <div key={i} style={{
                padding:"clamp(20px,3vw,32px) clamp(16px,2.5vw,24px)",borderRadius:16,background:BG_CARD,
                border:`1px solid ${item.color}15`,backdropFilter:"blur(20px)",
                opacity:missionInView?1:0,transform:missionInView?"translateY(0)":"translateY(30px)",
                transition:`all .7s ${ease} ${item.delay}ms`,
              }}>
                <div style={{ fontFamily:"'Instrument Serif',Georgia,serif",fontSize:"clamp(24px,3.5vw,32px)",color:item.color,marginBottom:10,fontStyle:"italic" }}>{item.word}</div>
                <div style={{ fontSize:13,color:"rgba(255,255,255,.5)",lineHeight:1.7 }}>{item.sub}</div>
              </div>
            ))}
          </div>
          <div style={{
            padding:"clamp(16px,3vw,24px) clamp(20px,4vw,36px)",borderRadius:16,maxWidth:640,margin:"0 auto",
            background:`linear-gradient(135deg,rgba(212,168,83,.04),transparent)`,border:`1px solid rgba(212,168,83,.1)`,
            opacity:missionInView?1:0,transform:missionInView?"translateY(0)":"translateY(20px)",
            transition:`all .8s ${ease} .8s`,
          }}>
            <div style={{ fontSize:"clamp(14px,1.8vw,17px)",color:"rgba(255,255,255,.7)",lineHeight:1.8,fontWeight:300 }}>
              Every AI pitch says <span style={{ fontStyle:"italic",opacity:.5 }}>"we'll make people more productive."</span>
              <br/>This is the <span style={{ color:GOLD,fontWeight:500 }}>living proof</span>.
              One founder. Three verticals. 4 million records and counting tonight.
              <br/><span style={{ color:GREEN,fontWeight:500 }}>AI doesn't replace people. It returns their time to them.</span>
            </div>
          </div>
        </div>
      </section>

      {/* ═══════════ THE MOAT ═══════════ */}
      <Section id="moat">
        <div ref={moatRef} style={{ textAlign:"center",marginBottom:56 }}>
          <div style={{ fontSize:12,color:AMETHYST,letterSpacing:".15em",textTransform:"uppercase",marginBottom:16 }}>THE MOAT</div>
          <h2 style={{ fontFamily:"'Instrument Serif',Georgia,serif",fontSize:"clamp(26px,5vw,56px)",fontWeight:400,lineHeight:1.12,maxWidth:850,margin:"0 auto" }}>
            Every AI agent on earth<br/>will cite <span style={{ fontStyle:"italic",color:AMETHYST }}>us</span>
          </h2>
          <p style={{ fontSize:"clamp(14px,1.8vw,17px)",color:"rgba(255,255,255,.42)",maxWidth:600,margin:"24px auto 0",lineHeight:1.7 }}>
            Every entity URL serves structured JSON-LD + llms.txt. When AI answers a healthcare question, HKG is the source it cites. A moat that compounds with every AI query on earth.
          </p>
        </div>
        <div style={{ maxWidth:700,margin:"0 auto",background:BG_CARD,borderRadius:16,border:`1px solid ${AMETHYST}18`,padding:"clamp(24px,4vw,36px) clamp(20px,3.5vw,32px)",position:"relative",overflow:"hidden",backdropFilter:"blur(20px)" }}>
          <div style={{ position:"absolute",top:0,left:0,right:0,height:2,background:`linear-gradient(90deg,transparent,${AMETHYST},transparent)` }}/>
          <div style={{ fontSize:12,color:AMETHYST,letterSpacing:".08em",marginBottom:20,fontFamily:"monospace" }}>{'>'} THE FLYWHEEL</div>
          {[
            { step:"01",text:"Someone asks AI about metformin side effects",icon:"🔍" },
            { step:"02",text:"AI finds HKG's structured data — the most citable source",icon:"🧠" },
            { step:"03",text:"AI cites HKG → organic traffic → zero acquisition cost",icon:"📈" },
            { step:"04",text:"Traffic builds authority → more citations → permanent loop",icon:"♾️" },
          ].map((item,i)=>(
            <div key={i} style={{
              display:"flex",alignItems:"center",gap:"clamp(8px,2vw,16px)",padding:"12px 0",
              borderBottom:i<3?"1px solid rgba(255,255,255,.04)":"none",
              opacity:moatInView?1:0,transform:moatInView?"translateX(0)":"translateX(-30px)",
              transition:`all .6s ${ease} ${i*120}ms`,
            }}>
              <span style={{ fontSize:18,width:32,textAlign:"center",flexShrink:0 }}>{item.icon}</span>
              <span style={{ fontFamily:"monospace",color:AMETHYST,fontSize:11,opacity:.4,flexShrink:0 }}>{item.step}</span>
              <span style={{ fontSize:"clamp(13px,1.6vw,15px)",color:"rgba(255,255,255,.75)",lineHeight:1.5 }}>{item.text}</span>
            </div>
          ))}
          <div style={{ marginTop:20,padding:"14px 18px",background:`rgba(167,139,250,.04)`,borderRadius:10,border:`1px solid rgba(167,139,250,.08)` }}>
            <div style={{ fontSize:14,fontWeight:600,color:AMETHYST }}>Zero marginal distribution cost. Infinite compounding.</div>
            <div style={{ fontSize:12,color:"rgba(255,255,255,.35)",marginTop:4 }}>As AI scales globally, our reach scales with it. No marketing spend.</div>
          </div>
        </div>
      </Section>

      {/* ═══════════ ECONOMICS ═══════════ */}
      <Section id="model">
        <div ref={modelRef} style={{ textAlign:"center",marginBottom:56 }}>
          <div style={{ fontSize:12,color:GOLD,letterSpacing:".15em",textTransform:"uppercase",marginBottom:16 }}>THE ECONOMIC ENGINE</div>
          <h2 style={{ fontFamily:"'Instrument Serif',Georgia,serif",fontSize:"clamp(26px,5vw,56px)",fontWeight:400,lineHeight:1.12,maxWidth:900,margin:"0 auto" }}>
            Four revenue layers.<br/><span style={{ fontStyle:"italic",color:GOLD }}>Each one funds the next.</span>
          </h2>
        </div>
        <div style={{ maxWidth:800,margin:"0 auto",display:"flex",flexDirection:"column",gap:12 }}>
          {[
            { layer:"01",color:RED,label:"Verification & Credentialing",who:"Hospitals · Insurers · Staffing",how:"$0.50–$2/query · $15–50/provider/mo · $50K–150K/yr enterprise",why:"Regulatory mandate. Hospitals cannot legally operate without it.",tag:"MANDATORY SPEND" },
            { layer:"02",color:GREEN,label:"Doctor Platform",who:"Physicians · CME · Recruiters",how:"CME affiliate (15–25%) · Recruiter fees · Premium portfolios",why:"Every provider recredentials every 2–3 years. Permanent lifecycle revenue.",tag:"RECURRING" },
            { layer:"03",color:AMETHYST,label:"Machine Lane / API",who:"AI companies · EHR vendors · Healthtech",how:"$99–$2,499/mo usage-based · MCP server · Enterprise feeds",why:"Every healthcare AI needs structured, citable data. We're the only source.",tag:"SCALES WITH AI" },
            { layer:"04",color:GOLD,label:"Intelligence & Analytics",who:"Pharma · Payers · Government",how:"$50K–$500K/yr enterprise · Population health · Workforce planning",why:"The graph reveals relationships no flat database can. Pure margin.",tag:"HIGH MARGIN" },
          ].map((item,i)=>(
            <div key={i} style={{
              background:BG_CARD,borderRadius:16,padding:"clamp(18px,3vw,26px) clamp(18px,3vw,28px)",
              border:`1px solid ${item.color}15`,position:"relative",overflow:"hidden",backdropFilter:"blur(20px)",
              opacity:modelInView?1:0,transform:modelInView?"translateX(0)":"translateX(-30px)",
              transition:`all .6s ${ease} ${i*120}ms`,
            }}>
              <div style={{ position:"absolute",top:0,left:0,bottom:0,width:3,background:item.color,opacity:.5 }}/>
              <div style={{ display:"flex",justifyContent:"space-between",alignItems:"flex-start",flexWrap:"wrap",gap:8,marginBottom:8 }}>
                <div style={{ display:"flex",alignItems:"center",gap:10 }}>
                  <span style={{ fontFamily:"monospace",fontSize:11,color:item.color,opacity:.4 }}>{item.layer}</span>
                  <span style={{ fontSize:"clamp(14px,1.8vw,17px)",fontWeight:600,color:item.color }}>{item.label}</span>
                </div>
                <span style={{ fontSize:9,letterSpacing:".1em",color:item.color,padding:"3px 10px",borderRadius:100,border:`1px solid ${item.color}28`,background:`${item.color}06` }}>{item.tag}</span>
              </div>
              <div style={{ fontSize:12,color:"rgba(255,255,255,.4)",marginBottom:4 }}>{item.who}</div>
              <div style={{ fontSize:"clamp(11px,1.4vw,13px)",color:"rgba(255,255,255,.7)",fontFamily:"monospace",marginBottom:6,lineHeight:1.6 }}>{item.how}</div>
              <div style={{ fontSize:13,color:"rgba(255,255,255,.42)",fontStyle:"italic" }}>{item.why}</div>
            </div>
          ))}
        </div>
        {/* Recession callout */}
        <div style={{
          maxWidth:800,margin:"32px auto 0",padding:"clamp(18px,3vw,24px) clamp(20px,3vw,28px)",borderRadius:16,
          background:`linear-gradient(135deg,rgba(52,211,153,.03),rgba(212,168,83,.03))`,border:"1px solid rgba(255,255,255,.05)",
          opacity:modelInView?1:0,transition:`all .8s ease .6s`,position:"relative",overflow:"hidden",
        }}>
          <div style={{ position:"absolute",top:0,left:0,right:0,height:1,background:`linear-gradient(90deg,${GREEN}33,${GOLD}33)` }}/>
          <div style={{ display:"flex",alignItems:"flex-start",gap:"clamp(12px,3vw,20px)",flexWrap:"wrap" }}>
            <div>
              <div style={{ fontFamily:"'Instrument Serif',Georgia,serif",fontSize:"clamp(36px,5vw,48px)",color:GREEN,lineHeight:1 }}>0</div>
              <div style={{ fontSize:10,color:"rgba(255,255,255,.35)",marginTop:4,letterSpacing:".05em" }}>TIMES HEALTHCARE<br/>HAS CONTRACTED Y/Y</div>
            </div>
            <div style={{ flex:1,minWidth:200 }}>
              <div style={{ fontSize:15,fontWeight:600,color:"rgba(255,255,255,.8)",marginBottom:6 }}>Recession-proof by design.</div>
              <div style={{ fontSize:13,color:"rgba(255,255,255,.42)",lineHeight:1.7 }}>
                Healthcare is 18% of GDP and has never contracted. Downturns <span style={{ color:GREEN }}>accelerate</span> our model: hospitals cut headcount → buy automation. AI adoption rises → more API queries. Compliance scrutiny intensifies → more verification.
              </div>
            </div>
          </div>
        </div>
      </Section>

      {/* ═══════════ PATTERN ═══════════ */}
      <Section id="pattern">
        <div style={{ textAlign:"center",marginBottom:56 }}>
          <div style={{ fontSize:12,color:GREEN,letterSpacing:".15em",textTransform:"uppercase",marginBottom:16 }}>THE PATTERN</div>
          <h2 style={{ fontFamily:"'Instrument Serif',Georgia,serif",fontSize:"clamp(26px,5vw,52px)",fontWeight:400,lineHeight:1.12 }}>
            Third vertical. <span style={{ fontStyle:"italic",color:GREEN }}>Same playbook.</span>
          </h2>
        </div>
        <div style={{ display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(min(100%,260px),1fr))",gap:14,maxWidth:900,margin:"0 auto" }}>
          {[
            { name:"BKG",full:"Builder's Knowledge Garden",market:"$17T Construction",status:"DEPLOYED",color:"#F97316" },
            { name:"OKG",full:"Orchid Knowledge Garden",market:"Botanical / Ecuagenera",status:"DEPLOYED",color:GREEN },
            { name:"HKG",full:"Healthcare Knowledge Garden",market:"$12T+ Healthcare",status:"LIVE · INGESTING",color:GOLD },
          ].map((v,i)=>(
            <div key={i} style={{ padding:"clamp(24px,4vw,36px) clamp(20px,3vw,28px)",background:BG_CARD,borderRadius:16,border:`1px solid ${v.color}18`,position:"relative",overflow:"hidden",backdropFilter:"blur(20px)" }}>
              {v.name==="HKG"&&<>
                <div style={{ position:"absolute",top:0,left:0,right:0,height:2,background:`linear-gradient(90deg,transparent,${v.color},transparent)`,animation:"gradientMove 3s ease infinite" }}/>
                <div style={{ position:"absolute",top:16,right:16,width:36,height:36,borderRadius:"50%",border:`1px solid ${GOLD}33`,animation:"ringPulse 3s ease infinite" }}/>
              </>}
              <div style={{ fontSize:11,letterSpacing:".12em",color:v.color,marginBottom:12,display:"flex",alignItems:"center",gap:8 }}>
                {v.name==="HKG"&&<span className="live-dot" style={{ width:6,height:6,borderRadius:"50%",background:v.color,display:"inline-block" }}/>}
                {v.status}
              </div>
              <div style={{ fontFamily:"'Instrument Serif',Georgia,serif",fontSize:"clamp(28px,4vw,40px)",color:v.color }}>{v.name}</div>
              <div style={{ fontSize:14,color:"rgba(255,255,255,.55)",marginTop:6 }}>{v.full}</div>
              <div style={{ fontSize:13,color:"rgba(255,255,255,.3)",marginTop:4 }}>{v.market}</div>
            </div>
          ))}
        </div>
        <div style={{ textAlign:"center",marginTop:32 }}>
          <div style={{ fontSize:14,color:"rgba(255,255,255,.4)",fontStyle:"italic",maxWidth:460,margin:"0 auto",lineHeight:1.7 }}>
            Same architecture. Same surfaces. Same RSI flywheel.
            <br/><span style={{ color:"rgba(255,255,255,.6)" }}>Morning Briefings delivered 5x dashboard engagement in OKG.</span>
          </div>
        </div>
      </Section>

      {/* ═══════════ TRACTION ═══════════ */}
      <Section id="traction">
        <div ref={tractionRef} style={{ textAlign:"center",marginBottom:44 }}>
          <div style={{ fontSize:12,color:GOLD,letterSpacing:".15em",textTransform:"uppercase",marginBottom:16 }}>WHAT'S BUILT</div>
          <h2 style={{ fontFamily:"'Instrument Serif',Georgia,serif",fontSize:"clamp(26px,5vw,52px)",fontWeight:400,lineHeight:1.12 }}>
            This is not a <span style={{ fontStyle:"italic",color:GOLD }}>pitch.</span><br/>It's a progress report.
          </h2>
        </div>
        <div style={{ display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(min(48%,180px),1fr))",gap:8,maxWidth:900,margin:"0 auto" }}>
          <Stat trigger={tractionInView} number={4000000} suffix="+" label="Records Ingested" color={GOLD} delay={0} />
          <Stat trigger={tractionInView} number={28} label="Table Schema" color={GREEN} delay={100} />
          <Stat trigger={tractionInView} number={17} label="Federal Sources" color={AMETHYST} delay={200} />
          <Stat trigger={tractionInView} number={22} label="Ingestion Scripts" color={RED} delay={300} />
        </div>
        <div style={{ maxWidth:700,margin:"40px auto 0",padding:"24px 28px",borderRadius:16,background:BG_CARD,border:"1px solid rgba(255,255,255,.05)",backdropFilter:"blur(20px)" }}>
          <div style={{ fontSize:12,color:"rgba(255,255,255,.25)",letterSpacing:".1em",marginBottom:14 }}>TECH STACK</div>
          <div style={{ display:"flex",flexWrap:"wrap",gap:8 }}>
            {["Neo4j","Supabase","Claude API","MCP","Next.js","React","Three.js","Python"].map(t=>(
              <span key={t} style={{ padding:"5px 13px",borderRadius:100,fontSize:12,background:"rgba(255,255,255,.03)",border:"1px solid rgba(255,255,255,.07)",color:"rgba(255,255,255,.45)" }}>{t}</span>
            ))}
          </div>
        </div>
        <div style={{ textAlign:"center",marginTop:28 }}>
          <div style={{ fontSize:14,color:"rgba(255,255,255,.35)",fontStyle:"italic" }}>
            One founder. Zero external capital.
            <br/><span style={{ color:GOLD }}>Imagine what a funded team does with this in 6 months.</span>
          </div>
        </div>
      </Section>

      {/* ═══════════ OPPORTUNITY ═══════════ */}
      <Section id="opportunity">
        <div ref={oppRef} style={{ textAlign:"center",marginBottom:56 }}>
          <div style={{ fontSize:12,color:GOLD,letterSpacing:".15em",textTransform:"uppercase",marginBottom:16 }}>THE WINDOW</div>
          <h2 style={{ fontFamily:"'Instrument Serif',Georgia,serif",fontSize:"clamp(26px,5vw,56px)",fontWeight:400,lineHeight:1.12 }}>
            The timing is <span style={{ fontStyle:"italic",color:RED }}>closing</span>
          </h2>
        </div>
        <div style={{ display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(min(48%,200px),1fr))",gap:12,maxWidth:900,margin:"0 auto" }}>
          {[
            { value:"$12T+",label:"Global Healthcare Market",color:GOLD },
            { value:"$394B",label:"Healthcare IT by 2027",color:GREEN },
            { value:"$75B",label:"Health Data Analytics by 2030",color:AMETHYST },
            { value:"$3.2B",label:"Credentialing (12% CAGR)",color:RED },
          ].map((m,i)=>(
            <div key={i} style={{
              textAlign:"center",padding:"clamp(20px,4vw,32px) 14px",borderRadius:16,
              background:BG_CARD,border:`1px solid ${m.color}10`,backdropFilter:"blur(20px)",
              opacity:oppInView?1:0,transform:oppInView?"scale(1)":"scale(.92)",
              transition:`all .6s ${ease} ${i*100}ms`,
            }}>
              <div style={{ fontFamily:"'Instrument Serif',Georgia,serif",fontSize:"clamp(28px,4.5vw,38px)",color:m.color }}>{m.value}</div>
              <div style={{ fontSize:12,color:"rgba(255,255,255,.4)",marginTop:8,lineHeight:1.5 }}>{m.label}</div>
            </div>
          ))}
        </div>
        <div style={{ textAlign:"center",marginTop:44,maxWidth:600,margin:"44px auto 0" }}>
          <p style={{ fontSize:"clamp(14px,1.8vw,17px)",color:"rgba(255,255,255,.48)",lineHeight:1.8 }}>
            AI is becoming the primary interface for healthcare information. The platform that becomes the <span style={{ color:GOLD,fontWeight:500 }}>canonical source of truth</span> captures a position that <span style={{ color:GREEN,fontWeight:500 }}>compounds permanently</span>.
          </p>
          <p style={{ fontSize:16,color:RED,fontWeight:500,marginTop:18 }}>That window doesn't stay open.</p>
        </div>
      </Section>

      {/* ═══════════ CTA ═══════════ */}
      <section id="cta" style={{ minHeight:"85vh",minHeight:"85dvh",display:"flex",flexDirection:"column",justifyContent:"center",alignItems:"center",textAlign:"center",padding:"80px clamp(16px,4vw,24px)",position:"relative",zIndex:1 }}>
        <div style={{ position:"absolute",top:"50%",left:"50%",transform:"translate(-50%,-50%)",width:"min(600px,90vw)",height:"min(600px,90vw)",borderRadius:"50%",background:`radial-gradient(circle,rgba(212,168,83,.05) 0%,transparent 60%)`,animation:"breathe 6s ease infinite",pointerEvents:"none" }}/>
        <div style={{ position:"absolute",top:"50%",left:"50%",transform:"translate(-50%,-50%)",width:"min(400px,70vw)",height:"min(400px,70vw)",borderRadius:"50%",border:`1px solid rgba(212,168,83,.06)`,animation:"ringPulse 4s ease infinite",pointerEvents:"none" }}/>

        <h2 style={{ fontFamily:"'Instrument Serif',Georgia,serif",fontSize:"clamp(30px,6vw,72px)",fontWeight:400,lineHeight:1.08,maxWidth:750,position:"relative" }}>
          The future of healthcare<br/>
          <span style={{ animation:"fadeGlow 4s ease infinite" }}>is being built </span>
          <span style={{ color:GREEN }}>tonight.</span>
        </h2>
        <p style={{ fontSize:"clamp(15px,2vw,18px)",color:"rgba(255,255,255,.4)",marginTop:24,maxWidth:420,lineHeight:1.7 }}>
          We're looking for investors and builders who want to own the infrastructure layer for a $12 trillion industry.
        </p>
        <div style={{ display:"flex",gap:14,marginTop:40,flexWrap:"wrap",justifyContent:"center" }}>
          <a href="mailto:chilly@xrworkers.com" style={{
            padding:"16px 40px",borderRadius:100,background:GOLD,color:BG,
            fontSize:15,fontWeight:600,textDecoration:"none",letterSpacing:".02em",
            transition:`all .4s ${ease}`,display:"inline-block",
          }}
            onMouseEnter={e=>{e.target.style.transform="scale(1.06)";e.target.style.boxShadow=`0 0 60px rgba(212,168,83,.3)`}}
            onMouseLeave={e=>{e.target.style.transform="scale(1)";e.target.style.boxShadow="none"}}
          >LET'S TALK</a>
          <a href="#hero" style={{
            padding:"16px 40px",borderRadius:100,border:"1px solid rgba(255,255,255,.12)",
            color:"rgba(255,255,255,.5)",fontSize:15,fontWeight:500,textDecoration:"none",transition:"all .3s ease",
          }}
            onMouseEnter={e=>{e.target.style.borderColor="rgba(255,255,255,.35)";e.target.style.color="#fff"}}
            onMouseLeave={e=>{e.target.style.borderColor="rgba(255,255,255,.12)";e.target.style.color="rgba(255,255,255,.5)"}}
          >BACK TO TOP</a>
        </div>
        <div style={{ marginTop:56,fontSize:11,color:"rgba(255,255,255,.15)",letterSpacing:".12em" }}>
          © 2026 XRWORKERS · HEALTHCARE KNOWLEDGE GARDEN
        </div>
      </section>
    </div>
  );
}
