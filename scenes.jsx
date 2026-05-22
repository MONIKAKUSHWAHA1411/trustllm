// scenes.jsx — all scenes, ambient layers, and reusable infographic primitives.
// Everything is mono: #000 / #f6f4ef / a single warm-gray accent.

const HELV   = '"Helvetica Neue", Helvetica, Arial, sans-serif';
const MONO   = '"JetBrains Mono", ui-monospace, "SF Mono", monospace';
const INK    = '#f6f4ef';          // warm white
const INK_2  = 'rgba(246,244,239,0.55)';
const INK_3  = 'rgba(246,244,239,0.25)';
const RULE   = 'rgba(246,244,239,0.18)';

// ─────────────────────────────────────────────────────────────────────────────
// AMBIENT LAYERS
// ─────────────────────────────────────────────────────────────────────────────

// Deterministic pseudo-random — keeps stars stable across renders/seeks.
function makeRng(seed) {
  let s = seed >>> 0;
  return () => { s = (s * 1664525 + 1013904223) >>> 0; return s / 4294967296; };
}

function Starfield({ count = 240, seed = 7 }) {
  const stars = React.useMemo(() => {
    const rng = makeRng(seed);
    return Array.from({ length: count }, () => ({
      x: rng() * 1920,
      y: rng() * 1080,
      r: rng() * 1.6 + 0.25,
      base: rng() * 0.55 + 0.15,
      twk: rng() * Math.PI * 2,
      speed: 0.6 + rng() * 1.4,
    }));
  }, [count, seed]);
  const t = useTime();
  return (
    <div style={{ position: 'absolute', inset: 0, pointerEvents: 'none' }}>
      {stars.map((s, i) => {
        const op = s.base * (0.55 + 0.45 * Math.sin(t * s.speed + s.twk));
        return (
          <div key={i} style={{
            position: 'absolute',
            left: s.x, top: s.y,
            width: s.r * 2, height: s.r * 2,
            background: '#fff',
            borderRadius: '50%',
            opacity: op,
          }}/>
        );
      })}
    </div>
  );
}

// Big drifting outlined "planet" circles in the background — celestial bodies.
function DriftingCircles() {
  const t = useTime();
  const circles = [
    { x: 1620, y: 200, r: 260, sp: 11, dx: 70, dy: 25, stroke: 0.10, fill: 0.012 },
    { x: 230,  y: 880, r: 360, sp: 17, dx: -50, dy: -40, stroke: 0.07, fill: 0.010 },
    { x: 1200, y: 1100, r: 520, sp: 23, dx: 60, dy: -70, stroke: 0.05, fill: 0.008 },
    { x: 520,  y: 120, r: 80, sp: 9,  dx: -30, dy: 50, stroke: 0.18, fill: 0.0 },
  ];
  return (
    <div style={{ position: 'absolute', inset: 0, pointerEvents: 'none' }}>
      {circles.map((c, i) => {
        const cx = c.x + Math.sin(t / c.sp) * c.dx;
        const cy = c.y + Math.cos(t / c.sp * 0.8) * c.dy;
        return (
          <div key={i} style={{
            position: 'absolute',
            left: cx - c.r, top: cy - c.r,
            width: c.r * 2, height: c.r * 2,
            borderRadius: '50%',
            border: `1px solid rgba(246,244,239,${c.stroke})`,
            background: c.fill > 0
              ? `radial-gradient(circle, rgba(246,244,239,${c.fill}) 0%, transparent 65%)`
              : 'transparent',
          }}/>
        );
      })}
    </div>
  );
}

// Edge vignette — keeps focus to center, very subtle.
function Vignette() {
  return (
    <div style={{
      position: 'absolute', inset: 0, pointerEvents: 'none',
      background: 'radial-gradient(ellipse at center, transparent 50%, rgba(0,0,0,0.55) 100%)',
    }}/>
  );
}

// SVG film grain — soft analog flicker via animated baseFrequency seed.
function Grain({ opacity = 0.18 }) {
  const t = useTime();
  const seed = Math.floor(t * 12) % 8; // change ~12fps for film flicker
  return (
    <svg
      style={{
        position: 'absolute', inset: 0, width: '100%', height: '100%',
        pointerEvents: 'none', mixBlendMode: 'screen', opacity,
      }}
      viewBox="0 0 1920 1080" preserveAspectRatio="none"
    >
      <filter id="lucy-grain">
        <feTurbulence type="fractalNoise" baseFrequency="0.95" numOctaves="2" seed={seed} stitchTiles="stitch"/>
        <feColorMatrix values="0 0 0 0 1  0 0 0 0 1  0 0 0 0 1  0 0 0 0.7 0"/>
      </filter>
      <rect width="1920" height="1080" filter="url(#lucy-grain)"/>
    </svg>
  );
}

// Bottom-left timecode + chapter — NASA-y mission overlay.
function ChapterTicker() {
  const { time, duration } = useTimeline();
  const chapters = [
    [0, 5,      'I.    PROLOGUE'],
    [5, 11,     'II.   ZOOM OUT'],
    [11, 15.5,  'III.  ENTER LUCY'],
    [15.5, 35.5,'IV.   OBSERVATIONS'],
    [35.5, 47.5,'V.    COMPARISONS'],
    [47.5, 54,  'VI.   QUIET'],
    [54, 62,    'VII.  TRANSFORMATION'],
    [62, 70,    'VIII. EPILOGUE'],
  ];
  const active = chapters.find(c => time >= c[0] && time < c[1]) || chapters[chapters.length - 1];
  const mm = String(Math.floor(time / 60)).padStart(2, '0');
  const ss = String(Math.floor(time % 60)).padStart(2, '0');
  const ff = String(Math.floor((time * 24) % 24)).padStart(2, '0');
  return (
    <div style={{
      position: 'absolute', left: 60, bottom: 50, zIndex: 50,
      display: 'flex', flexDirection: 'column', gap: 6,
      fontFamily: MONO, color: INK_2, fontSize: 13, letterSpacing: '0.12em',
      textTransform: 'uppercase', pointerEvents: 'none',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
        <span style={{ width: 6, height: 6, background: INK, borderRadius: '50%',
          opacity: 0.4 + 0.6 * Math.abs(Math.sin(time * 2)) }}/>
        <span>{`T+ ${mm}:${ss}:${ff}`}</span>
      </div>
      <div style={{ color: INK_3, fontSize: 11 }}>
        {active[2]}
      </div>
    </div>
  );
}

// Top-right corner mark — fixed mission tag for cinematic feel.
function CornerMark() {
  return (
    <div style={{
      position: 'absolute', right: 60, top: 50, zIndex: 50,
      fontFamily: MONO, color: INK_3, fontSize: 11, letterSpacing: '0.28em',
      textTransform: 'uppercase', textAlign: 'right', lineHeight: 1.6,
      pointerEvents: 'none', whiteSpace: 'nowrap',
    }}>
      <div>mission M-L &nbsp;·&nbsp; 2026</div>
      <div>obs. record no. 42</div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// SCENE 1 — THE DOT
// ─────────────────────────────────────────────────────────────────────────────
function SceneOneDot() {
  const { localTime } = useSprite();
  // Dot appears at t=0.8, slowly intensifies until ~3.5, then begins to swell
  // setting up the zoom-out in scene 2.
  const dotOp   = animate({ from: 0, to: 1,    start: 0.8, end: 2.4, ease: Easing.easeOutCubic })(localTime);
  const dotR    = animate({ from: 2, to: 6,    start: 0.8, end: 4.2, ease: Easing.easeOutCubic })(localTime);
  const halo    = animate({ from: 0, to: 80,   start: 1.6, end: 4.6, ease: Easing.easeOutCubic })(localTime);
  const haloOp  = animate({ from: 0, to: 0.35, start: 1.6, end: 3.0, ease: Easing.easeOutCubic })(localTime)
                * animate({ from: 1, to: 0,    start: 4.2, end: 5.4, ease: Easing.easeInCubic })(localTime);

  return (
    <div style={{ position: 'absolute', inset: 0 }}>
      <CornerMark />

      {/* The dot */}
      <div style={{
        position: 'absolute', left: '50%', top: '50%',
        transform: 'translate(-50%, -50%)',
        width: dotR * 2, height: dotR * 2,
        background: INK, borderRadius: '50%', opacity: dotOp,
        boxShadow: `0 0 ${halo}px ${halo / 2}px rgba(246,244,239,${haloOp})`,
      }}/>

      {/* Text */}
      <Sprite start={1.4} end={5.2}>
        <CenteredText
          text="In a universe of 200 billion stars…"
          y={760}
          size={56}
          weight={300}
          letterSpacing="0.04em"
          color={INK}
        />
      </Sprite>

      {/* Tiny annotation pointing to the dot */}
      <Sprite start={2.0} end={5.0}>
        <Annotation
          x={960 + 40} y={540 - 30}
          label="OBS-01 · candidate"
          subLabel="m ≈ ?"
          align="left"
        />
      </Sprite>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// SCENE 2 — ZOOM OUT INTO A GIANT WHITE CIRCLE
// ─────────────────────────────────────────────────────────────────────────────
function SceneTwoZoom() {
  const { localTime } = useSprite();
  // The dot expands into a massive white disc, then settles.
  const r = animate({ from: 6, to: 1600, start: 0, end: 1.8, ease: Easing.easeInOutCubic })(localTime);
  const settleR = animate({ from: 1600, to: 1200, start: 1.8, end: 2.6, ease: Easing.easeOutCubic })(localTime);
  const finalR = localTime < 1.8 ? r : settleR;
  // Fade out as scene 3 takes over
  const op = animate({ from: 1, to: 0, start: 5.8, end: 6.4, ease: Easing.easeInCubic })(localTime);

  return (
    <div style={{ position: 'absolute', inset: 0, opacity: op }}>
      {/* The giant disc */}
      <div style={{
        position: 'absolute',
        left: 960 - finalR, top: 540 - finalR,
        width: finalR * 2, height: finalR * 2,
        background: INK,
        borderRadius: '50%',
        boxShadow: '0 0 120px 40px rgba(246,244,239,0.18)',
      }}/>

      {/* Massive black-on-white type, three staggered lines */}
      <Sprite start={2.3} end={6.2}>
        <BigTypeLine
          line1="one tortoiseshell cat"
          line2="mattered most."
        />
      </Sprite>

      {/* NASA-style coordinate tick over the disc */}
      <Sprite start={2.6} end={6.0}>
        <DiscCoordinate />
      </Sprite>
    </div>
  );
}

function BigTypeLine({ line1, line2 }) {
  const { localTime, duration } = useSprite();
  const exitStart = duration - 0.6;

  const baseSlide = animate({ from: 32, to: 0, start: 0, end: 0.55, ease: Easing.easeOutCubic })(localTime);
  const baseOp1   = animate({ from: 0, to: 1,  start: 0,    end: 0.45, ease: Easing.easeOutCubic })(localTime);
  const baseOp2   = animate({ from: 0, to: 1,  start: 0.25, end: 0.7,  ease: Easing.easeOutCubic })(localTime);
  const exitOp    = animate({ from: 1, to: 0,  start: exitStart, end: duration, ease: Easing.easeInCubic })(localTime);

  // Text sits on top of the giant white disc — render black for max contrast.
  return (
    <div style={{
      position: 'absolute', inset: 0,
      display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center',
      textAlign: 'center',
      color: '#000', fontFamily: HELV,
    }}>
      <div style={{
        fontSize: 140, fontWeight: 800, lineHeight: 0.96,
        letterSpacing: '-0.04em',
        transform: `translateY(${baseSlide}px)`,
        opacity: baseOp1 * exitOp,
      }}>{line1}</div>
      <div style={{
        fontSize: 140, fontWeight: 400, lineHeight: 0.96,
        letterSpacing: '-0.03em',
        transform: `translateY(${baseSlide * 0.7}px)`,
        opacity: baseOp2 * exitOp,
        fontStyle: 'italic',
      }}>{line2}</div>
    </div>
  );
}

function DiscCoordinate() {
  const { localTime, duration } = useSprite();
  const op = animate({ from: 0, to: 1, start: 0, end: 0.6, ease: Easing.easeOutCubic })(localTime)
           * animate({ from: 1, to: 0, start: duration - 0.5, end: duration, ease: Easing.easeInCubic })(localTime);
  return (
    <div style={{
      position: 'absolute', left: 200, top: 200, opacity: op,
      fontFamily: MONO, color: '#000', fontSize: 12, letterSpacing: '0.18em',
      textTransform: 'uppercase',
    }}>
      <div style={{ width: 60, height: 1, background: '#000', marginBottom: 8 }}/>
      <div>SUBJECT · CIRC-02</div>
      <div style={{ opacity: 0.6 }}>RA 04h 24m / DEC −31°</div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// SCENE 3 — LUCY (scratch-in)
// ─────────────────────────────────────────────────────────────────────────────
function SceneThreeLucy() {
  const { localTime, duration } = useSprite();

  // Each letter "scratches" in with a slight rotation + claw mark drawing
  const letters = ['L', 'U', 'C', 'Y'];
  const stagger = 0.28;

  // Exit
  const exitOp = animate({ from: 1, to: 0, start: duration - 0.6, end: duration, ease: Easing.easeInCubic })(localTime);

  return (
    <div style={{ position: 'absolute', inset: 0, opacity: exitOp }}>
      {/* Claw-mark diagonal scratches behind the letters */}
      <Claws localTime={localTime} />

      <div style={{
        position: 'absolute', inset: 0,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        gap: 18,
      }}>
        {letters.map((ch, i) => {
          const start = 0.3 + i * stagger;
          const a = clamp((localTime - start) / 0.35, 0, 1);
          const ease = Easing.easeOutBack(a);
          const opacity = clamp((localTime - start) / 0.2, 0, 1);
          // settle wobble
          const wob = (1 - a) * (i % 2 === 0 ? -6 : 6);
          return (
            <span key={i} style={{
              display: 'inline-block',
              fontFamily: HELV,
              fontSize: 540, fontWeight: 900,
              color: INK, lineHeight: 0.85,
              letterSpacing: '-0.06em',
              transform: `translateY(${(1 - ease) * 40}px) rotate(${wob}deg) scale(${0.7 + 0.3 * ease})`,
              transformOrigin: 'center 70%',
              opacity,
              textShadow: '0 0 60px rgba(246,244,239,0.18)',
            }}>{ch}</span>
          );
        })}
      </div>

      {/* Caption */}
      <Sprite start={1.6} end={duration - 0.2}>
        <CenteredText
          text="(noun · the entire universe, compressed into 4kg)"
          y={920} size={22} weight={400} letterSpacing="0.22em"
          color={INK_2} font={MONO} upper
        />
      </Sprite>
    </div>
  );
}

function Claws({ localTime }) {
  // Three diagonal scratches drawn across screen
  // each scratch is a rotated thin rect whose width animates 0 → full
  const scratches = [
    { y: 280, rot: -8,  delay: 0.05, w: 1600, thick: 6 },
    { y: 580, rot: -10, delay: 0.18, w: 1800, thick: 8 },
    { y: 820, rot: -7,  delay: 0.32, w: 1500, thick: 5 },
  ];
  return (
    <div style={{ position: 'absolute', inset: 0, pointerEvents: 'none' }}>
      {scratches.map((s, i) => {
        const t = clamp((localTime - s.delay) / 0.28, 0, 1);
        const w = s.w * Easing.easeOutExpo(t);
        const op = clamp(t * 2, 0, 1) * (1 - clamp((localTime - 2.2) / 1.2, 0, 1));
        return (
          <div key={i} style={{
            position: 'absolute',
            left: 960 - w / 2, top: s.y,
            width: w, height: s.thick,
            background: `linear-gradient(90deg, transparent 0%, ${INK} 15%, ${INK} 85%, transparent 100%)`,
            transform: `rotate(${s.rot}deg)`,
            transformOrigin: 'center center',
            opacity: op * 0.5,
            mixBlendMode: 'screen',
          }}/>
        );
      })}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// SCENE 4 — STAT CARDS (5x)
// ─────────────────────────────────────────────────────────────────────────────
function StatCard({ index, big, unit, label, sub, orbits = 3 }) {
  const { localTime, duration } = useSprite();
  const entryDur = 0.5, exitDur = 0.45;
  const exitStart = duration - exitDur;

  const ein = clamp(localTime / entryDur, 0, 1);
  const eout = clamp((localTime - exitStart) / exitDur, 0, 1);

  const inEase = Easing.easeOutCubic(ein);
  const outEase = Easing.easeInCubic(eout);

  const opacity = Math.min(inEase, 1 - outEase);
  const slide = (1 - inEase) * 32 + outEase * -16;

  // The orbit visualization on the left
  return (
    <div style={{ position: 'absolute', inset: 0, opacity }}>
      <CornerMark />

      {/* Orbit diagram, centered-left */}
      <div style={{
        position: 'absolute', left: 0, top: 0, width: 1920, height: 1080,
        display: 'flex', alignItems: 'center', justifyContent: 'flex-start',
        paddingLeft: 180,
      }}>
        <OrbitDiagram count={orbits} time={localTime} size={620} />
      </div>

      {/* Right column — index, big number, label */}
      <div style={{
        position: 'absolute', right: 140, top: 220, width: 880,
        transform: `translateY(${slide}px)`,
        display: 'flex', flexDirection: 'column', gap: 28,
      }}>
        <div style={{
          fontFamily: MONO, color: INK_2,
          fontSize: 14, letterSpacing: '0.32em', textTransform: 'uppercase',
        }}>
          {index} ·· observation
        </div>

        <div style={{ display: 'flex', alignItems: 'baseline', gap: 24, color: INK }}>
          <div style={{
            fontFamily: HELV, fontWeight: 700,
            fontSize: 340, lineHeight: 0.85,
            letterSpacing: '-0.06em',
          }}>{big}</div>
          <div style={{
            fontFamily: MONO, color: INK_2, fontSize: 18,
            letterSpacing: '0.18em', textTransform: 'uppercase',
            paddingBottom: 32,
          }}>{unit}</div>
        </div>

        <div style={{ width: 240, height: 1, background: RULE }}/>

        <div style={{
          fontFamily: HELV, color: INK, fontWeight: 500,
          fontSize: 54, lineHeight: 1.05, letterSpacing: '-0.02em',
          maxWidth: 800,
          textWrap: 'pretty',
        }}>{label}</div>

        <div style={{
          fontFamily: HELV, color: INK_2, fontWeight: 300,
          fontSize: 28, lineHeight: 1.3, letterSpacing: '-0.005em',
          fontStyle: 'italic',
        }}>{sub}</div>
      </div>
    </div>
  );
}

function OrbitDiagram({ count = 3, time = 0, size = 600 }) {
  // Concentric ellipses, each with a small dot orbiting at its own rate.
  const orbits = Array.from({ length: count }, (_, i) => {
    const ratio = (i + 1) / count;
    const r = size * 0.5 * ratio;
    return {
      r,
      ry: r * (0.6 + 0.2 * ((i % 2) === 0 ? 1 : -1)),
      rot: (i * 17) % 90,
      speed: 0.7 + i * 0.35,
      phase: i * 1.3,
    };
  });

  return (
    <div style={{ position: 'relative', width: size, height: size }}>
      {/* Center sun (Monika) */}
      <div style={{
        position: 'absolute', left: '50%', top: '50%',
        transform: 'translate(-50%, -50%)',
        width: 22, height: 22, borderRadius: '50%',
        background: INK,
        boxShadow: '0 0 40px 8px rgba(246,244,239,0.22)',
      }}/>
      <div style={{
        position: 'absolute', left: '50%', top: 'calc(50% + 26px)',
        transform: 'translateX(-50%)',
        fontFamily: MONO, fontSize: 11, color: INK_2,
        letterSpacing: '0.24em', textTransform: 'uppercase',
      }}>M · core</div>

      {orbits.map((o, i) => {
        const ang = time * o.speed + o.phase;
        const px = Math.cos(ang) * o.r;
        const py = Math.sin(ang) * o.ry;
        return (
          <React.Fragment key={i}>
            <div style={{
              position: 'absolute', left: '50%', top: '50%',
              width: o.r * 2, height: o.ry * 2,
              marginLeft: -o.r, marginTop: -o.ry,
              border: `1px solid ${RULE}`,
              borderRadius: '50%',
              transform: `rotate(${o.rot}deg)`,
            }}/>
            <div style={{
              position: 'absolute', left: '50%', top: '50%',
              width: 8, height: 8, borderRadius: '50%',
              background: INK,
              transform: `translate(-50%, -50%) rotate(${o.rot}deg) translate(${px}px, ${py}px)`,
            }}/>
          </React.Fragment>
        );
      })}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// SCENE 5 — COMPARISONS (NASA-style bar charts)
// ─────────────────────────────────────────────────────────────────────────────
function CompareScene({ index, aLabel, bLabel, aValue, bValue, aUnit, bUnit, note }) {
  const { localTime, duration } = useSprite();
  const exitStart = duration - 0.5;

  const op = animate({ from: 0, to: 1, start: 0,        end: 0.5,      ease: Easing.easeOutCubic })(localTime)
           * animate({ from: 1, to: 0, start: exitStart, end: duration, ease: Easing.easeInCubic })(localTime);

  const aGrow = animate({ from: 0, to: aValue, start: 0.6, end: 1.8, ease: Easing.easeOutCubic })(localTime);
  const bGrow = animate({ from: 0, to: bValue, start: 0.9, end: 2.1, ease: Easing.easeOutCubic })(localTime);

  return (
    <div style={{ position: 'absolute', inset: 0, opacity: op }}>
      <CornerMark />

      {/* Index + title row */}
      <div style={{
        position: 'absolute', left: 140, top: 140,
        fontFamily: MONO, color: INK_2,
        fontSize: 14, letterSpacing: '0.32em', textTransform: 'uppercase',
      }}>
        {index} · scaled comparison
      </div>

      <div style={{
        position: 'absolute', left: 140, top: 200, width: 1640,
        fontFamily: HELV, color: INK, fontWeight: 700,
        fontSize: 92, lineHeight: 1.0, letterSpacing: '-0.035em',
      }}>
        {aLabel} <span style={{ color: INK_2, fontWeight: 300, fontStyle: 'italic' }}>vs.</span> {bLabel}
      </div>

      {/* Two bars */}
      <div style={{
        position: 'absolute', left: 140, top: 460, width: 1640,
        display: 'flex', flexDirection: 'column', gap: 70,
      }}>
        <Bar label={aLabel} value={aGrow} max={1.0} unit={aUnit} />
        <Bar label={bLabel} value={bGrow} max={1.0} unit={bUnit} />
      </div>

      {/* Footnote */}
      <div style={{
        position: 'absolute', left: 140, bottom: 130,
        fontFamily: MONO, color: INK_3,
        fontSize: 14, letterSpacing: '0.22em', textTransform: 'uppercase',
      }}>
        † {note}
      </div>
    </div>
  );
}

function Bar({ label, value, max, unit }) {
  const pct = clamp(value / max, 0, 1);
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      <div style={{
        display: 'flex', justifyContent: 'space-between',
        fontFamily: MONO, color: INK_2,
        fontSize: 14, letterSpacing: '0.24em', textTransform: 'uppercase',
      }}>
        <span>{label}</span>
        <span>{value.toFixed(2)} <span style={{ color: INK_3 }}>{unit}</span></span>
      </div>
      <div style={{
        position: 'relative', width: '100%', height: 56,
        border: `1px solid ${RULE}`, background: 'transparent',
      }}>
        {/* tick marks */}
        {Array.from({ length: 11 }).map((_, i) => (
          <div key={i} style={{
            position: 'absolute', left: `${i * 10}%`, top: 0,
            width: 1, height: i % 5 === 0 ? 14 : 8,
            background: RULE,
          }}/>
        ))}
        {/* filled bar */}
        <div style={{
          position: 'absolute', left: 0, top: 0, bottom: 0,
          width: `${pct * 100}%`,
          background: INK,
        }}/>
        {/* end marker label */}
        <div style={{
          position: 'absolute',
          left: `calc(${pct * 100}% + 12px)`, top: '50%',
          transform: 'translateY(-50%)',
          fontFamily: MONO, fontSize: 13, color: INK_2,
          letterSpacing: '0.22em', textTransform: 'uppercase',
          whiteSpace: 'nowrap', opacity: pct > 0.04 ? 1 : 0,
        }}>{(pct * 100).toFixed(1)}%</div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// SCENE 6 — QUIET PAUSE
// ─────────────────────────────────────────────────────────────────────────────
function ScenePause() {
  const { localTime, duration } = useSprite();
  // Heavy black overlay — fades in over ambient, dims everything down.
  const overlayOp = animate({ from: 0, to: 0.92, start: 0,         end: 0.8,     ease: Easing.easeInOutCubic })(localTime)
                  * animate({ from: 1, to: 0,   start: duration - 0.6, end: duration, ease: Easing.easeInCubic })(localTime);

  return (
    <div style={{ position: 'absolute', inset: 0 }}>
      <div style={{
        position: 'absolute', inset: 0, background: '#000', opacity: overlayOp,
      }}/>

      {/* Two whispered lines — kept slightly overlapping so the screen is never empty */}
      <Sprite start={0.8} end={3.4}>
        <CenteredText
          text="Some planets have rings."
          y={540 - 22}
          size={42} weight={300}
          letterSpacing="0.04em"
          color={INK}
        />
      </Sprite>

      <Sprite start={3.2} end={duration - 0.2}>
        <CenteredText
          text="Monika had Lucy."
          y={540 - 22}
          size={52} weight={500}
          letterSpacing="-0.005em"
          color={INK}
        />
      </Sprite>

      {/* one slow pulsing dot offset to the right, like a distant star */}
      <Sprite start={0.5} end={duration - 0.2}>
        <DistantDot />
      </Sprite>
    </div>
  );
}

function DistantDot() {
  const { localTime } = useSprite();
  const pulse = 0.5 + 0.5 * Math.sin(localTime * 1.5);
  return (
    <div style={{
      position: 'absolute', left: 1260, top: 540 - 1,
      width: 3, height: 3, borderRadius: '50%',
      background: INK, opacity: 0.5 + 0.4 * pulse,
      boxShadow: `0 0 ${10 + pulse * 14}px ${pulse * 4}px rgba(246,244,239,${0.18 + pulse * 0.15})`,
    }}/>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// SCENE 7 — TRANSFORMATION (circle → cat silhouette)
// ─────────────────────────────────────────────────────────────────────────────
function SceneSilhouette() {
  const { localTime, duration } = useSprite();
  // Start with a giant white circle that morphs by growing two ears.
  // Then text fades in. Then exit.

  // Disc scales in
  const discR = animate({ from: 0,    to: 280, start: 0,    end: 1.4, ease: Easing.easeOutCubic })(localTime);
  // Ears grow from 0 → full
  const earScale = animate({ from: 0, to: 1, start: 1.6, end: 2.6, ease: Easing.easeOutBack })(localTime);

  const exitOp = animate({ from: 1, to: 0, start: duration - 0.6, end: duration, ease: Easing.easeInCubic })(localTime);

  return (
    <div style={{ position: 'absolute', inset: 0, opacity: exitOp }}>
      {/* Cat silhouette: SVG composed of head (circle) + two triangle ears.
          Iconic, minimal — fits the monochrome infographic aesthetic. */}
      <div style={{
        position: 'absolute', left: '50%', top: 480,
        transform: 'translate(-50%, -50%)',
        width: 600, height: 600,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}>
        <svg width="600" height="600" viewBox="-200 -200 400 400" style={{ overflow: 'visible' }}>
          {/* Ears — scale from base */}
          <g transform={`scale(${earScale})`}>
            <polygon points="-150,-60 -200,-200 -60,-130" fill={INK}
                     style={{ transformOrigin: '-130px -100px' }}/>
            <polygon points="150,-60 200,-200 60,-130" fill={INK}
                     style={{ transformOrigin: '130px -100px' }}/>
            {/* Inner ear hints */}
            <polygon points="-145,-80 -175,-170 -90,-115" fill="#000" opacity="0.18"/>
            <polygon points="145,-80 175,-170 90,-115" fill="#000" opacity="0.18"/>
          </g>
          {/* Head */}
          <circle cx="0" cy="0" r={discR * 0.5} fill={INK} />
          {/* Tiny whisker dots — subtle, only when silhouette has settled */}
          <Sprite start={2.4} end={duration - 0.5}>
            <WhiskerDots />
          </Sprite>
        </svg>
      </div>

      {/* Two lines of text below */}
      <Sprite start={3.2} end={duration - 0.4}>
        <CenteredText
          text="Not every universe needs planets."
          y={860} size={48} weight={300}
          letterSpacing="0.02em" color={INK}
        />
      </Sprite>
      <Sprite start={4.6} end={duration - 0.4}>
        <CenteredText
          text="Some only need a girl and her cat."
          y={930} size={56} weight={600}
          letterSpacing="-0.01em" color={INK}
        />
      </Sprite>
    </div>
  );
}

function WhiskerDots() {
  const { localTime } = useSprite();
  const op = clamp(localTime / 0.6, 0, 1);
  // Two small eye dots, a tiny nose triangle — embedded in current svg coord space.
  return (
    <g opacity={op}>
      <circle cx="-50" cy="-20" r="6" fill="#000"/>
      <circle cx="50" cy="-20" r="6" fill="#000"/>
      <polygon points="-12,25 12,25 0,42" fill="#000" opacity="0.85"/>
    </g>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// SCENE 8 — END CARD
// ─────────────────────────────────────────────────────────────────────────────
function SceneEndCard() {
  const { localTime, duration } = useSprite();

  const slideM = animate({ from: -40, to: 0,  start: 0.2, end: 1.2, ease: Easing.easeOutCubic })(localTime);
  const slideL = animate({ from: 40,  to: 0,  start: 0.5, end: 1.5, ease: Easing.easeOutCubic })(localTime);
  const opM = animate({ from: 0, to: 1, start: 0.2, end: 1.0, ease: Easing.easeOutCubic })(localTime);
  const opL = animate({ from: 0, to: 1, start: 0.5, end: 1.3, ease: Easing.easeOutCubic })(localTime);
  const opPlus = animate({ from: 0, to: 1, start: 1.4, end: 1.9, ease: Easing.easeOutCubic })(localTime);
  const opCap = animate({ from: 0, to: 1, start: 2.4, end: 3.2, ease: Easing.easeOutCubic })(localTime);

  // Slow vignette darkening for cinematic close
  const closeIn = clamp((localTime - 5.5) / 2.0, 0, 1);

  return (
    <div style={{ position: 'absolute', inset: 0 }}>
      {/* Close-in darkening */}
      <div style={{
        position: 'absolute', inset: 0, background: '#000',
        opacity: closeIn * 0.6,
      }}/>

      <div style={{
        position: 'absolute', inset: 0,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontFamily: HELV, color: INK,
        fontWeight: 700, fontSize: 180, lineHeight: 1, letterSpacing: '-0.04em',
      }}>
        <span style={{
          transform: `translateX(${slideM}px)`, opacity: opM,
          display: 'inline-block',
        }}>MONIKA</span>
        <span style={{
          margin: '0 48px', opacity: opPlus,
          fontWeight: 300, color: INK_2,
        }}>+</span>
        <span style={{
          transform: `translateX(${slideL}px)`, opacity: opL,
          display: 'inline-block',
        }}>LUCY</span>
      </div>

      {/* tiny mission tag below */}
      <div style={{
        position: 'absolute', left: 0, right: 0, top: 660,
        textAlign: 'center', opacity: opCap,
        fontFamily: MONO, color: INK_2,
        fontSize: 16, letterSpacing: '0.36em', textTransform: 'uppercase',
      }}>
        an ongoing mission · since the first purr
      </div>

      {/* fin */}
      <div style={{
        position: 'absolute', left: 0, right: 0, bottom: 140,
        textAlign: 'center', opacity: opCap * 0.7,
        fontFamily: MONO, color: INK_3,
        fontSize: 12, letterSpacing: '0.48em', textTransform: 'uppercase',
      }}>
        — fin —
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// PRIMITIVES
// ─────────────────────────────────────────────────────────────────────────────

// CenteredText: a Sprite-aware centered text element with fade in / hold / fade out.
function CenteredText({
  text, y = 540, size = 48, weight = 400, color = INK,
  font = HELV, letterSpacing = '0.02em', upper = false,
}) {
  const { localTime, duration } = useSprite();
  const op = animate({ from: 0, to: 1, start: 0, end: 0.4, ease: Easing.easeOutCubic })(localTime)
           * animate({ from: 1, to: 0, start: duration - 0.4, end: duration, ease: Easing.easeInCubic })(localTime);
  const slide = animate({ from: 14, to: 0, start: 0, end: 0.5, ease: Easing.easeOutCubic })(localTime);
  return (
    <div style={{
      position: 'absolute', left: 0, right: 0, top: y,
      textAlign: 'center',
      fontFamily: font, fontSize: size, fontWeight: weight,
      color, letterSpacing, opacity: op,
      transform: `translateY(${slide}px)`,
      textTransform: upper ? 'uppercase' : 'none',
      lineHeight: 1.1,
    }}>{text}</div>
  );
}

// Annotation: a small label with a leader line and ticker text — NASA-y.
function Annotation({ x, y, label, subLabel = '', align = 'left' }) {
  const { localTime, duration } = useSprite();
  const op = animate({ from: 0, to: 1, start: 0, end: 0.5, ease: Easing.easeOutCubic })(localTime)
           * animate({ from: 1, to: 0, start: duration - 0.5, end: duration, ease: Easing.easeInCubic })(localTime);
  const lineW = animate({ from: 0, to: 80, start: 0.1, end: 0.6, ease: Easing.easeOutCubic })(localTime);
  return (
    <div style={{
      position: 'absolute', left: x, top: y, opacity: op,
      display: 'flex', alignItems: 'center', gap: 12,
      flexDirection: align === 'left' ? 'row' : 'row-reverse',
    }}>
      <div style={{ width: lineW, height: 1, background: INK_2 }}/>
      <div style={{
        fontFamily: MONO, color: INK_2,
        fontSize: 12, letterSpacing: '0.22em', textTransform: 'uppercase',
        lineHeight: 1.5,
      }}>
        <div>{label}</div>
        {subLabel && <div style={{ color: INK_3 }}>{subLabel}</div>}
      </div>
    </div>
  );
}

// Expose scene components & ambient layers globally for app.jsx.
Object.assign(window, {
  Starfield, DriftingCircles, Vignette, Grain, ChapterTicker, CornerMark,
  SceneOneDot, SceneTwoZoom, SceneThreeLucy,
  StatCard, CompareScene, ScenePause, SceneSilhouette, SceneEndCard,
  CenteredText, Annotation, OrbitDiagram, Bar,
});
