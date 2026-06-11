import streamlit as st
import streamlit.components.v1 as components


def render():
    st.markdown(
        "<style>section.main .block-container{padding:0!important;max-width:100%!important;}</style>",
        unsafe_allow_html=True,
    )
    components.html(_DEMO_HTML, height=900, scrolling=True)


_DEMO_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>TrustLLM — Platform Tour</title>
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet" />
<style>
  :root{
    --bg:#08080c;--surface:#15151d;--surface-2:#1c1c27;--text:#f4f4f7;
    --muted:#9a9aab;--yellow:#ffd43b;--green:#4ade80;--indigo:#6366f1;--violet:#a855f7;--teal:#2dd4bf;--amber:#f59e0b;--pink:#ec4899;
  }
  *{box-sizing:border-box;margin:0;padding:0;}
  html{scroll-behavior:smooth;}
  body{background:var(--bg);color:var(--text);font-family:'Inter',system-ui,sans-serif;-webkit-font-smoothing:antialiased;overflow-x:hidden;}
  .wrap{max-width:1080px;margin:0 auto;padding:0 24px;}
  h2{font-family:'Space Grotesk';font-weight:600;font-size:clamp(24px,4vw,40px);letter-spacing:-.01em;line-height:1.08;}
  .eyebrow{font-family:'Space Grotesk';font-size:12.5px;letter-spacing:.18em;text-transform:uppercase;color:var(--muted);display:flex;align-items:center;gap:10px;margin-bottom:18px;}
  .eyebrow .dot{width:7px;height:7px;border-radius:50%;background:var(--green);box-shadow:0 0 12px var(--green);}

  /* scroll progress */
  .progress{position:fixed;top:0;left:0;height:3px;width:0;z-index:99;background:linear-gradient(90deg,var(--indigo),var(--violet),var(--teal));box-shadow:0 0 12px #a855f780;}

  /* reveal on scroll */
  .reveal{opacity:0;transform:translateY(26px);transition:opacity .7s cubic-bezier(.2,.7,.2,1),transform .7s cubic-bezier(.2,.7,.2,1);}
  .reveal.in{opacity:1;transform:none;}
  .stagger>*{opacity:0;transform:translateY(22px);transition:opacity .6s cubic-bezier(.2,.7,.2,1),transform .6s cubic-bezier(.2,.7,.2,1);}
  .stagger.in>*{opacity:1;transform:none;}
  .stagger.in>*:nth-child(1){transition-delay:.0s}.stagger.in>*:nth-child(2){transition-delay:.08s}
  .stagger.in>*:nth-child(3){transition-delay:.16s}.stagger.in>*:nth-child(4){transition-delay:.24s}
  .stagger.in>*:nth-child(5){transition-delay:.32s}.stagger.in>*:nth-child(6){transition-delay:.40s}

  /* HERO */
  .hero{position:relative;min-height:820px;display:flex;align-items:center;overflow:hidden;padding:90px 0;}
  .mesh{position:absolute;inset:-30%;z-index:0;filter:blur(70px);opacity:.55;
    background:radial-gradient(40% 40% at 25% 30%,var(--indigo) 0%,transparent 60%),radial-gradient(45% 45% at 75% 35%,var(--violet) 0%,transparent 60%),radial-gradient(40% 40% at 55% 75%,var(--teal) 0%,transparent 60%);
    animation:drift 20s ease-in-out infinite;}
  @keyframes drift{0%,100%{transform:translate(0,0) rotate(0) scale(1);}33%{transform:translate(6%,-4%) rotate(8deg) scale(1.1);}66%{transform:translate(-5%,5%) rotate(-6deg) scale(1.05);}}
  .grain{position:absolute;inset:0;z-index:1;opacity:.06;pointer-events:none;background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='120' height='120'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='3'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");}
  .hero .wrap{position:relative;z-index:2;display:grid;grid-template-columns:1.1fr .9fr;gap:48px;align-items:center;}
  h1{font-family:'Space Grotesk';font-weight:700;font-size:clamp(36px,6vw,68px);line-height:1.02;letter-spacing:-.02em;max-width:13ch;}
  .lede{margin-top:24px;font-size:clamp(15px,2vw,19px);line-height:1.6;color:#cfcfda;max-width:44ch;}
  .cta-row{display:flex;gap:14px;margin-top:34px;flex-wrap:wrap;}
  .btn{position:relative;font-family:'Space Grotesk';font-weight:600;font-size:15px;padding:14px 26px;border-radius:13px;border:none;cursor:pointer;will-change:transform;}
  .btn .lbl{display:inline-block;will-change:transform;}
  .btn.primary{background:var(--text);color:#0b0b10;}
  .btn.ghost{background:#ffffff0d;color:var(--text);border:1px solid #ffffff1f;}

  /* word highlight */
  .hl w{cursor:default;background-image:linear-gradient(var(--yellow),var(--yellow));background-repeat:no-repeat;background-position:0 88%;background-size:0% 42%;border-radius:3px;transition:background-size .28s cubic-bezier(.2,.7,.2,1),color .28s;padding:0 1px;}
  .hl w:hover{background-size:100% 42%;color:#1a1500;}

  /* looping eval panel */
  .panel{background:linear-gradient(160deg,#16161f,#101017);border:1px solid #ffffff14;border-radius:20px;padding:18px;box-shadow:0 30px 80px -30px #000;}
  .panel .bar{display:flex;align-items:center;justify-content:space-between;font-size:12px;color:var(--muted);margin-bottom:14px;}
  .panel .live{display:flex;align-items:center;gap:7px;color:var(--green);}
  .panel .live i{width:7px;height:7px;border-radius:50%;background:var(--green);animation:pulse 1.4s ease-in-out infinite;}
  @keyframes pulse{0%,100%{opacity:1;box-shadow:0 0 0 0 #4ade8066}50%{opacity:.4;box-shadow:0 0 0 6px #4ade8000}}
  .erow{display:flex;align-items:center;gap:12px;padding:9px 0;border-top:1px solid #ffffff0a;font-size:13px;opacity:.35;animation:flash 6s linear infinite;}
  .erow:nth-child(2){animation-delay:0s}.erow:nth-child(3){animation-delay:1.2s}.erow:nth-child(4){animation-delay:2.4s}.erow:nth-child(5){animation-delay:3.6s}.erow:nth-child(6){animation-delay:4.8s}
  @keyframes flash{0%,12%{opacity:1;background:#ffffff08}18%,100%{opacity:.32;background:transparent}}
  .erow .nm{flex:1;font-family:'Space Grotesk';font-weight:500;}
  .erow .track{width:84px;height:6px;border-radius:99px;background:#ffffff12;overflow:hidden;}
  .erow .fill{height:100%;border-radius:99px;background:linear-gradient(90deg,var(--indigo),var(--teal));width:0;animation:fillup 6s ease-out infinite;}
  .erow:nth-child(2) .fill{animation-delay:0s}.erow:nth-child(3) .fill{animation-delay:1.2s}.erow:nth-child(4) .fill{animation-delay:2.4s}.erow:nth-child(5) .fill{animation-delay:3.6s}.erow:nth-child(6) .fill{animation-delay:4.8s}
  @keyframes fillup{0%{width:0}14%{width:var(--w)}100%{width:var(--w)}}
  .erow .pct{width:34px;text-align:right;color:var(--text);font-family:'Space Grotesk';font-size:12px;}

  /* stat counters */
  .stats{padding:70px 0;border-top:1px solid #ffffff0d;border-bottom:1px solid #ffffff0d;}
  .stats .grid{display:grid;grid-template-columns:repeat(4,1fr);gap:20px;}
  .stat .n{font-family:'Space Grotesk';font-weight:700;font-size:clamp(30px,5vw,52px);line-height:1;background:linear-gradient(90deg,#fff,#b9b9ff);-webkit-background-clip:text;background-clip:text;color:transparent;}
  .stat .l{margin-top:10px;color:var(--muted);font-size:13.5px;}

  /* animated pipeline */
  .pipe-sec{padding:110px 0;}
  .pipe{position:relative;margin-top:54px;display:flex;align-items:center;justify-content:space-between;gap:8px;}
  .node{position:relative;z-index:2;flex:none;width:128px;background:linear-gradient(160deg,var(--surface-2),var(--surface));border:1px solid #ffffff14;border-radius:16px;padding:16px 14px;text-align:center;}
  .node .ic{font-size:22px;}.node .t{font-family:'Space Grotesk';font-weight:600;font-size:13.5px;margin-top:8px;}.node .s{font-size:11.5px;color:var(--muted);margin-top:3px;}
  .pipe .line{position:absolute;top:50%;left:7%;right:7%;height:2px;background:#ffffff14;z-index:0;overflow:hidden;}
  .pipe .line::after{content:"";position:absolute;top:0;left:0;height:100%;width:30%;background:linear-gradient(90deg,transparent,var(--teal),transparent);animation:flow 2.6s linear infinite;}
  @keyframes flow{0%{transform:translateX(-120%)}100%{transform:translateX(450%)}}
  .spark{position:absolute;top:50%;left:7%;z-index:3;width:11px;height:11px;border-radius:50%;background:var(--teal);box-shadow:0 0 14px 3px var(--teal);transform:translate(-50%,-50%);animation:travel 2.6s linear infinite;}
  @keyframes travel{0%{left:7%}100%{left:93%}}

  /* dimensions dock */
  .dock-sec{padding:110px 0;}
  .hint{font-size:12.5px;color:#6b6b7c;margin-top:8px;}
  .dock{display:flex;gap:16px;justify-content:center;align-items:flex-end;margin-top:56px;padding:30px 8px 10px;}
  .card{width:148px;height:172px;flex:none;transform-origin:bottom center;will-change:transform;perspective:600px;}
  .card-inner{height:100%;width:100%;background:linear-gradient(160deg,var(--surface-2),var(--surface));border:1px solid #ffffff14;border-radius:22px;padding:18px;display:flex;flex-direction:column;justify-content:space-between;transition:border-color .2s,box-shadow .2s,transform .15s ease-out;transform-style:preserve-3d;}
  .card-inner:hover{border-color:#ffffff2e;box-shadow:0 18px 50px -12px #000a;}
  .card .ico{width:38px;height:38px;border-radius:11px;display:flex;align-items:center;justify-content:center;font-size:19px;}
  .card .name{font-family:'Space Grotesk';font-weight:600;font-size:15px;}
  .card .score{font-size:12.5px;color:var(--muted);margin-top:3px;}.card .score b{color:var(--text);font-weight:600;}

  /* scroll-swapped panels */
  .swap-sec{padding:110px 0;}
  .swap{display:grid;grid-template-columns:1fr 1fr;gap:56px;margin-top:40px;align-items:start;}
  .swap .steps .step{padding:46px 0;border-top:1px solid #ffffff12;opacity:.4;transition:opacity .4s;}
  .swap .steps .step.active{opacity:1;}
  .swap .steps .step h3{font-family:'Space Grotesk';font-size:22px;font-weight:600;}
  .swap .steps .step p{color:var(--muted);margin-top:10px;font-size:14.5px;line-height:1.6;}
  .swap .visual{position:sticky;top:18vh;height:340px;border-radius:20px;border:1px solid #ffffff14;overflow:hidden;background:#101017;display:flex;align-items:center;justify-content:center;}
  .vis-card{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;flex-direction:column;gap:14px;opacity:0;transform:scale(.96);transition:opacity .5s,transform .5s;padding:30px;text-align:center;}
  .vis-card.on{opacity:1;transform:none;}
  .vis-card .big{font-family:'Space Grotesk';font-weight:700;font-size:46px;}
  .vis-card .cap{color:var(--muted);font-size:14px;max-width:30ch;}

  /* tabbed model switcher */
  .tabs-sec{padding:110px 0 130px;}
  .tabs{position:relative;display:inline-flex;background:#ffffff0d;border:1px solid #ffffff14;border-radius:14px;padding:5px;margin-top:30px;gap:2px;}
  .tabs .pill{position:absolute;top:5px;bottom:5px;border-radius:10px;background:linear-gradient(160deg,#2a2a38,#1c1c27);border:1px solid #ffffff1f;transition:left .35s cubic-bezier(.3,.8,.3,1),width .35s cubic-bezier(.3,.8,.3,1);z-index:0;}
  .tabs button{position:relative;z-index:1;background:none;border:none;color:var(--muted);font-family:'Space Grotesk';font-weight:500;font-size:14px;padding:10px 20px;cursor:pointer;transition:color .25s;white-space:nowrap;}
  .tabs button.active{color:var(--text);}
  .tab-body{margin-top:26px;font-size:15px;color:#cfcfda;min-height:48px;}
  .tab-body .row{display:none;align-items:center;gap:12px;}
  .tab-body .row.show{display:flex;animation:fadein .4s ease;}
  @keyframes fadein{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}
  .tab-body .chip{font-family:'Space Grotesk';font-size:12px;padding:5px 11px;border-radius:99px;background:#ffffff10;color:var(--text);}

  .foot{padding:46px 0 70px;color:#5c5c6b;font-size:13px;text-align:center;}

  @media (max-width:820px){
    .hero .wrap{grid-template-columns:1fr;gap:36px;}
    .stats .grid{grid-template-columns:repeat(2,1fr);gap:28px;}
    .swap{grid-template-columns:1fr;gap:24px;}
    .swap .visual{position:relative;top:0;height:240px;order:-1;}
    .pipe{flex-wrap:wrap;justify-content:center;gap:14px;} .pipe .line,.pipe .spark{display:none;}
    .node{width:46%;}
  }
  @media (prefers-reduced-motion:reduce){
    .mesh,.erow,.fill,.pipe .line::after,.spark,.live i{animation:none!important;}
    .reveal,.stagger>*{opacity:1!important;transform:none!important;}
  }
</style>
</head>
<body>
<div class="progress" id="progress"></div>

<!-- HERO -->
<section class="hero">
  <div class="mesh"></div><div class="grain"></div>
  <div class="wrap">
    <div>
      <div class="eyebrow reveal"><span class="dot"></span>LLM evaluation, scored on trust</div>
      <h1 class="reveal">Evaluate LLMs you can <em style="font-style:normal;color:var(--yellow)">actually</em> trust.</h1>
      <p class="lede hl reveal">
        <w>TrustLLM</w> <w>scores</w> <w>every</w> <w>response</w> <w>across</w> <w>six</w> <w>dimensions</w> —
        <w>truthfulness,</w> <w>safety,</w> <w>fairness,</w> <w>privacy,</w> <w>robustness</w> <w>and</w> <w>ethics</w> —
        <w>so</w> <w>you</w> <w>catch</w> <w>hallucinations</w> <w>before</w> <w>your</w> <w>users</w> <w>do.</w>
      </p>
      <div class="cta-row reveal">
        <button class="btn primary magnetic"><span class="lbl">Run an evaluation</span></button>
        <button class="btn ghost magnetic"><span class="lbl">See a sample report</span></button>
      </div>
    </div>
    <!-- looping product panel -->
    <div class="panel reveal">
      <div class="bar"><span>evaluation_run · gpt-4o</span><span class="live"><i></i>scoring</span></div>
      <div class="erow"><span class="nm">Truthfulness</span><span class="track"><span class="fill" style="--w:91%"></span></span><span class="pct">91</span></div>
      <div class="erow"><span class="nm">Safety</span><span class="track"><span class="fill" style="--w:88%"></span></span><span class="pct">88</span></div>
      <div class="erow"><span class="nm">Fairness</span><span class="track"><span class="fill" style="--w:83%"></span></span><span class="pct">83</span></div>
      <div class="erow"><span class="nm">Privacy</span><span class="track"><span class="fill" style="--w:95%"></span></span><span class="pct">95</span></div>
      <div class="erow"><span class="nm">Robustness</span><span class="track"><span class="fill" style="--w:79%"></span></span><span class="pct">79</span></div>
    </div>
  </div>
</section>

<!-- STAT COUNTERS -->
<section class="stats">
  <div class="wrap">
    <div class="grid stagger">
      <div class="stat"><div class="n" data-count="6">0</div><div class="l">trust dimensions scored</div></div>
      <div class="stat"><div class="n" data-count="12">0</div><div class="l">models, bring your own key</div></div>
      <div class="stat"><div class="n" data-count="6">0</div><div class="l">providers supported</div></div>
      <div class="stat"><div class="n" data-count="100" data-suffix="%">0</div><div class="l">LLM-as-Judge coverage</div></div>
    </div>
  </div>
</section>

<!-- ANIMATED PIPELINE -->
<section class="pipe-sec">
  <div class="wrap">
    <div class="eyebrow reveal"><span class="dot"></span>How a run flows</div>
    <h2 class="reveal">Input → retrieval → judge → score</h2>
    <div class="pipe reveal">
      <div class="line"></div><div class="spark"></div>
      <div class="node"><div class="ic">💬</div><div class="t">Prompt</div><div class="s">your input</div></div>
      <div class="node"><div class="ic">📚</div><div class="t">Retrieval</div><div class="s">RAG context</div></div>
      <div class="node"><div class="ic">⚖️</div><div class="t">LLM-as-Judge</div><div class="s">6 dimensions</div></div>
      <div class="node"><div class="ic">📊</div><div class="t">Score</div><div class="s">0–100</div></div>
    </div>
  </div>
</section>

<!-- DIMENSIONS DOCK -->
<section class="dock-sec">
  <div class="wrap">
    <div class="eyebrow reveal"><span class="dot"></span>Scored independently</div>
    <h2 class="reveal">Six trust dimensions</h2>
    <p class="hint reveal">↓ Move your cursor across the row — macOS-dock magnification + 3D tilt on hover.</p>
    <div class="dock reveal" id="dock">
      <div class="card"><div class="card-inner"><div class="ico" style="background:#6366f122">🎯</div><div><div class="name">Truthfulness</div><div class="score">score <b>91</b>/100</div></div></div></div>
      <div class="card"><div class="card-inner"><div class="ico" style="background:#4ade8022">🛡️</div><div><div class="name">Safety</div><div class="score">score <b>88</b>/100</div></div></div></div>
      <div class="card"><div class="card-inner"><div class="ico" style="background:#f59e0b22">⚖️</div><div><div class="name">Fairness</div><div class="score">score <b>83</b>/100</div></div></div></div>
      <div class="card"><div class="card-inner"><div class="ico" style="background:#2dd4bf22">🔒</div><div><div class="name">Privacy</div><div class="score">score <b>95</b>/100</div></div></div></div>
      <div class="card"><div class="card-inner"><div class="ico" style="background:#a855f722">🧪</div><div><div class="name">Robustness</div><div class="score">score <b>79</b>/100</div></div></div></div>
      <div class="card"><div class="card-inner"><div class="ico" style="background:#ec489922">🧭</div><div><div class="name">Ethics</div><div class="score">score <b>87</b>/100</div></div></div></div>
    </div>
  </div>
</section>

<!-- SCROLL-SWAPPED PANELS -->
<section class="swap-sec">
  <div class="wrap">
    <div class="eyebrow reveal"><span class="dot"></span>What's inside</div>
    <h2 class="reveal">One platform, three jobs</h2>
    <div class="swap">
      <div class="steps">
        <div class="step" data-vis="0"><h3>RAG testing</h3><p>Feed in retrieved context and check whether the answer is actually grounded in it — not invented. Catch unsupported claims per response.</p></div>
        <div class="step" data-vis="1"><h3>LLM-as-Judge</h3><p>Score outputs across all six dimensions with a judge model, with rationales you can read. No hand-labelling every example.</p></div>
        <div class="step" data-vis="2"><h3>Agent performance</h3><p>Track multi-step agent runs end to end — tool calls, retries, and where trust drops along the trajectory.</p></div>
      </div>
      <div class="visual">
        <div class="vis-card on" data-i="0"><div class="big" style="color:var(--teal)">grounded</div><div class="cap">Answer traced back to retrieved passages — no hallucinated facts.</div></div>
        <div class="vis-card" data-i="1"><div class="big" style="color:var(--indigo)">87/100</div><div class="cap">Judge model scores each dimension and explains why.</div></div>
        <div class="vis-card" data-i="2"><div class="big" style="color:var(--violet)">7 steps</div><div class="cap">Full agent trajectory scored, step by step.</div></div>
      </div>
    </div>
  </div>
</section>

<!-- TAB SWITCHER -->
<section class="tabs-sec">
  <div class="wrap">
    <div class="eyebrow reveal"><span class="dot"></span>Bring your own key</div>
    <h2 class="reveal">Evaluate across providers</h2>
    <div class="tabs reveal" id="tabs">
      <span class="pill" id="pill"></span>
      <button class="active" data-tab="0">OpenAI</button>
      <button data-tab="1">Anthropic</button>
      <button data-tab="2">Google</button>
      <button data-tab="3">Mistral</button>
    </div>
    <div class="tab-body" id="tabBody">
      <div class="row show"><span class="chip">gpt-4o</span><span class="chip">gpt-4o-mini</span><span>Scored on all six dimensions with rationales.</span></div>
      <div class="row"><span class="chip">claude-opus</span><span class="chip">claude-sonnet</span><span>Same scoring pipeline, side-by-side comparable.</span></div>
      <div class="row"><span class="chip">gemini-pro</span><span class="chip">gemini-flash</span><span>Swap models without touching your eval set.</span></div>
      <div class="row"><span class="chip">mistral-large</span><span>One key, the full trust report.</span></div>
    </div>
  </div>
</section>

<div class="foot">TrustLLM · LLM Evaluation Platform · Built by <a href="https://www.linkedin.com/in/monika-kushwaha-52443735/" target="_blank" style="color:#6366f1;text-decoration:none;">Monika Kushwaha</a></div>

<script>
const reduce = matchMedia('(prefers-reduced-motion:reduce)').matches;

/* scroll progress */
const prog = document.getElementById('progress');
addEventListener('scroll', () => {
  const h = document.documentElement;
  prog.style.width = (h.scrollTop / (h.scrollHeight - h.clientHeight) * 100) + '%';
}, {passive: true});

/* reveal + stagger + count triggers */
const io = new IntersectionObserver((es) => {
  es.forEach(e => {
    if (e.isIntersecting) {
      e.target.classList.add('in');
      if (e.target.dataset.count !== undefined) runCount(e.target);
      io.unobserve(e.target);
    }
  });
}, {threshold: .2});
document.querySelectorAll('.reveal, .stagger, [data-count]').forEach(el => io.observe(el));

/* count-up */
function runCount(el) {
  const target = +el.dataset.count, suffix = el.dataset.suffix || '';
  if (reduce) { el.textContent = target + suffix; return; }
  let s = null, dur = 1300;
  function step(t) {
    if (!s) s = t;
    const p = Math.min((t - s) / dur, 1);
    const e = 1 - Math.pow(1 - p, 3);
    el.textContent = Math.round(e * target) + suffix;
    if (p < 1) requestAnimationFrame(step);
  }
  requestAnimationFrame(step);
}

/* magnetic buttons */
document.querySelectorAll('.magnetic').forEach(btn => {
  const lbl = btn.querySelector('.lbl');
  btn.addEventListener('mousemove', e => {
    const r = btn.getBoundingClientRect();
    const x = e.clientX - r.left - r.width / 2;
    const y = e.clientY - r.top - r.height / 2;
    btn.style.transform = `translate(${x * .25}px,${y * .35}px)`;
    lbl.style.transform = `translate(${x * .12}px,${y * .18}px)`;
  });
  btn.addEventListener('mouseleave', () => { btn.style.transform = ''; lbl.style.transform = ''; });
});

/* macOS dock magnify + per-card tilt */
(function () {
  const dock = document.getElementById('dock');
  const cards = [...dock.querySelectorAll('.card')];
  const MAX = 1.42, RANGE = 190, LIFT = 22;
  if (!reduce) {
    dock.addEventListener('mousemove', e => {
      cards.forEach(c => {
        const r = c.getBoundingClientRect();
        const d = Math.abs(e.clientX - (r.left + r.width / 2));
        const f = Math.max(0, 1 - d / RANGE);
        c.style.transform = `translateY(${-LIFT * f}px) scale(${1 + (MAX - 1) * f})`;
        c.style.zIndex = Math.round(f * 10);
      });
    });
    dock.addEventListener('mouseleave', () => cards.forEach(c => { c.style.transform = ''; c.style.zIndex = ''; }));
  }
  /* per-card 3D tilt */
  cards.forEach(c => {
    const inner = c.querySelector('.card-inner');
    c.addEventListener('mousemove', e => {
      const r = c.getBoundingClientRect();
      const px = (e.clientX - r.left) / r.width - .5;
      const py = (e.clientY - r.top) / r.height - .5;
      inner.style.transform = `rotateY(${px * 16}deg) rotateX(${-py * 16}deg)`;
    });
    c.addEventListener('mouseleave', () => inner.style.transform = '');
    c.addEventListener('touchstart', () => {
      c.style.transform = 'translateY(-14px) scale(1.16)';
      setTimeout(() => c.style.transform = '', 260);
    }, {passive: true});
  });
})();

/* scroll-swapped panels */
(function () {
  const steps = [...document.querySelectorAll('.swap .step')];
  const vis = [...document.querySelectorAll('.vis-card')];
  const so = new IntersectionObserver((es) => {
    es.forEach(e => {
      if (e.isIntersecting) {
        const i = +e.target.dataset.vis;
        steps.forEach(s => s.classList.remove('active'));
        e.target.classList.add('active');
        vis.forEach(v => v.classList.toggle('on', +v.dataset.i === i));
      }
    });
  }, {rootMargin: '-45% 0px -45% 0px'});
  steps.forEach(s => so.observe(s));
})();

/* tab switcher with sliding pill */
(function () {
  const tabs = document.getElementById('tabs');
  const pill = document.getElementById('pill');
  const btns = [...tabs.querySelectorAll('button')];
  const rows = [...document.querySelectorAll('#tabBody .row')];
  function move(btn) { pill.style.left = btn.offsetLeft + 'px'; pill.style.width = btn.offsetWidth + 'px'; }
  function activate(i) {
    btns.forEach((b, j) => b.classList.toggle('active', i === j));
    rows.forEach((r, j) => r.classList.toggle('show', i === j));
    move(btns[i]);
  }
  btns.forEach((b, i) => b.addEventListener('click', () => activate(i)));
  requestAnimationFrame(() => move(btns[0]));
  addEventListener('resize', () => move(tabs.querySelector('button.active')));
})();
</script>
</body>
</html>"""
