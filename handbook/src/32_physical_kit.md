# Physical Demo Kit

The physical kit lets a judge turn a knob and watch VeriQ adapt. It is a real OpenWrt router running VeriQ, in front of an emulated ISP link, with a control panel that injects the faults from the evaluation: a capacity drop, remote-path delay, a lying reflector and a controller crash. LED bars and a small display show what VeriQ measured and decided, next to the emulator's ground truth. This chapter specifies the kit completely: block diagram, network plan, wiring, firmware, protocol, safety interlocks, enclosure, bill of materials, assembly and tests.

The kit is a P1 deliverable (Sprint 5+, docs/11 §18) and the second stretch track in docs/05 §5. It reuses deployment view D3 (a Raspberry Pi with a USB 3 Gigabit Ethernet adapter running OpenWrt 24.10) and the lab's emulation scripts. Chapter 29 describes how the kit is used in the live demo.

## Purpose and design rules

1. **The judge drives, VeriQ observes.** The panel talks only to the ISP emulator, plus one restricted command to kill the daemon. It never tells `veriqd` what fault was injected. VeriQ must work out what happened from its own telemetry, exactly as in the lab's fault-blind scenarios (docs/05 §4: "VeriQ responds from telemetry only, never from a hidden scenario label").
2. **Emulation is labelled on the hardware.** The panel carries the printed words "EMULATED ISP LINK". The scoreboard shows the emulator's true capacity labelled "truth (lab)".
3. **Offline.** Every server, reflector and video source lives on the emulator. The kit needs no internet and no venue Wi-Fi.
4. **Safe by construction.** Faults revert by themselves, the dangerous button is covered and armed, mains voltage stays inside certified adapters, and losing the panel or the hub returns the emulator to a clean baseline.
5. **Same software as the lab.** The router runs the release packages with a documented kit configuration; the emulator runs the lab's scripts. Nothing on the router exists only for the demo except a read-only rpcd user and a restricted SSH key, both removed after the event.

## Block diagram

![Physical demo kit block and wiring diagram.](figures/fig17_physical_kit.svg)

| Unit | Hardware | Role |
|---|---|---|
| Router (system under test) | Raspberry Pi 5, 4 GB, active cooler, official PSU; USB 3 to 2.5 GbE adapter | OpenWrt 24.10 with VeriQ; on-board Ethernet = WAN, USB adapter = LAN |
| ISP emulator | Mini PC with two Ethernet ports (recommended), or a second Pi with a USB adapter, or an old laptop | Ubuntu 24.04; network namespaces for the ISP bottleneck (tbf with a bloated FIFO), remote delay (netem), reflectors, and servers (Jitsi Meet with its video bridge, DASH, file server, game echo); `emu-agent` |
| LAN switch | 5-port Gigabit, unmanaged | Connects router LAN, call laptop, bulk client and hub laptop |
| Call laptop | Team laptop | Jitsi call in Chromium with the stats overlay |
| Bulk client | Old laptop, Pi 4 or the hub laptop | Four TCP downloads or uploads to the file server |
| Hub laptop | Team laptop with a USB Ethernet adapter | LAN client; management link to the emulator; MQTT broker; `kit-bridge`; scoreboard; 3D twin (Chapter 30) |
| Control panel | ESP32 DevKitC, rotary encoder, five buttons, ARM switch, WS2812B LED strip, 0.96-inch OLED | Judge input and at-a-glance output; USB to the hub laptop |
| Optional booth display | 7-inch HDMI display | Twin in live mode |
| Optional retail router | ARM OpenWrt router (deployment view D4) | Swapped in for the Pi to show VeriQ on real home-gateway silicon |

**Three separate paths** keep the experiment clean:

- **Data path:** clients → switch → router LAN → router WAN → emulator → servers and reflectors. This is the only path the measured traffic uses.
- **Management path:** a direct cable between the hub laptop's USB Ethernet adapter and the emulator's second port. Fault commands and truth data use it and never cross the shaped link.
- **Panel path:** USB serial between the ESP32 and the hub laptop. It also powers the ESP32. No Wi-Fi is involved.

The hub laptop also polls the router over the LAN for telemetry (status, per-tin statistics and the last decisions). That traffic is small and never crosses the WAN shaper.

## Network plan

| Network | Addresses | Notes |
|---|---|---|
| Home LAN | `192.168.1.0/24`; router `.1`; call laptop `.10`, bulk client `.11`, hub `.20` (DHCP reservations) | IPv6 ULA `fd00:1::/64` from the router for the IPv6 scenario (S9) |
| WAN access link | `100.64.10.0/30`; emulator `.1` (default gateway, the near probe target), router `.2` | Shared address space, as many carrier-grade NAT access networks use |
| Emulated internet: servers | `198.51.100.0/24`; Jitsi `.10`, DASH and file server `.20`, game echo `.30` | Documentation range; never routed outside the kit |
| Emulated internet: reflectors | `203.0.113.11`–`.18`, one network namespace each | Linux namespaces answer ICMP echo and timestamp requests, so one-way deltas work |
| Management | `172.16.99.0/30`; hub `.1`, emulator `.2` | Direct cable; MQTT and SSH only |

**Kit configuration of VeriQ.** The kit differs from the product defaults in exactly three documented places, recorded in the kit's run manifest:

- the reflector list (`list reflector4`) names the eight lab reflectors instead of public resolvers;
- `start_mode` is `live` ("Adapt now"), so the judge does not wait 24 h for SHADOW to end;
- `down_base_kbit` and `up_base_kbit` come from running the wizard against the emulator's 100/20 Mbit/s baseline line (90% of the lowest of three measurements, so about 90/18 Mbit/s; the wizard's result is recorded, not assumed).

> **Note.** With S_base = 90 Mbit/s, the floor is S_min = max(1 Mbit/s, 0.10·S_base) = 9 Mbit/s. The configuration rule in docs/09 A.2 requires S_min ≤ 0.8 × the lowest capacity used, so the download knob stops at 12 Mbit/s (0.8 × 12 = 9.6). For upload, S_min = 1.8 Mbit/s, and the knob stops at 4 Mbit/s.

### Inside the emulator

```text
  router WAN ── eth-rtr [ns isp] ── veth-core ══ [ns core] ── veth-inet ── [ns inet]
                  tbf (download:      tbf (upload:     netem (remote        ├─ servers
                  rate + bloated      rate + bloated   delay, off by        └─ veth-r1..r8
                  FIFO)               FIFO)            default)                  └─ [ns refl1..8]
  near target = 100.64.10.1 on eth-rtr: unaffected by the core netem, so NEAR stays flat
```

The download bottleneck is a tbf on `eth-rtr` (egress toward the router); the upload bottleneck is a tbf on `veth-core` (egress toward the internet). Each tbf has a buffer of 300 ms at the baseline rate, like the Day-0 lab, so a bulk transfer fills it unless VeriQ shapes below the line rate. The buffer is fixed in bytes, so when the knob lowers the rate, the same buffer holds more milliseconds of delay, as real modems do.

### The fault agent

`emu-agent` subscribes to the command topic and calls one script per command. Every command sets an **absolute** state ("download capacity is now 20 Mbit/s"), never a relative change, so a repeated or delayed message cannot stack.

```bash
#!/usr/bin/env bash
# emu-fault.sh: apply one kit fault on the ISP emulator. LAB EQUIPMENT ONLY.
set -euo pipefail
BASE_DOWN_KBIT=100000; BASE_UP_KBIT=20000; BUF_MS=300
nsx() { ip netns exec "$@"; }

tbf_set() {  # tbf_set <ns> <dev> <kbit> <base_kbit>
  local ns=$1 dev=$2 kbit=$3 base=$4
  local limit=$(( base * 1000 / 8 * BUF_MS / 1000 ))   # bytes: 300 ms at the base rate
  local burst=$(( kbit * 125 / 100 ))                  # about 10 ms of data
  (( burst < 16000 )) && burst=16000
  nsx "$ns" tc qdisc replace dev "$dev" root tbf rate "${kbit}kbit" \
      burst "$burst" limit "$limit"
}

case "${1:-}" in
  capacity)        # capacity <down_kbit> <up_kbit>
    tbf_set isp eth-rtr "$2" "$BASE_DOWN_KBIT"
    tbf_set isp veth-core "$3" "$BASE_UP_KBIT" ;;
  remote_delay)    # remote_delay on|off  (+80 ms beyond the first hop)
    if [ "$2" = on ]; then
      nsx core tc qdisc replace dev veth-inet root netem delay 80ms limit 10000
    else
      nsx core tc qdisc del dev veth-inet root 2>/dev/null || true
    fi ;;
  lying_reflector) # lying_reflector on|off  (reflector 3 answers late and jittery)
    if [ "$2" = on ]; then
      nsx inet tc qdisc replace dev veth-r3 root netem delay 150ms 60ms limit 1000
    else
      nsx inet tc qdisc del dev veth-r3 root 2>/dev/null || true
    fi ;;
  reset)
    "$0" remote_delay off; "$0" lying_reflector off
    "$0" capacity "$BASE_DOWN_KBIT" "$BASE_UP_KBIT" ;;
  truth)           # print the true state as one JSON line
    nsx isp tc -s -j qdisc show dev eth-rtr ;;
  *) echo "usage: $0 capacity|remote_delay|lying_reflector|reset|truth" >&2; exit 2 ;;
esac
```

The netem `limit 10000` keeps the delay line from dropping packets: at 100 Mbit/s, 80 ms holds about 1 MB, which is roughly 670 full-size packets, more than half of netem's default limit of 1000. `emu-agent` turns the `truth` output into a truth message: the configured rates, the tbf backlog in bytes, and the true ISP queue delay (backlog × 8 / rate).

| Panel input | Emulator command | Scenario |
|---|---|---|
| Knob (download mode) | `capacity <knob> <current up>` | A1, A2, A3 |
| Knob press, then turn (upload mode) | `capacity <current down> <knob>` | S4, A9 |
| WAN DROP | `capacity 20000 <current up>` | S2, A1 |
| REMOTE DELAY | `remote_delay on`, auto-off after 120 s | S6, A4 |
| LYING REFLECTOR | `lying_reflector on`, auto-off after 120 s | S7, A5 |
| KILL | Hub runs the restricted SSH command on the router | S8, A15 |
| RESET | `reset` | — |

## Panel hardware and wiring

### Components

- **ESP32 DevKitC** with an ESP32-WROOM-32 module.
- **Rotary encoder** module (KY-040 type) with a push switch: capacity knob; a press toggles download/upload.
- **Five momentary buttons:** WAN DROP (large red dome), REMOTE DELAY, LYING REFLECTOR, KILL (under a hinged safety cover), RESET.
- **ARM key switch** (or a latching toggle): the panel ignores every input while disarmed.
- **WS2812B LED strip**, 60 LEDs in five segments of 12: WAN, RT, IV, BE, BK.
- **0.96-inch SSD1306 OLED**, 128 × 64, I2C.
- **74AHCT125 level shifter**: the ESP32's 3.3 V data line drives the 5 V strip reliably.
- **5 V, 4 A external power supply** (certified adapter) for the LEDs, an inline fuse, a 1000 µF capacitor across the strip supply, and a 330 Ω series resistor in the data line.

### Wiring table

| Signal | ESP32 pin | Connects to | Notes |
|---|---|---|---|
| Encoder A (CLK) | GPIO 32 | Encoder CLK | Power the module from **3.3 V**, not 5 V; module pull-ups then sit at 3.3 V |
| Encoder B (DT) | GPIO 33 | Encoder DT | Polled in the main loop |
| Encoder switch | GPIO 25 | Encoder SW → GND | Internal pull-up |
| WAN DROP | GPIO 26 | Button → GND | Internal pull-up; active low |
| REMOTE DELAY | GPIO 27 | Button → GND | Internal pull-up |
| LYING REFLECTOR | GPIO 19 | Button → GND | Internal pull-up |
| KILL | GPIO 13 | Button (under cover) → GND | Must be held 1 s |
| RESET | GPIO 4 | Button → GND | Internal pull-up |
| ARM switch | GPIO 23 | Switch → GND | Closed = armed |
| LED data | GPIO 18 | 74AHCT125 input A1; output Y1 → 330 Ω → strip DIN | Shifter powered from 5 V; its OE pin tied to GND |
| OLED SDA / SCL | GPIO 21 / GPIO 22 | OLED SDA / SCL | OLED VCC from 3.3 V |
| Strip +5 V | — | External 5 V supply via fuse | 1000 µF capacitor across +5 V and GND at the strip input |
| Ground | GND | Strip GND, supply GND, shifter GND, OLED GND | **One common ground** for every part |
| ESP32 power | USB | Hub laptop | Never also feed the external 5 V into the ESP32's 5 V pin |

These pins avoid the ESP32's boot-strapping pins (GPIO 0, 2, 5, 12, 15) and the input-only pins 34–39, which have no internal pull-ups. On an ESP32-WROVER module, GPIO 16 and 17 are used by its PSRAM; they are not used here either.

### Power budget (worked example)

A WS2812B LED can draw roughly 60 mA at full white (a common rule of thumb; measure your strip). Sixty LEDs at full white would need about 3.6 A. The firmware caps brightness at 64 of 255 (about 25%) and lights only coloured bars, so the worst case is about 60 × 60 mA × 0.25 ≈ 0.9 A. A 5 V, 4 A supply leaves a large margin, and the fuse protects the wiring if a strip shorts. All values are approximate; check them with a USB or inline current meter during the bench test.

## Firmware

The firmware is deliberately simple: it reports inputs and draws what the hub tells it to draw. All logic that could need a fix on demo day (interlocks, mapping to faults, text on the display) lives in the hub's Python code.

- **Framework:** Arduino core for the ESP32 (ESP-IDF underneath).
- **Libraries:** FastLED (LEDs), U8g2 (OLED) and ArduinoJson (messages). Pin exact library versions in the build file and check each licence at that version.
- **Status:** the firmware is demo equipment. It is not part of any VeriQ package and is never shipped to households.

The skeleton below is Arduino C++, shown as a `text` block.

```text
// panel.ino: VeriQ demo-kit panel firmware (Arduino core for ESP32). Demo equipment only.
#include <Arduino.h>
#include <FastLED.h>
#include <U8g2lib.h>
#include <ArduinoJson.h>

constexpr uint8_t PIN_ENC_A = 32, PIN_ENC_B = 33, PIN_ENC_SW = 25, PIN_ARM = 23;
constexpr uint8_t PIN_LED = 18;
constexpr int SEG = 12, SEGS = 5, NUM_LEDS = SEG * SEGS;   // WAN, RT, IV, BE, BK
constexpr uint8_t MAX_BRIGHT = 64;                         // about 25%: power budget
constexpr uint32_t HUB_TIMEOUT_MS = 3000, DEBOUNCE_MS = 30, KILL_HOLD_MS = 1000;

struct Button { uint8_t pin; const char* id; uint32_t hold; bool down; uint32_t t0; bool sent; };
Button buttons[] = {
  {26, "wan_drop", 0}, {27, "remote_delay", 0}, {19, "lying_reflector", 0},
  {13, "kill", KILL_HOLD_MS}, {4, "reset", 0}};

CRGB leds[NUM_LEDS];
const CRGB SEG_COLOUR[SEGS] = {CRGB(0x00, 0x72, 0xB2), CRGB(0xD5, 0x5E, 0x00),
  CRGB(0xE6, 0x9F, 0x00), CRGB(0x56, 0xB4, 0xE9), CRGB(0x00, 0x9E, 0x73)};
U8G2_SSD1306_128X64_NONAME_F_HW_I2C oled(U8G2_R0, U8X8_PIN_NONE);

uint8_t barLen[SEGS] = {0}, barSev[SEGS] = {0};   // length 0..SEG; 0 ok, 1 warn, 2 bad
int8_t truthIdx = -1;                             // WAN segment: true-capacity marker
char line[3][22] = {"BOOT", "", ""};
uint32_t seq = 0, lastHub = 0, lastDraw = 0, lastBeat = 0;
uint8_t encPrev = 0; int encAcc = 0;

void emit(const char* type, const char* id, int value) {
  JsonDocument doc;
  doc["seq"] = ++seq; doc["type"] = type; doc["id"] = id; doc["v"] = value;
  doc["armed"] = digitalRead(PIN_ARM) == LOW;
  serializeJson(doc, Serial); Serial.print('\n');
}

void pollEncoder() {                       // quadrature state table, polled
  static const int8_t T[16] = {0,-1,1,0, 1,0,0,-1, -1,0,0,1, 0,1,-1,0};
  uint8_t s = (digitalRead(PIN_ENC_A) << 1) | digitalRead(PIN_ENC_B);
  encAcc += T[(encPrev << 2) | s]; encPrev = s;
  if (encAcc >= 4)  { emit("knob", "step", +1); encAcc = 0; }   // one detent
  if (encAcc <= -4) { emit("knob", "step", -1); encAcc = 0; }
}

void pollButtons(uint32_t now) {
  for (auto& b : buttons) {
    bool pressed = digitalRead(b.pin) == LOW;
    if (pressed && !b.down) { b.down = true; b.t0 = now; b.sent = false; }
    if (!pressed) b.down = false;
    uint32_t need = b.hold ? b.hold : DEBOUNCE_MS;
    if (b.down && !b.sent && now - b.t0 >= need) { emit("button", b.id, 1); b.sent = true; }
  }
}

void handleLine(const String& s) {         // messages from the hub
  JsonDocument doc;
  if (deserializeJson(doc, s)) return;
  lastHub = millis();
  const char* t = doc["t"] | "";
  if (strcmp(t, "disp") == 0) {
    for (int i = 0; i < 3; i++) strlcpy(line[i], doc["l"][i] | "", sizeof line[i]);
  } else if (strcmp(t, "bars") == 0) {
    for (int i = 0; i < SEGS; i++) { barLen[i] = doc["b"][i] | 0; barSev[i] = doc["s"][i] | 0; }
    truthIdx = doc["truth"] | -1;
  }
}

void draw(uint32_t now) {
  bool hubLost = now - lastHub > HUB_TIMEOUT_MS;
  bool blinkOn = (now / 250) % 2;
  fill_solid(leds, NUM_LEDS, CRGB::Black);
  for (int k = 0; k < SEGS && !hubLost; k++) {
    for (int i = 0; i < min<int>(barLen[k], SEG); i++) {
      bool show = barSev[k] < 2 || blinkOn;     // severity 2 blinks
      if (show) leds[k * SEG + i] = SEG_COLOUR[k];
    }
  }
  if (!hubLost && truthIdx >= 0 && truthIdx < SEG) leds[truthIdx] = CRGB(0xFF, 0xB0, 0x00);
  FastLED.show();
  oled.clearBuffer(); oled.setFont(u8g2_font_6x12_tf);
  if (hubLost) { oled.drawStr(0, 12, "HUB LOST"); oled.drawStr(0, 28, "inputs ignored"); }
  else for (int i = 0; i < 3; i++) oled.drawStr(0, 12 + 16 * i, line[i]);
  oled.drawStr(0, 63, digitalRead(PIN_ARM) == LOW ? "ARMED  EMULATED LINK" : "SAFE (disarmed)");
  oled.sendBuffer();
}

void setup() {
  Serial.begin(115200);
  for (auto& b : buttons) pinMode(b.pin, INPUT_PULLUP);
  pinMode(PIN_ENC_A, INPUT_PULLUP); pinMode(PIN_ENC_B, INPUT_PULLUP);
  pinMode(PIN_ENC_SW, INPUT_PULLUP); pinMode(PIN_ARM, INPUT_PULLUP);
  FastLED.addLeds<WS2812B, PIN_LED, GRB>(leds, NUM_LEDS);
  FastLED.setBrightness(MAX_BRIGHT);
  oled.begin();
}

void loop() {
  static String buf;
  uint32_t now = millis();
  pollEncoder(); pollButtons(now);
  static bool swDown = false;
  bool sw = digitalRead(PIN_ENC_SW) == LOW;
  if (sw && !swDown) emit("knob", "toggle_dir", 0);
  swDown = sw;
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n') { handleLine(buf); buf = ""; } else if (buf.length() < 512) buf += c;
  }
  if (now - lastDraw >= 33) { draw(now); lastDraw = now; }          // about 30 Hz
  if (now - lastBeat >= 1000) { emit("heartbeat", "panel", 0); lastBeat = now; }
}
```

The encoder switch is not debounced in this skeleton; add the same debounce as the buttons in the real firmware. The firmware reports the ARM state with every message, but it does not enforce the interlocks itself; the hub enforces them (defence in depth: a firmware bug cannot fire a fault).

## Protocol

### Transport

- **Panel ↔ hub:** USB serial, 115200 baud, 8N1, one JSON object per line, at most 512 bytes per line.
- **Hub ↔ emulator:** MQTT over the management cable. The broker (Mosquitto) runs on the hub, listening on the management interface and on localhost only.
- **Hub ↔ twin:** the twin bridge (Chapter 30) subscribes to the router-telemetry topic instead of polling the router a second time.
- **Optional wireless panel:** the ESP32 may publish to the same topics over Wi-Fi to a kit-private access point. USB serial is the default because it cannot be disturbed by the venue's radio environment.

### Topics and messages

| Topic | From → to | Example payload | QoS, retain |
|---|---|---|---|
| `kit/v1/panel/input` | hub (from serial) → log | `{"seq":41,"type":"button","id":"wan_drop","v":1,"armed":true}` | 1, no |
| `kit/v1/emu/cmd` | hub → emulator | `{"id":"c-41","cmd":"capacity","down_kbit":20000,"up_kbit":20000,"ttl_s":0}` | 1, no |
| `kit/v1/emu/ack` | emulator → hub | `{"id":"c-41","ok":true,"t_wall":"2026-12-20T11:02:07.412+05:30"}` | 1, no |
| `kit/v1/emu/truth` | emulator → hub, 4 Hz | `{"down_kbit":20000,"up_kbit":20000,"isp_queue_ms":212.5,"faults":["capacity"]}` | 0, yes |
| `kit/v1/router/telemetry` | hub → twin, scoreboard, 4 Hz | `{"state":"LIVE","S_down":18090,"S_up":17900,"diag":"WAN_LIKELY","level":2}` | 0, yes |
| `kit/v1/heartbeat/<node>` | every node, 1 Hz | `{"node":"emu","t_mono_ms":5123456}` | 0, no |

Messages from the hub to the panel are not MQTT; they go straight to the serial port:

```json
{"t":"disp","l":["LIVE dn 18.1 up 17.9","WAN_LIKELY L2 FAR+THR","TRUTH dn 20 up 20"]}
{"t":"bars","b":[2,1,3,6,10],"s":[0,0,0,1,0],"truth":3}
```

The telemetry numbers above are illustrative; on the kit they come from the router. Bar lengths are computed by the hub:

- **WAN segment:** S as a share of S_max (12 LEDs = S_max); the amber marker LED is the true capacity from the emulator.
- **Class segments:** each tin's throughput as a share of S (measured from per-tin byte counters).
- **Severity:** the tin's average delay against the wizard's grade boundaries: up to 5 ms is 0, up to 30 ms is 1, above 30 ms is 2 (blinking). These boundaries are VeriQ's own choice, labelled as such.

**Ordering and idempotency.** Every command has an ID and carries absolute values. The emulator acknowledges each ID once and ignores repeats. The hub shows "pending" on the scoreboard until the acknowledgement arrives.

## Hub software

`kit-bridge` is a small Python program on the hub laptop. It owns the interlocks, translates panel events into emulator commands, polls the router (rpcd over HTTP with a read-only user, as in Chapter 30) and draws the panel. `kitctl` is its command-line twin, used as the backup when the panel fails (Chapter 29).

```python
"""kit-bridge: panel (serial) <-> MQTT <-> emulator; router telemetry -> panel. Demo only."""
import json, subprocess, time
import serial                            # pyserial, BSD-3-Clause
import paho.mqtt.client as mqtt          # EPL-2.0 / EDL-1.0; demo tooling only

KNOB_DOWN = [12, 16, 20, 30, 40, 50, 60, 70, 80, 90, 100]   # Mbit/s, floor-safe range
KNOB_UP = [4, 6, 8, 10, 12, 14, 16, 18, 20]
FAULT_COOLDOWN_S = 10          # starting value: one fault at a time is readable
AUTO_REVERT_S = 120            # remote delay and lying reflector switch themselves off
KILL_CMD = ["ssh", "-i", "/etc/veriq-kit/kill_key", "-o", "BatchMode=yes",
            "root@192.168.1.1", "kill"]   # the router forces the real command

class Kit:
    def __init__(self):
        self.down_i, self.up_i, self.dir = len(KNOB_DOWN) - 1, len(KNOB_UP) - 1, "down"
        self.last_fault, self.timers, self.n = 0.0, {}, 0
        self.mq = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="kit-bridge")
        self.mq.connect("127.0.0.1", 1883)
        self.port = serial.Serial("/dev/ttyUSB0", 115200, timeout=0.05)

    def cmd(self, **kw):
        self.n += 1
        kw["id"] = f"c-{self.n}"
        self.mq.publish("kit/v1/emu/cmd", json.dumps(kw), qos=1)

    def capacity(self):
        self.cmd(cmd="capacity", down_kbit=KNOB_DOWN[self.down_i] * 1000,
                 up_kbit=KNOB_UP[self.up_i] * 1000, ttl_s=0)

    def on_input(self, ev):
        self.mq.publish("kit/v1/panel/input", json.dumps(ev), qos=1)
        if not ev.get("armed"):
            return                                    # interlock 1: ARM switch
        if ev["type"] == "knob":
            if ev["id"] == "toggle_dir":
                self.dir = "up" if self.dir == "down" else "down"
            elif self.dir == "down":
                self.down_i = max(0, min(len(KNOB_DOWN) - 1, self.down_i + ev["v"]))
            else:
                self.up_i = max(0, min(len(KNOB_UP) - 1, self.up_i + ev["v"]))
            self.capacity()
            return
        if ev["type"] != "button":
            return
        now = time.monotonic()
        if ev["id"] == "reset":                       # always allowed
            self.down_i, self.up_i = len(KNOB_DOWN) - 1, len(KNOB_UP) - 1
            self.cmd(cmd="reset"); self.timers.clear(); return
        if now - self.last_fault < FAULT_COOLDOWN_S:
            return                                    # interlock 2: cooldown
        self.last_fault = now
        if ev["id"] == "wan_drop":
            self.down_i = KNOB_DOWN.index(20); self.capacity()
        elif ev["id"] in ("remote_delay", "lying_reflector"):
            self.cmd(cmd=ev["id"], state="on", ttl_s=AUTO_REVERT_S)
            self.timers[ev["id"]] = now + AUTO_REVERT_S   # interlock 3: auto-revert
        elif ev["id"] == "kill":                     # interlock 4: cover + 1 s hold
            subprocess.run(KILL_CMD, timeout=5, check=False)

    def tick(self):
        now = time.monotonic()
        for name, due in list(self.timers.items()):
            if now >= due:
                self.cmd(cmd=name, state="off"); del self.timers[name]
        line = self.port.readline()
        if line:
            try:
                self.on_input(json.loads(line))
            except (ValueError, KeyError):
                pass                                  # malformed line: ignore, log
        # Router telemetry -> panel bars and text: see poll_router() (rpcd, Chapter 30).

if __name__ == "__main__":
    kit = Kit()
    kit.mq.loop_start()
    while True:
        kit.tick()
```

**The restricted kill key.** On the router, the kill key is installed in Dropbear's `authorized_keys` with a forced command, so the key can do one thing only:

```text
command="kill -9 $(pidof veriqd)",no-port-forwarding,no-agent-forwarding,no-pty ssh-ed25519 AAAA... kit-kill
```

Check that your Dropbear build honours these options before the event (try the key with another command and confirm it still only kills `veriqd`). Remove the key, and the read-only rpcd user, from the router after the event.

## Safety interlocks

| # | Interlock | Protects against | Where enforced |
|---|---|---|---|
| 1 | ARM key switch | Accidental presses during transport and setup | Hub (firmware only reports the switch) |
| 2 | Fault cooldown, 10 s (starting value) | Stacked faults that make the demo unreadable | Hub |
| 3 | Auto-revert of remote delay and lying reflector after 120 s | A forgotten fault that silently persists | Hub timer, plus `ttl_s` in the command so the emulator reverts even if the hub dies |
| 4 | KILL under a hinged cover, 1 s hold | Killing the daemon by accident | Panel hardware and firmware |
| 5 | Knob ranges 12–100 and 4–20 Mbit/s | Capacities below what the configured floor can follow | Hub tables |
| 6 | Dead-man: emulator resets to baseline if no hub heartbeat for 10 s | A crashed hub leaving the link degraded | `emu-agent` |
| 7 | Panel shows "HUB LOST" after 3 s without hub messages | The judge pressing buttons that do nothing | Firmware |
| 8 | Forced-command SSH key | The demo key being used for anything else | Router's Dropbear configuration |
| 9 | Fuse, single common ground, level shifter, 1000 µF capacitor, 330 Ω data resistor | Short circuits, LED damage, unreliable data | Panel wiring |
| 10 | No mains wiring inside the panel; certified adapters only | Electric shock | Design rule |
| 11 | LED brightness cap 25% | Overcurrent and glare | Firmware |
| 12 | Pi 5 active cooler; vents unobstructed in the case | Thermal throttling during the demo | Enclosure |

> **Honesty check.** The KILL button really sends `kill -9` to `veriqd`. Do not replace it with a softer stop "to be safe": the point of the demo is that a crash is survivable. If a judge asks, show the forced command.

## Enclosure

### Panel

- **Size:** a top plate of about 300 × 200 mm, tilted about 15° toward the judge, in a box 70 mm deep at the back.
- **Layout, left to right:** the capacity knob with a printed scale (12 to 100 Mbit/s), the large WAN DROP button, REMOTE DELAY and LYING REFLECTOR, then KILL under its cover and RESET at the far right, away from the other buttons. The LED segments run along the top edge with printed labels WAN, RT, IV, BE, BK; the OLED window sits beside the ARM key.
- **Printed labels:** "VeriQ demo kit · EMULATED ISP LINK" on the top edge, and a short legend: "solid = VeriQ's rate, amber dot = true capacity (lab)".
- **Diffuser:** the LED strip sits in a channel behind 3 mm opal acrylic, or behind a 0.6 mm wall printed in white PLA, so individual LEDs do not glare.

### Build options

| Option | Material | Settings and notes |
|---|---|---|
| 3D-printed | PETG (heat and impact) or PLA (easier) | 0.4 mm nozzle, 0.2 mm layers, 3 perimeters, 20–25% gyroid infill, supports only under the button bosses. Most print beds are smaller than 300 mm, so print the top plate in two halves joined by a printed spline and M3 screws into heat-set inserts |
| Laser-cut | 3 mm acrylic or plywood | Finger-jointed box; engraved labels; quicker if a maker space is available |

**Hole sizes:** measure each button's thread, the encoder shaft and the OLED's visible area with calipers, and add 0.3–0.5 mm clearance. Buttons of the same nominal size differ between suppliers.

**Inside the panel:** mount the ESP32 and the level shifter on a small perfboard with screw terminals, so a wire can be replaced without soldering at the venue. Add strain relief for the USB cable and the 5 V input.

### Transport

Pack the router, the emulator, the switch, the panel and all cables in one foam-lined hard case. Label both ends of every cable (for example "R-WAN ↔ E-RTR"), and tape a printed wiring diagram (fig17) inside the lid.

## Bill of materials

All prices are **approximate, in Indian rupees, and must be verified before purchase**. Where docs/06 §2 gives an estimate, it is used as the anchor of the range.

| Item | Qty | Role | Approx. ₹ (range) | Notes |
|---|---|---|---|---|
| Raspberry Pi 5 (4 GB) + active cooler + 27 W PSU + 64 GB microSD | 1 | Router | 8,000–9,500 | docs/06: about 8,500 |
| USB 3 to 2.5 GbE adapter (RTL8156B class) | 1 | Router LAN port | 1,500–2,500 | docs/06: about 2,000; check the OpenWrt driver package |
| 5-port Gigabit switch | 1 | LAN | 1,000–1,500 | docs/06: about 1,200 |
| ISP emulator: dual-NIC mini PC | 1 | Emulator and servers | 12,000–22,000 | Or a team laptop with a USB NIC (₹0–2,000), or a second Pi 5 + adapter (docs/06: about 10,500; may struggle with the call bridge) |
| USB Ethernet adapter (hub management link) | 1 | Management path | 800–1,500 | — |
| ESP32 DevKitC (WROOM-32) | 1 (+1 spare) | Panel controller | 400–900 each | Keep a pre-flashed spare |
| Rotary encoder module with push switch | 1 | Capacity knob | 80–250 | Buy two |
| Arcade buttons (one large, four standard) | 5 | Fault inputs | 500–1,500 total | docs/06: about 300 for the button set and wires |
| Safety cover for KILL + ARM key switch | 1 + 1 | Interlocks | 200–600 | — |
| WS2812B strip, 60 LEDs/m, 1 m | 1 | LED bars | 400–1,000 | — |
| SSD1306 0.96-inch OLED, I2C | 1 | Display | 200–500 | — |
| 74AHCT125 level shifter | 1 | LED data level | 50–150 | — |
| 5 V 4 A certified adapter, inline fuse holder, 1000 µF capacitor, resistors | 1 set | LED power | 500–1,200 | — |
| Perfboard, screw terminals, wires, connectors, heat-set inserts | 1 set | Assembly | 300–800 | — |
| Enclosure material (filament or acrylic) | 1 | Panel box | 500–2,000 | — |
| Ethernet cables (0.5–1 m) | 6 | Cabling | 500–1,000 | Short, labelled |
| Foam-lined hard case | 1 | Transport | 1,500–4,000 | — |
| Optional: 7-inch HDMI display | 1 | Twin at the booth | 3,000–5,000 | docs/06: about 4,000 |
| Optional: ARM OpenWrt retail router | 1 | Deployment view D4 | 8,000–10,000 | docs/06: about 9,000 |

**Totals (approximate).** Excluding the emulator and the optional items, the kit costs about ₹16,000–29,000. With a dual-NIC mini PC as the emulator it rises to about ₹28,000–51,000; using a team laptop as the emulator keeps it near the lower figure. The laptops for the call and the hub are the team's own. These are sums of the ranges above, not quotes.

> **Implementation tip.** Before ordering the Pi 5 and the USB adapter, confirm in the OpenWrt Table of Hardware that the 24.10 release has an image for the board and a driver package for the adapter's chipset. The same check applies to the optional retail router.

## Assembly

1. **Router.** Flash OpenWrt 24.10 for the Pi 5. Install the USB NIC driver and assign on-board Ethernet to WAN and the USB adapter to LAN. Install the VeriQ packages from the signed feed (Chapter 16). Run the wizard against the emulator, then apply the three kit settings and record them in the manifest. Run `veriqctl health` and `veriqctl selftest`.
2. **Emulator.** Install Ubuntu 24.04 and the lab repository. Build the namespaces of the emulator diagram with the lab scripts (Chapter 25), start the servers and reflectors, and install `emu-agent` as a systemd service that starts at boot with the baseline (100/20 Mbit/s, no faults).
3. **Panel, bench stage.** Before anything goes into the box, test each block on the bench: LED strip with a test pattern, OLED with text, each button and the encoder with the serial monitor.
4. **Panel, final wiring.** Mount the parts, wire them as in the wiring table, fit the fuse and the capacitor, then check continuity and confirm there is no short between +5 V and GND before applying power.
5. **Firmware.** Flash the panel and the spare ESP32 with the same pinned build.
6. **Hub.** Install Mosquitto (management and localhost listeners only), `kit-bridge`, `kitctl`, the twin and the scoreboard. Install the kill key and the read-only rpcd credentials.
7. **Integration.** Cable the data path, the management path and the panel. Run the test checklist below.
8. **Label and pack.** Label cables, photograph the assembled kit for the setup card, and pack.

## Test checklist

Targets are starting values, to be confirmed on the assembled kit.

| # | Test | Method | Pass criterion (target) |
|---|---|---|---|
| 1 | Cold start | Power on all units in the documented order | Ready (LIVE, call possible) within 5 min |
| 2 | Router health | `veriqctl health`, `veriqctl selftest` | Both pass, including the tin self-test in both directions |
| 3 | Reflectors | Router's reflector table | At least 5 far reflectors qualified, timestamp support shown |
| 4 | Buttons | Press each while armed | Event in the hub log within 100 ms; emulator acknowledgement within 500 ms |
| 5 | Knob | Turn through every detent in both modes | Emulator `tc -s qdisc` shows each rate; scoreboard truth follows |
| 6 | ARM interlock | Press every button while disarmed | No command sent |
| 7 | KILL interlock | Tap KILL briefly; then hold 1 s | Tap: nothing. Hold: `veriqd` killed; SAFE within 12 s; procd restarts it |
| 8 | Cooldown | Two faults 3 s apart | Second ignored, with a scoreboard note |
| 9 | Auto-revert | Press REMOTE DELAY and wait | Off after 120 s; truth shows no faults |
| 10 | Dead-man | Stop `kit-bridge` with a fault active | Emulator back to baseline within 10 s; panel shows "HUB LOST" |
| 11 | LED mapping | Send traffic in each class (tin self-test traffic) | The matching segment lights; the WAN marker matches truth |
| 12 | Scenario smoke | WAN DROP, REMOTE DELAY, LYING REFLECTOR, KILL in turn | Expected diagnosis shown for each; decision log recorded |
| 13 | Offline | Disconnect every external network | Full demo still runs |
| 14 | Soak | `kitctl` presses a random allowed input every 30–90 s for 2 h | No crash, no stuck fault, no reboot |
| 15 | Thermal | Read the Pi's temperature during the soak (`/sys/class/thermal`) | Below the throttling point throughout |
| 16 | Power | Inline meter on the LED supply during a full-bar test | Below the budget (about 1 A) |
| 17 | Transport | Pack, carry, unpack and rebuild | Rebuilt and passing tests 1–4 within 20 min |

Record every run of this checklist with its date and results in the evidence ledger under `kit/`. A kit test failure found at rehearsal is a discrepancy to log and fix, exactly like a lab result that differs from expectation.
