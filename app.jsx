// app.jsx — mounts the Stage and composes scenes onto the timeline.

const DURATION = 70; // seconds — one full cycle

// Allow `#t=12&pause=1` for deterministic frame captures during dev.
function readHashParams() {
  const h = (typeof location !== 'undefined' ? location.hash : '').replace(/^#/, '');
  if (!h) return {};
  const out = {};
  for (const pair of h.split('&')) {
    const [k, v] = pair.split('=');
    if (k) out[k] = v ?? '';
  }
  return out;
}

// Seed localStorage from hash BEFORE Stage mounts so it picks up the time.
{
  const params = readHashParams();
  const hashT = parseFloat(params.t);
  if (isFinite(hashT)) {
    try { localStorage.setItem('lucy:t', String(hashT)); } catch {}
  }
}

function App() {
  const params = readHashParams();
  const paused = params.pause === '1' || params.pause === 'true';

  return (
    <Stage
      width={1920}
      height={1080}
      duration={DURATION}
      background="#000"
      persistKey="lucy"
      loop={true}
      autoplay={!paused}
    >
      {/* Ambient layers — always on */}
      <Starfield count={260} seed={7} />
      <DriftingCircles />
      <Vignette />
      <Grain opacity={0.18} />

      {/* ── Scene 1 — The dot (0–5s) ──────────────────────────────────── */}
      <Sprite start={0} end={5.4}>
        <SceneOneDot />
      </Sprite>

      {/* ── Scene 2 — Zoom into white circle (5–11s) ─────────────────── */}
      <Sprite start={5} end={11.4}>
        <SceneTwoZoom />
      </Sprite>

      {/* ── Scene 3 — LUCY scratch (11–15.5s) ────────────────────────── */}
      <Sprite start={11} end={15.6}>
        <SceneThreeLucy />
      </Sprite>

      {/* ── Scene 4 — Five cosmic stats (15.5–35.5s) ─────────────────── */}
      <Sprite start={15.5} end={19.6}>
        <StatCard
          index="01 / 05"
          big="3"
          unit="rooms / min"
          label="Lucy travels 3 rooms per minute"
          sub="at maximum zoomies"
          orbits={3}
        />
      </Sprite>
      <Sprite start={19.5} end={23.6}>
        <StatCard
          index="02 / 05"
          big="∞"
          unit="mg caffeine"
          label="Monika survives on coffee"
          sub="and ambition"
          orbits={2}
        />
      </Sprite>
      <Sprite start={23.5} end={27.6}>
        <StatCard
          index="03 / 05"
          big="0.00"
          unit="light-years"
          label="Distance between Monika and Lucy"
          sub="emotionally zero"
          orbits={1}
        />
      </Sprite>
      <Sprite start={27.5} end={31.6}>
        <StatCard
          index="04 / 05"
          big="42"
          unit="meows / day"
          label="Average daily meows detected"
          sub="give or take a trill"
          orbits={4}
        />
      </Sprite>
      <Sprite start={31.5} end={35.6}>
        <StatCard
          index="05 / 05"
          big="99.8"
          unit="% probability"
          label="Lucy ignoring Monika after being called"
          sub="margin of error: a single ear flick"
          orbits={5}
        />
      </Sprite>

      {/* ── Scene 5 — Funny scientific comparisons (35.5–47.5s) ──────── */}
      <Sprite start={35.5} end={39.6}>
        <CompareScene
          index="FIG. A"
          aLabel="Lucy's ego"
          bLabel="Jupiter"
          aValue={0.93}
          bValue={0.41}
          aUnit="ego-units"
          bUnit="ego-units"
          note="measurement error: ±none"
        />
      </Sprite>
      <Sprite start={39.5} end={43.6}>
        <CompareScene
          index="FIG. B"
          aLabel="Monika's overthinking"
          bLabel="The Milky Way"
          aValue={0.88}
          bValue={0.62}
          aUnit="thoughts·s⁻¹"
          bUnit="stars (×10¹¹)"
          note="sample size: every 3 a.m."
        />
      </Sprite>
      <Sprite start={43.5} end={47.6}>
        <CompareScene
          index="FIG. C"
          aLabel="Cat hair density"
          bLabel="Dark matter"
          aValue={0.97}
          bValue={0.27}
          aUnit="g / black sweater"
          bUnit="g / cm³"
          note="hypothesis: they are the same thing"
        />
      </Sprite>

      {/* ── Scene 6 — Quiet pause (47.5–54s) ─────────────────────────── */}
      <Sprite start={47.5} end={54.2}>
        <ScenePause />
      </Sprite>

      {/* ── Scene 7 — Circle → silhouette (54–62s) ───────────────────── */}
      <Sprite start={54} end={62.4}>
        <SceneSilhouette />
      </Sprite>

      {/* ── Scene 8 — End card (62–70s) ──────────────────────────────── */}
      <Sprite start={62} end={70}>
        <SceneEndCard />
      </Sprite>

      {/* Universal chapter ticker — bottom-left timecode/chapter */}
      <ChapterTicker />
    </Stage>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(<App />);
