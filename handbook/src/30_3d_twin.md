# 3D Home-Network Twin

Bufferbloat is invisible. A judge cannot see a queue, a reflector or an evidence level; they can only see a call that freezes or does not. The 3D twin makes those internal quantities visible: a house with its devices, a pipe to the provider whose width is the shaper rate, glass towers that fill with queueing delay, beacons in the sky for the reflectors, and a halo around the router that shows how much evidence VeriQ has. This chapter specifies the twin completely, from its honesty rules to code skeletons, assets, performance and live mode.

The twin is a P1 deliverable (Sprint 5+, before the finale, docs/11 §18). It lives in the `twin/` folder of the repository (docs/11 §14.1). It runs off the router, in a browser on the demo laptop, and never touches the packet path.

## Purpose and rules

### What the twin is for

- **Explaining** the control loop to a judge in about 30 seconds: where the queue is, what VeriQ measured, what it concluded, what it did, and whether it helped.
- **Debugging** for the team: scrubbing a recorded run shows at a glance when a reflector went bad or when an action was refused.
- **Evidence presentation:** a replay of a ledger run can sit next to the result chart for the same run.

### What the twin is not

- Not a simulator: it draws recorded or live telemetry and computes no network behaviour.
- Not a packet animation: particles are illustrative and drawn from aggregates.
- Not part of the product: the router does not serve it and does not depend on it.

### The rules

These rules extend the 3D replay rules in docs/09 §7 and the visual encodings in docs/05 (module M8). They are checked by the twin's own tests.

1. **It replays real event streams.** Every frame comes from a run in the evidence ledger (replay mode) or from the router's live API (live mode). No frame is hand-written, and no event is invented to make a scene look better.
2. **Every visible object carries a tag:** *measured*, *estimated*, *illustrative* or *truth*. The tag decides the visual encoding, as shown in the table below, and a legend explains it on screen at all times.
3. **The inferred upstream queue is drawn separately from ground truth.** VeriQ can only infer the queue in the ISP equipment from its probe deltas. In lab replays, the emulator's true queue is drawn beside it as a wireframe, which makes estimator accuracy visible.
4. **Aggregates only.** Flows are summarised per device and class. No per-packet animation and no per-flow export beyond what the decision log and stats already hold.
5. **Clicking an event opens its record:** the observations, diagnosis, proposed action, checker verdict, read-back and receipt, plus the application metrics for that time.
6. **Privacy.** The twin shows device names from the run's manifest. Demo runs use lab device names, never a real household's.

| Tag | Meaning | Visual encoding | Examples |
|---|---|---|---|
| measured | Read from counters or probes on the router | Solid surfaces, full opacity | S (read back from tc), per-tin delay, Ĝ, reflector deltas |
| estimated | Computed by VeriQ from measurements | Outlined or translucent, with a band where a spread exists | μ±σ, diagnosis and level, inferred upstream queue |
| illustrative | Decoration that helps reading | Muted colours, a small "illustrative" note in the legend | House, rooms, furniture, particles |
| truth | Ground truth from the lab emulator, available only in lab replays | Dashed wireframe, labelled "TRUTH (lab only)" | True capacity, true ISP queue, the injected fault |

> **Honesty check.** In live demos on the physical kit, truth comes from the ISP emulator, which is part of the lab. On a real home connection there is no truth channel, and the twin must hide all truth objects. The loader enforces this: a stream whose header says `"source":"router"` cannot contain truth frames.

## Scene design

![3D twin scene layout sketch.](figures/fig16_twin.svg)

The scene reads left to right, the same way the traffic flows: the home, the router, the access link, the provider's first hop, then the internet. The camera's default view is a three-quarter view from above, so every element is visible at once.

### Layout

```text
   [study]   [living room]             first hop          sky: far reflector beacons
   laptop    TV  console               (near beacon)        o   o   o   o   o
      \        |    /                       |
       \       |   /                        |              remote servers
   [hall] ROUTER ==== WAN pipe (down/up) ==== ISP block ===== cloud ====== [server]
          queue towers per tin           inferred ISP queue      |
          evidence halo                  (+ truth wireframe)   remote-delay zone
   [bedroom] phone/tablet
```

### Objects and mappings

| Object | Represents | Data field | Visual mapping | Tag |
|---|---|---|---|---|
| House, rooms, furniture | The home | Manifest (device → room) | Static low-poly model | illustrative |
| Device model | A LAN device | `devices[]` in the header | One model per device type; a name label | illustrative (model), measured (label) |
| Lease ring | An active lease on the device | `event.kind = lease` | Gold ring around the device until expiry; a countdown label | measured |
| Sanction badge | An envelope sanction on one of the device's flows | `event.kind = sanction` | Small red badge with the remaining penalty time | measured |
| Flow particles | Throughput per device and class | `flows` frames | Particle density ∝ kbit/s; colour = class | illustrative |
| Router and state badge | `veriqd` operating state | `tick.state` | Badge text and colour (LIVE, SHADOW, DEGRADED, SAFE …) | measured |
| Queue towers | Own queue per CAKE tin, per direction | `tins[].av_delay_ms`, `pk_delay_ms` | Glass tower; liquid height = average delay, a thin line = peak delay; red flash on new drops; small sparks on ECN marks | measured |
| WAN pipe | Configured shaper rate per direction | `tick.S` | Two lanes (down, up); lane width ∝ S | measured |
| Capacity sleeve | Capacity estimate | `tick.mu`, `tick.sigma` | Translucent sleeve around each lane from μ − σ to μ + σ | estimated |
| Truth ring | True emulator capacity | `truth.cap_down`, `truth.cap_up` | Dashed ring on each lane | truth |
| Inferred ISP queue | Delay beyond VeriQ's shaper | Derived: max(0, D − Q_own of the probe tin) | Hatched tower at the ISP block | estimated |
| Truth ISP queue | Emulator queue | `truth.isp_queue_ms` | Wireframe tower beside the hatched one | truth |
| Near beacon | WAN default gateway probe | `reflectors[role = near]` | Beacon on the ISP block; pulse height = delta | measured |
| Far beacons | Active far reflectors | `reflectors[role = far]` | Beacons on an arc in the sky; green healthy, amber outlier, grey unhealthy with a cool-off timer; double ring if ICMP timestamps are supported | measured (delta), estimated (health) |
| Evidence halo | Diagnosis and evidence level | `tick.diag` | Ring around the router; thickness and brightness grow with L0–L3; text "WAN_LIKELY @ L2: FAR + THR" | estimated |
| Action arcs | An action and its verdict | `event.kind = action` | Short arc from the router to the pipe; green for ACCEPT, red with the code for REJECT | measured |
| Receipt card | Outcome of an action | `event.kind = receipt` | Card that floats up 10 s after the action: IMPROVED, NOT_IMPROVED or INCONCLUSIVE | measured |
| Remote-delay zone | Injected remote delay (lab) | `truth.fault` | Dashed amber zone on the cloud link | truth |

### Scale choices

- **Pipe width.** Width is linear in S, clamped to a minimum of 4% of the maximum so a 1 Mbit/s lane stays visible. Linear scaling matters: a judge must see that 20 Mbit/s is a fifth of 100 Mbit/s.
- **Tower height.** Delay spans three orders of magnitude (1 ms to 1 s), so heights use a log scale: `h = H · log10(1 + d) / log10(1 + 1000)` for delay d in ms. Rings on the tower mark 5, 30, 60 and 200 ms, the boundaries of the wizard's bufferbloat grades (VeriQ's own boundaries, labelled as such).
- **Colours per class.** RT, IV, BE and BK use the class palette of Chapter 31, so the twin, LuCI, the LED bars on the kit and the charts all agree.

### Camera presets

| Key | Preset | Use |
|---|---|---|
| 1 | Overview | Default; whole scene |
| 2 | Router close-up | Queue towers and halo |
| 3 | Access link | Pipe, sleeve, truth ring, ISP queue towers |
| 4 | Sky | Reflector beacons |
| 5 | Device | The device selected in the side panel |

## Tech stack

| Layer | Choice | Why | Alternatives considered |
|---|---|---|---|
| Rendering | three.js [R43] | WebGL standard; large community; MIT licence | Babylon.js (heavier); Unity WebGL (large download, a separate toolchain) |
| Scene graph | React with react-three-fiber and drei | Declarative scene; components match the object table; drei gives text, outlines, camera controls | Plain three.js (more glue code) |
| State | zustand | Small store; components read only the slice they need, which avoids re-rendering the scene every frame | React context (re-render storms) |
| Timeline chart | uPlot [R43] | Same chart library as LuCI; fast for long series | Chart.js |
| Build | Vite | Fast dev server; static output that can be opened offline | webpack |
| Replay converter | Python (in `twin/tools/`) | Same language as the lab and evaluator | — |
| Live bridge | Python with the `websockets` package | Small; runs on the hub laptop | Node.js |

All front-end dependencies are MIT-licensed; check each licence when adding a package, and pin exact versions with `npm install --save-exact`, so `package-lock.json` fixes the build. The twin is built to static files (`twin/dist/`) and opened from the hub laptop with no internet access.

> **Why it matters.** A twin that needs internet access, a cloud service or the router's CPU would contradict the design: control is local, and the router does nothing but route. The twin is a separate, off-box viewer.

## The twin event stream

### Sources

A replay is built from files that the lab already records for every run (Chapter 25):

- the **decision log** (JSONL, docs/11 §14.3), one line per tick per direction, with snapshot, diagnosis, action, verdict and read-back;
- **receipts**, with outcome and windows;
- **per-tin statistics** from `tc -s -j qdisc`, sampled every 250 ms by the lab runner;
- the **reflector table** (health, baseline, delta, timestamp support);
- **lease, sanction and state events**;
- **application metrics** from the harness: WebRTC `getStats` [R35], DASH player events, the synthetic game flow;
- **emulator truth** (lab only): true capacity, true queue, the fault schedule.

### Format `twin.v1`

A replay file is JSONL. The first line is a header; every later line is a frame with a type and a time `t` in milliseconds since the run start (monotonic). Tags are declared once in the header, per field path, so the renderer can look them up and frames stay small.

```json
{"type":"header","schema":"twin.v1","source":"ledger","run_id":"S2-veriq-r07",
 "scenario":"S2","arm":"veriq","t0_wall":"2026-11-20T20:40:00.000+05:30",
 "devices":[{"id":"d1","name":"Call laptop","kind":"laptop","room":"study"},
            {"id":"d2","name":"Download PC","kind":"desktop","room":"living"}],
 "tags":{"tick.S":"measured","tick.Ghat":"measured","tick.D":"measured",
         "tick.mu":"estimated","tick.sigma":"estimated","tick.diag":"estimated",
         "tins":"measured","reflectors.delta_ms":"measured",
         "reflectors.health":"estimated","truth":"truth","flows":"illustrative"}}
```

Typical frames (values are illustrative, chosen to match the example in docs/11 §14.3):

```json
{"type":"tick","t":61250,"dir":"down","state":"LIVE","S":95000,"Ghat":20100,
 "load":0.99,"D":42.1,"qown":0.8,"near":39.0,"mu":21000,"sigma":1500,
 "diag":{"label":"WAN_LIKELY","level":2,"sources":["FAR","THR"]}}
{"type":"tins","t":61250,"dir":"down","tins":[
 {"tin":"voice","av_delay_ms":0.9,"pk_delay_ms":2.1,"drops":0,"ecn":0,"kbit":800},
 {"tin":"bulk","av_delay_ms":4.6,"pk_delay_ms":11.0,"drops":3,"ecn":12,"kbit":17000}]}
{"type":"reflectors","t":61000,"items":[
 {"id":"near","role":"near","health":"ok","delta_ms":39.0,"ts":false},
 {"id":"r3","role":"far","health":"ok","delta_ms":41.0,"ts":true}]}
{"type":"event","t":61250,"kind":"action","id":"01JC-demo","action":"RATE_CUT",
 "dir":"down","from":95000,"to":18090,"verdict":"ACCEPT","code":null}
{"type":"event","t":71250,"kind":"receipt","action_id":"01JC-demo","outcome":"IMPROVED"}
{"type":"truth","t":60000,"cap_down":20000,"cap_up":20000,"isp_queue_ms":180.0,
 "fault":"capacity_step"}
{"type":"app","t":61000,"device":"d1","webrtc":{"freezeCount":0,"rtt_ms":38}}
{"type":"flows","t":61000,"device":"d2","class":"BK","kbit":17000,"prov":"heuristic"}
```

Reflector IDs in replays are short aliases (`r1`…`r8`) mapped to addresses in the run manifest, so a screenshot shows no addresses.

### Field mapping

| Source | Source field | Twin field | Drives |
|---|---|---|---|
| Decision log | `snapshot.S` | `tick.S` | Pipe lane width |
| Decision log | `snapshot.Ghat`, `snapshot.load` | `tick.Ghat`, `tick.load` | Particle flow speed on the pipe; side panel |
| Decision log | `snapshot.D`, `snapshot.near.d` | `tick.D`, `tick.near` | Inferred ISP queue; near beacon |
| Decision log | `snapshot.QOwn` | `tick.qown` | Inferred ISP queue (subtracted) |
| Decision log | `diag` | `tick.diag` | Evidence halo and its text |
| Decision log | `state` | `tick.state` | Router badge |
| Decision log | `action`, `verdict`, `applied` | `event` (kind `action`) | Action arc; event panel |
| Receipts | `outcome`, windows | `event` (kind `receipt`) | Receipt card |
| Estimator log | μ, σ | `tick.mu`, `tick.sigma` | Capacity sleeve |
| tc -s -j | per-tin `av_delay`, `peak_delay`, `drops`, `ecn_mark`, bytes | `tins[]` | Queue towers |
| Prober | reflector table | `reflectors` | Beacons |
| Lease/sanction log | grant, revoke, expiry; sanction, escalation, recovery | `event` | Lease ring; sanction badge |
| Harness | WebRTC, DASH, game flow | `app` | Device label; side panel charts |
| Emulator | capacity schedule, tbf backlog, fault | `truth` | Truth ring, truth tower, fault zones |

> **Implementation tip.** Check the exact JSON key names of the CAKE tin statistics in `tc -s -j` output on the target iproute2 version before writing the converter. The converter maps them to the stable twin names above, so a key name change touches one function.

### The converter

`twin/tools/build_replay.py` reads one run folder from the evidence ledger and writes `replay.twin.jsonl`. It refuses to write a frame without a source file, and it copies the run manifest's hash into the header, so every replay traces to its run.

```python
"""Build a twin.v1 replay from one evidence-ledger run folder."""
import json, pathlib, sys

def tick_frames(path):
    for line in open(path, encoding="utf-8"):
        rec = json.loads(line)
        snap = rec["snapshot"]
        yield {"type": "tick", "t": rec["t_mono_ms"], "dir": rec["dir"],
               "state": rec["state"], "S": snap["S"], "Ghat": snap["Ghat"],
               "load": snap["load"], "D": snap["D"], "qown": snap["QOwn"],
               "near": snap["near"]["d"] if snap["near"]["ok"] else None,
               "diag": rec["diag"]}
        if rec.get("action"):
            yield {"type": "event", "t": rec["t_mono_ms"], "kind": "action",
                   "id": rec["action"]["id"], "action": rec["action"]["type"],
                   "dir": rec["dir"], "to": rec["action"].get("target"),
                   "verdict": "ACCEPT" if rec["verdict"]["accept"] else "REJECT",
                   "code": rec["verdict"].get("code")}

def main(run_dir, out):
    run = pathlib.Path(run_dir)
    manifest = json.loads((run / "manifest.json").read_text())
    t0 = manifest["t0_mono_ms"]
    frames = list(tick_frames(run / "decision_log.jsonl"))
    # tins_frames(), reflector_frames(), receipt_frames(), app_frames() and
    # truth_frames() follow the same pattern; truth only if manifest["lab"] is true.
    for f in frames:
        f["t"] -= t0
    frames.sort(key=lambda f: f["t"])
    header = {"type": "header", "schema": "twin.v1", "source": "ledger",
              "run_id": manifest["run_id"], "manifest_sha256": manifest["sha256"]}
    with open(out, "w", encoding="utf-8") as fh:
        for obj in [header, *frames]:
            fh.write(json.dumps(obj, separators=(",", ":")) + "\n")

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
```

**Time alignment.** veriqd times are monotonic; harness and emulator times are wall-clock. The run manifest records the offset between them at the start and end of the run; the converter applies it and warns if the drift exceeds 50 ms (a starting value).

## Step-by-step build guide

### Step 1: scaffold

```bash
cd veriq/twin
npm create vite@<x.y.z> . -- --template react  # pin the create-vite version you tested
npm install --save-exact three @react-three/fiber @react-three/drei zustand uplot
npm run dev                                     # http://localhost:5173
```

Folder layout:

```text
twin/
├── src/
│   ├── data/      loader.js, index.js, live.js
│   ├── store.js
│   ├── scene/     Scene.jsx, House.jsx, Router.jsx, WanPipe.jsx, QueueTower.jsx,
│   │              Beacon.jsx, EvidenceHalo.jsx, Device.jsx, Particles.jsx
│   ├── ui/        Timeline.jsx, EventPanel.jsx, Legend.jsx, SidePanel.jsx
│   └── palette.js
├── public/models/ house.glb, devices.glb, router.glb
├── public/replays/ *.twin.jsonl
└── tools/          build_replay.py, bridge.py, validate.py
```

### Step 2: load and index a replay

The loader parses JSONL once, splits frames by type and keeps each list sorted by time. Lookups during playback use binary search, so scrubbing a 10-minute run stays instant.

```javascript
// src/data/loader.js
export async function loadReplay(url) {
  const text = await (await fetch(url)).text();
  const lines = text.split('\n').filter((l) => l.trim().length > 0);
  const header = JSON.parse(lines[0]);
  if (header.schema !== 'twin.v1') throw new Error(`unsupported schema ${header.schema}`);
  const byType = { tick: [], tins: [], reflectors: [], event: [], truth: [], app: [],
    flows: [] };
  for (let i = 1; i < lines.length; i++) {
    const f = JSON.parse(lines[i]);
    if (f.type === 'truth' && header.source === 'router') {
      throw new Error('truth frames are not allowed in a router stream');
    }
    (byType[f.type] ??= []).push(f);
  }
  for (const list of Object.values(byType)) list.sort((a, b) => a.t - b.t);
  const tEnd = Math.max(...Object.values(byType).map((l) => (l.length ? l.at(-1).t : 0)));
  return { header, byType, tEnd };
}

// Last frame at or before t (binary search). Optional filter, e.g. by direction.
export function frameAt(list, t, pred = () => true) {
  let lo = 0, hi = list.length - 1, best = -1;
  while (lo <= hi) {
    const mid = (lo + hi) >> 1;
    if (list[mid].t <= t) { best = mid; lo = mid + 1; } else { hi = mid - 1; }
  }
  for (let i = best; i >= 0 && i > best - 8; i--) if (pred(list[i])) return list[i];
  return null;
}

export function tagOf(header, path) {
  const tags = header.tags || {};
  return tags[path] ?? tags[path.split('.')[0]] ?? 'untagged';
}
```

### Step 3: the playback store

```javascript
// src/store.js
import { create } from 'zustand';

export const useTwin = create((set, get) => ({
  replay: null,         // { header, byType, tEnd }
  t: 0,                 // playback time, ms since run start
  playing: false,
  speed: 1,             // 0.25, 0.5, 1, 2, 4
  selectedEvent: null,
  mode: 'replay',       // 'replay' | 'live'
  setReplay: (replay) => set({ replay, t: 0, playing: false }),
  seek: (t) => set({ t: Math.max(0, Math.min(t, get().replay?.tEnd ?? 0)) }),
  toggle: () => set({ playing: !get().playing }),
  advance: (dtMs) => {
    const { playing, t, speed, replay } = get();
    if (!playing || !replay) return;
    const next = t + dtMs * speed;
    set({ t: Math.min(next, replay.tEnd), playing: next < replay.tEnd });
  },
  select: (ev) => set({ selectedEvent: ev }),
}));
```

### Step 4: the scene

The scene components read the store inside `useFrame` and mutate three.js objects through refs. They do not use React state for per-frame values, so React does not re-render the scene 60 times a second.

```javascript
// src/scene/Scene.jsx
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls } from '@react-three/drei';
import { useTwin } from '../store';
import { House } from './House';
import { Router } from './Router';
import { WanPipe } from './WanPipe';
import { QueueTowers } from './QueueTower';
import { Beacons } from './Beacon';
import { EvidenceHalo } from './EvidenceHalo';

function Clock() {
  const advance = useTwin((s) => s.advance);
  useFrame((_, delta) => advance(delta * 1000));
  return null;
}

export function Scene() {
  return (
    <Canvas camera={{ position: [6, 9, 14], fov: 45 }} dpr={[1, 1.5]}>
      <ambientLight intensity={0.6} />
      <directionalLight position={[5, 10, 5]} intensity={0.8} />
      <Clock />
      <House />
      <Router position={[0, 0, 0]} />
      <QueueTowers position={[0, 0, 1.5]} />
      <EvidenceHalo position={[0, 0.05, 0]} />
      <WanPipe from={[0.8, 0.6, 0]} to={[8, 0.6, 0]} />
      <Beacons origin={[12, 4, 0]} />
      <OrbitControls makeDefault />
    </Canvas>
  );
}
```

```javascript
// src/scene/WanPipe.jsx: two lanes; width = S (measured), sleeve = mu ± sigma (estimated)
import { useRef } from 'react';
import { useFrame } from '@react-three/fiber';
import { useTwin } from '../store';
import { frameAt } from '../data/loader';

const MAX_KBIT = 110000;     // scene scale; set from the header's S_max
const MAX_W = 0.6;           // metres in scene units
const widthOf = (kbit) => Math.max(0.04 * MAX_W, (kbit / MAX_KBIT) * MAX_W);

function Lane({ dir, z, length }) {
  const core = useRef();
  const sleeve = useRef();
  const truth = useRef();
  useFrame(() => {
    const { replay, t } = useTwin.getState();
    if (!replay) return;
    const tick = frameAt(replay.byType.tick, t, (f) => f.dir === dir);
    if (tick) {
      const w = widthOf(tick.S);
      core.current.scale.set(1, w, w);
      const hasMu = tick.mu != null && tick.sigma != null;
      sleeve.current.visible = hasMu;
      if (hasMu) {
        const wHi = widthOf(tick.mu + tick.sigma);
        sleeve.current.scale.set(1, wHi, wHi);
      }
    }
    const tr = frameAt(replay.byType.truth, t);
    truth.current.visible = Boolean(tr);
    if (tr) {
      const w = widthOf(dir === 'down' ? tr.cap_down : tr.cap_up);
      truth.current.scale.set(1, w, w);
    }
  });
  return (
    <group position={[length / 2, 0, z]}>
      <mesh ref={core} rotation={[0, 0, Math.PI / 2]}>
        <cylinderGeometry args={[0.5, 0.5, length, 24]} />
        <meshStandardMaterial color={dir === 'down' ? '#3a7bd5' : '#7b8794'} />
      </mesh>
      <mesh ref={sleeve} rotation={[0, 0, Math.PI / 2]}>
        <cylinderGeometry args={[0.5, 0.5, length, 24, 1, true]} />
        <meshStandardMaterial transparent opacity={0.18} color="#ffffff" />
      </mesh>
      <mesh ref={truth} rotation={[0, 0, Math.PI / 2]}>
        <cylinderGeometry args={[0.5, 0.5, length, 24, 1, true]} />
        <meshBasicMaterial wireframe color="#ffb000" />
      </mesh>
    </group>
  );
}

export function WanPipe({ from, to }) {
  const length = to[0] - from[0];
  return (
    <group position={from}>
      <Lane dir="down" z={-0.45} length={length} />
      <Lane dir="up" z={0.45} length={length} />
    </group>
  );
}
```

```javascript
// src/scene/QueueTower.jsx: one tower per CAKE tin and direction (measured)
import { useRef } from 'react';
import { useFrame } from '@react-three/fiber';
import { useTwin } from '../store';
import { frameAt } from '../data/loader';
import { CLASS_COLOURS } from '../palette';

const H = 3.0;
const heightOf = (ms) => (H * Math.log10(1 + Math.max(0, ms))) / Math.log10(1001);
const TINS = [['voice', 'RT'], ['video', 'IV'], ['besteffort', 'BE'], ['bulk', 'BK']];

function Tower({ dir, tin, cls, x }) {
  const liquid = useRef();
  const peak = useRef();
  const lastDrops = useRef(0);
  useFrame(() => {
    const { replay, t } = useTwin.getState();
    const f = replay && frameAt(replay.byType.tins, t, (fr) => fr.dir === dir);
    const s = f?.tins.find((x2) => x2.tin === tin);
    if (!s) return;
    const h = Math.max(0.001, heightOf(s.av_delay_ms));
    liquid.current.scale.y = h;
    liquid.current.position.y = h / 2;
    peak.current.position.y = heightOf(s.pk_delay_ms);
    const flash = s.drops > lastDrops.current;
    liquid.current.material.emissiveIntensity = flash ? 1.0 : 0.0;
    lastDrops.current = s.drops;
  });
  return (
    <group position={[x, 0, dir === 'down' ? -0.6 : 0.6]}>
      <mesh position={[0, H / 2, 0]}>
        <cylinderGeometry args={[0.18, 0.18, H, 16, 1, true]} />
        <meshPhysicalMaterial transparent opacity={0.15} roughness={0.1} />
      </mesh>
      <mesh ref={liquid}>
        <cylinderGeometry args={[0.16, 0.16, 1, 16]} />
        <meshStandardMaterial color={CLASS_COLOURS[cls]} emissive="#ff0000" />
      </mesh>
      <mesh ref={peak}>
        <torusGeometry args={[0.19, 0.01, 6, 24]} />
        <meshBasicMaterial color="#222222" />
      </mesh>
    </group>
  );
}

export function QueueTowers(props) {
  return (
    <group {...props}>
      {['down', 'up'].flatMap((dir) =>
        TINS.map(([tin, cls], i) => (
          <Tower key={dir + tin} dir={dir} tin={tin} cls={cls} x={i * 0.45 - 0.7} />
        )))}
    </group>
  );
}
```

```javascript
// src/scene/EvidenceHalo.jsx: ring thickness and brightness by evidence level (estimated)
import { useRef } from 'react';
import { useFrame } from '@react-three/fiber';
import { Text } from '@react-three/drei';
import { useTwin } from '../store';
import { frameAt } from '../data/loader';

const LEVEL_STYLE = [
  { tube: 0.02, opacity: 0.25 },   // L0
  { tube: 0.04, opacity: 0.45 },   // L1
  { tube: 0.07, opacity: 0.70 },   // L2
  { tube: 0.10, opacity: 0.95 },   // L3
];

export function EvidenceHalo(props) {
  const ring = useRef();
  const label = useRef();
  useFrame(() => {
    const { replay, t } = useTwin.getState();
    const tick = replay && frameAt(replay.byType.tick, t, (f) => f.dir === 'down');
    if (!tick?.diag) return;
    const st = LEVEL_STYLE[tick.diag.level] ?? LEVEL_STYLE[0];
    ring.current.scale.setScalar(1 + st.tube * 4);
    ring.current.material.opacity = st.opacity;
    const src = (tick.diag.sources || []).join(' + ');
    label.current.text = `${tick.diag.label} @ L${tick.diag.level}${src ? ': ' + src : ''}`;
  });
  return (
    <group {...props}>
      <mesh ref={ring} rotation={[-Math.PI / 2, 0, 0]}>
        <torusGeometry args={[1.1, 0.05, 8, 64]} />
        <meshBasicMaterial transparent color="#f2a33a" />
      </mesh>
      <Text ref={label} position={[0, 2.2, 0]} fontSize={0.22} color="#ffffff">
        {' '}
      </Text>
    </group>
  );
}
```

The halo above follows the download direction; a toggle in the side panel switches it to upload. Beacons, devices and particles follow the same pattern: look up the frame at time t, then mutate refs. Particles use one `InstancedMesh` per class, with the instance count set from the device's kbit/s (illustrative), so thousands of particles cost a handful of draw calls.

### Step 5: timeline and event panel

The timeline is a strip at the bottom of the screen:

- a uPlot chart of S and the true capacity (when available) for both directions;
- event markers above it (action, refusal, receipt, lease, sanction, state change, fault);
- a play head that the user drags to seek.

Clicking a marker calls `select(event)`, and the event panel shows the full decision-log line for that tick, the receipt (if any) and the application metrics in a ±10 s window.

```javascript
// src/ui/EventPanel.jsx
import { useTwin } from '../store';
import { frameAt } from '../data/loader';

export function EventPanel() {
  const ev = useTwin((s) => s.selectedEvent);
  const replay = useTwin((s) => s.replay);
  if (!ev || !replay) return null;
  const tick = frameAt(replay.byType.tick, ev.t, (f) => f.dir === ev.dir);
  const receipt = replay.byType.event.find(
    (e) => e.kind === 'receipt' && e.action_id === ev.id);
  return (
    <aside className="event-panel">
      <h3>{ev.action} {ev.dir}: {ev.verdict}{ev.code ? ` (${ev.code})` : ''}</h3>
      <p>Evidence: {tick?.diag.label} @ L{tick?.diag.level}
        [{tick?.diag.sources.join(', ')}]</p>
      <p>S {tick?.S} kbit/s, Ĝ {tick?.Ghat} kbit/s, D {tick?.D} ms, Q_own {tick?.qown} ms</p>
      <p>Receipt: {receipt ? receipt.outcome : 'pending or none'}</p>
      <p className="tag">Tags: measured (S, Ĝ, D), estimated (diagnosis)</p>
    </aside>
  );
}
```

### Step 6: legend and tag audit

The legend is always visible in the top-right corner and shows the four tag encodings. A development-mode **tag audit** walks the scene graph and logs any mesh whose `userData.tag` is missing; the CI test (below) fails if the audit finds one. Every component sets `userData.tag` on its root group.

### Step 7: tests

| Test | What it checks |
|---|---|
| `validate.py` on every replay | Header present, schema `twin.v1`, every frame has `type` and `t`, times sorted, no truth frames in router streams |
| Golden replay | A short recorded S2 run loads, and at t = 70 s the lane width and halo text match stored values |
| Tag audit | No untagged mesh in the scene |
| Performance smoke | A 10-minute replay plays at 4× for 60 s with no frame longer than 50 ms on the demo laptop (target) |
| Live-mode fallback | When the WebSocket closes, the UI shows "LIVE: disconnected" within 2 s and stops moving |

## Assets

### Modelling in Blender

- **Style:** low-poly, flat-shaded, matte. The twin should look like a clear diagram, not a game. Muted colours for the house, so the measured objects (towers, pipe, beacons) stand out.
- **Budget (targets):** house ≤ 15k triangles; each device model ≤ 1.5k; total scene ≤ 50k triangles; textures ≤ 1024 × 1024, preferably none (vertex colours).
- **Names:** name objects for the code: `room_study`, `room_living`, `anchor_router`, `anchor_device_01`, `anchor_isp`, `anchor_sky`. Code positions dynamic objects at these anchors, so the model can change without code changes.
- **Units:** 1 Blender unit = 1 scene unit; origin at the router anchor; +Y up in three.js.

### Export

- File → Export → glTF 2.0, format **glTF Binary (.glb)**.
- Include: selected objects or the visible collection; apply modifiers; +Y up.
- Leave Draco compression off at first. Turn it on only if the file exceeds about 2 MB, and then ship the Draco decoder files locally in `public/`, because the demo runs offline.
- Load with drei's `useGLTF('/models/house.glb')`.

### Third-party assets

CC0 low-poly packs (for example Kenney, as suggested in docs/06) are acceptable for furniture and devices. Record each asset's source and licence in `twin/ASSETS.md`. Do not use assets whose licence forbids redistribution, and do not use real brand logos on devices.

## Performance tips

- **Mutate, do not re-render.** Read the store with `useTwin.getState()` inside `useFrame` and write to refs. Subscribe React components only to values that change rarely (selected event, mode).
- **Instancing** for particles and repeated device models.
- **Pre-index** frames by type and direction at load time; never filter the full array per frame.
- **Parse in a Web Worker** if a replay is larger than about 20 MB, so the UI does not stall at load.
- **Clamp the pixel ratio** (`dpr={[1, 1.5]}`) on high-density laptop screens.
- **Pause rendering when paused:** use `frameloop="demand"` while playback is paused and call `invalidate()` on interaction.
- **Avoid shadows and post-processing** on integrated graphics; the twin needs readability, not realism.
- **Target:** a steady 60 fps on the demo laptop, at least 30 fps on the 7-inch booth display (targets, to be measured).

## How to demo it

1. **Open on the overview** (key 1) with a replay of the rehearsal run of S2 loaded and paused just before the drop. Point at the legend first: "solid is measured, outlined is estimated, dashed is lab truth, the house is decoration."
2. **Play at 1×.** The truth ring shrinks at the drop. Then the far beacons rise, the halo thickens to L2 with "WAN_LIKELY: FAR + THR", the green action arc fires, and the lane shrinks to the truth ring. Ten seconds later, the receipt card rises.
3. **Click the action marker** to open the event panel and read the evidence aloud.
4. **Switch to the S6 replay** (remote delay): the far beacons rise, the near beacon stays flat, the halo reads REMOTE_LIKELY, and the lane does not move. "Delay rose, but there was nothing to cut."
5. **Switch to live mode** if the kit is running, and let the judge press a button.

Bookmarks jump to the key moments of each prepared replay; each is a real ledger run, named on screen by its run ID.

> **For judges.** If a judge asks "is this animation scripted?", open the event panel and the run ID, and offer to load any other run from the ledger. The twin draws only what the logs contain.

## Live mode

### Architecture

```text
 Router (VeriQ)                          Hub laptop (off-box)
 veriqd ── rpcd (luci.veriq) ── HTTP /ubus, LAN, read-only ──► bridge.py ── WS ──► twin
        └─ veriq-exporter (P2, opt.) ── HTTP :9567, LAN ─────►    │
                                                                   └─► live.twin.jsonl
```

The router serves no WebSocket and gains no new listener. A small bridge on the hub laptop polls the router over the LAN and pushes `twin.v1` frames to the browser:

- **Default (P1):** rpcd over HTTP. The bridge logs in as a read-only rpcd user whose ACL allows only status, queue statistics, autorate state and recent events (Chapter 21 defines the methods). This is the path LuCI itself uses.
- **When the exporter exists (P2):** scrape the Prometheus text endpoint on the LAN (default port 9567) for counters, and use rpcd only for events.

The bridge writes every frame it sends to `live.twin.jsonl`. A live demo can therefore be replayed afterwards, frame for frame, and filed in the ledger.

Live streams have `"source":"router"` in their header, so truth frames are refused. On the physical kit, a separate `truth` channel from the ISP emulator may be enabled; the header then says `"source":"lab-live"` and the legend shows the truth tag.

### Bridge skeleton

```python
"""bridge.py: poll the router over rpcd and push twin.v1 frames over WebSocket."""
import asyncio, json, time
import requests                      # Apache-2.0
import websockets                    # BSD-3-Clause

ROUTER = "http://192.168.1.1/ubus"
NULL_SESSION = "0" * 32
OBJECT = "luci.veriq"                # rpcd plugin; method names per Chapter 21
CLIENTS = set()

def ubus(session, obj, method, args=None):
    body = {"jsonrpc": "2.0", "id": 1, "method": "call",
            "params": [session, obj, method, args or {}]}
    reply = requests.post(ROUTER, json=body, timeout=1.0).json()
    code, data = reply["result"][0], (reply["result"][1:] or [None])[0]
    if code != 0:
        raise RuntimeError(f"ubus {obj}.{method} failed with code {code}")
    return data

def login(user, password):
    return ubus(NULL_SESSION, "session", "login",
                {"username": user, "password": password})["ubus_rpc_session"]

async def poll(session, log):
    t0 = time.monotonic()
    while True:
        status = ubus(session, OBJECT, "status")
        t = int((time.monotonic() - t0) * 1000)
        frames = to_frames(status, t)          # map fields to tick/tins/reflectors
        for f in frames:
            line = json.dumps(f, separators=(",", ":"))
            log.write(line + "\n")
            websockets.broadcast(CLIENTS, line)
        await asyncio.sleep(0.25)

async def handler(ws):
    CLIENTS.add(ws)
    try:
        await ws.wait_closed()
    finally:
        CLIENTS.discard(ws)

async def main():
    session = login("kit", open("/etc/veriq-kit/password").read().strip())
    with open("live.twin.jsonl", "a", encoding="utf-8") as log:
        log.write(json.dumps({"type": "header", "schema": "twin.v1",
                              "source": "router", "mode": "live"}) + "\n")
        async with websockets.serve(handler, "127.0.0.1", 8765):
            await poll(session, log)

def to_frames(status, t):
    raise NotImplementedError("map the status fields of Chapter 21 to twin.v1 frames")

if __name__ == "__main__":
    asyncio.run(main())
```

For brevity the skeleton makes a blocking HTTP call inside the event loop; the real bridge should use a thread executor or an async client. It binds to `127.0.0.1`, so only the hub laptop's browser can connect.

### Live client

```javascript
// src/data/live.js: append live frames to the same structures the replay uses
import { useTwin } from '../store';

export function connectLive(url = 'ws://127.0.0.1:8765') {
  const replay = { header: { schema: 'twin.v1', source: 'router', tags: {} },
    byType: { tick: [], tins: [], reflectors: [], event: [], truth: [], app: [],
      flows: [] }, tEnd: 0 };
  useTwin.setState({ replay, mode: 'live', playing: false });
  const ws = new WebSocket(url);
  ws.onmessage = (msg) => {
    const f = JSON.parse(msg.data);
    if (f.type === 'header') { replay.header = f; return; }
    if (f.type === 'truth' && replay.header.source === 'router') return;
    const list = (replay.byType[f.type] ??= []);
    list.push(f);
    if (list.length > 20000) list.splice(0, 5000);   // keep memory bounded
    replay.tEnd = Math.max(replay.tEnd, f.t);
    useTwin.setState({ t: replay.tEnd });            // follow the newest frame
  };
  ws.onclose = () => useTwin.setState({ mode: 'live-disconnected' });
  return ws;
}
```

Because live frames go into the same structures as a replay, every scene component works unchanged in both modes. The timeline in live mode shows the last 5 minutes and lets the presenter scrub back.

### Security and privacy in live mode

- The rpcd user `kit` is read-only and exists only on the demo kit image.
- The bridge and the twin run on the hub laptop and talk only over the LAN and localhost.
- Nothing is sent off the laptop. The live log is filed in the ledger like any other run.

## Extending the twin

- **Comparator overlay:** load two replays of the same scenario (VeriQ and a comparator arm) and draw the comparator's lane as a ghost pipe, with both arms and run IDs labelled.
- **Wi-Fi layer:** station signal and retry rate as a halo around each wireless device, from the WIFI evidence group.
- **Operator view (P2 idea):** one small twin per pilot home, from aggregated receipts; it needs consent and the DPDP Act review of Chapter 17 first.

## Acceptance checklist

| Item | Done when |
|---|---|
| Replay of any ledger run | `build_replay.py` + `validate.py` pass; the twin loads it |
| Tags | Legend visible; tag audit reports zero untagged meshes |
| Truth separation | Truth objects appear only in lab streams; inferred and true ISP queues drawn side by side |
| Event panel | Every action marker opens its decision-log line, verdict and receipt |
| Offline | Runs from `twin/dist/` with the network cable unplugged |
| Performance | Targets above met on the demo laptop and the booth display |
| Live mode | Bridge connects as the read-only user; disconnection shown within 2 s; live log saved |
| Licences | `twin/ASSETS.md` lists every third-party asset and its licence |
