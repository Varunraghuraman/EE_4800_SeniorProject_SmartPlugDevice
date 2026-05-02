# EE_4800_SeniorProject_SmartPlugDevice
Python code for a voice activated smart plug device on EDGE 
# Edge Voice Smart Plug

A privacy-preserving, voice-activated smart plug that switches a 120 V AC load entirely through on-device speech recognition — no cloud, no network calls, no API keys. Designed and built as the Senior Design (DB&T) project at Kennesaw State University, Spring 2026.

**Team J:** Nathan Kirkwood, Varun Raghuraman, Javon Barron
**Faculty Mentor:** Dr. Cyril Okhio
**Department:** Electrical and Computer Engineering, KSU

## What it does

Say **"hey scrappy"** — the device wakes up. Say **"lights on"** — the relay closes and your lamp turns on. Say **"lights off"** — the relay opens. The Sense HAT LED matrix gives you visual feedback at every step. All voice recognition runs locally on a Raspberry Pi 4 using the Vosk offline speech recognition toolkit.

## Repository layout

```
.
├── poc/                          # Base proof-of-concept (Phase 2)
│   ├── app.py                    # entry point
│   ├── audio.py                  # Vosk + sounddevice pipeline
│   ├── display.py                # Sense HAT animations
│   └── state_machine.py          # FSM with GPIO relay control
│
├── power_profile/                # Power-profiling instrumented version
│   ├── app_with_power.py         # entry point with PowerTracker
│   ├── audio.py                  # (identical to poc/audio.py)
│   ├── display.py                # (identical to poc/display.py)
│   ├── state_machine_with_power.py
│   ├── power_tracker.py          # background sampler, per-state attribution
│   └── power_monitor.py          # standalone runner (no FSM)
│
├── data/                         # Captured CSVs from power-profile runs
│   ├── baseline_idle.csv
│   ├── light_use.csv
│   └── heavy_use.csv
│
└── README.md
```

## Hardware

| Component | Role |
|---|---|
| Raspberry Pi 4 (4 GB) | Main controller |
| Audio-Technica ATR4650-USB | Voice input (USB, 44.1 kHz native) |
| Raspberry Pi Sense HAT (Rev 2) | Visual state feedback (8×8 RGB matrix) |
| Adafruit Perma-Proto Pi HAT | GPIO breakout for relay wiring |
| 5 V single-channel relay (active-low) | Switches 120 V AC mains |
| 1N4148 diode + 20D201K MOV + 10 A fuse | Protective components on AC side |

## Software stack

- Raspberry Pi OS (64-bit Trixie)
- Python 3.12
- [Vosk](https://alphacephei.com/vosk) (offline speech recognition, ~40 MB English model)
- `sounddevice` (audio capture via PortAudio)
- `RPi.GPIO` (relay control)
- `sense-hat` (LED matrix)
- `psutil` (only required for power-profile version)

## Getting started

### 1. Install system dependencies

On the Pi:

```bash
sudo apt update
sudo apt install -y portaudio19-dev unzip wget python3-numpy
```

### 2. Install Python dependencies

```bash
pip install vosk sounddevice RPi.GPIO --break-system-packages

# Only if running the power-profile version:
pip install psutil --break-system-packages
```

### 3. Download the Vosk model

```bash
cd poc/  # or power_profile/
wget https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
unzip vosk-model-small-en-us-0.15.zip
mv vosk-model-small-en-us-0.15 model
rm vosk-model-small-en-us-0.15.zip
```

### 4. Find your USB microphone's device index

```bash
python3 -c "
import sounddevice as sd
for i, d in enumerate(sd.query_devices()):
    if d['max_input_channels'] > 0:
        print(f'  index {i}: {d[\"name\"]}  ({int(d[\"default_samplerate\"])} Hz)')
"
```

Find the line with your USB mic and update `MIC_DEVICE_INDEX` at the top of `app.py` (or `app_with_power.py`).

### 5. Wire the relay

| Pi pin | Relay pin |
|---|---|
| 5 V (physical pin 2 or 4) | VCC |
| GND (physical pin 6) | GND |
| GPIO 4 (physical pin 7) | IN |

The AC mains side wires through the relay's COM and NO terminals to the lamp's hot wire. **Use a fuse and MOV on the mains side** — see project paper for the full safety scheme. Do not work on AC wiring while plugged in.

### 6. Run it

Base version (no power tracking):

```bash
cd poc/
python3 app.py
```

Power-profiling version (writes `power_log.csv`):

```bash
cd power_profile/
python3 app_with_power.py
```

Press Ctrl+C to stop. The power version prints a summary report to the terminal on shutdown.

## How it works

**Two-state finite state machine:**

- `SLEEPING`: Sense HAT scrolls "zzz...", system continuously listens for the wake phrase.
- `AWAKE`: Sense HAT shows solid blue. System listens for an ON or OFF command. Returns to SLEEPING after a successful command, an error (already-on / already-off), or a 5-second timeout.

**Vosk pipeline:**

- USB mic → 16 kHz mono PCM (resampled in software with `np.interp`) → Vosk acoustic model (TDNN) → lexicon → n-gram language model → recognized text → phrase matching.

**Recognized phrases:**

- Wake: `"hey scrappy"`, `"scrappy"`
- ON: `"lights on"`, `"turn on"`, `"light on"`
- OFF: `"lights off"`, `"turn off"`, `"light off"`

## Power profile (measured)

Captured across three 200-second runs with `power_tracker.py`:

| Scenario | Avg power | Peak | Energy/cmd |
|---|---|---|---|
| Baseline (idle) | **3.73 W** | 4.48 W | — |
| Light use (4 cmd) | 3.75 W | 4.75 W | 1.02 J |
| Heavy use (12 cmd) | 3.84 W | 5.66 W | 1.89 J |

CPU temperature stable at 45–50 °C across all runs (no thermal throttling). Projected annual energy at 24/7 operation: **32.7 kWh/yr** (~$4.57 at $0.14/kWh).

For comparison, commercial smart speakers (Echo Dot 5, Nest Mini 2) draw ~1.5 W idle per the [NRDC 2019 study](https://www.nrdc.org/resources/always-smart-speakers-now-use-more-energy). The 2.5× gap is attributable to general-purpose silicon vs. custom NN accelerators, not architectural limitation.

## Hardware-software design history

The original platform was the ESP32-S3 with the ESP-SR speech recognition framework. After ESP-IDF v6.0 / ESP-SR v1.9.0 toolchain incompatibilities (missing `__getreent` symbol, no English wake words in the registry-distributed model), the team migrated to the Raspberry Pi 4. The actuation circuit (2N2222 driver, SRD-05VDC relay, 1N4148 diode, MOV, 10 A fuse) carried over unchanged because the relay control interface is identical between platforms.

The actuation circuit was validated in MATLAB Simulink under three scenarios:

- **Nominal:** 71.4 mA through coil, back-EMF clamped at 5.7 V
- **Missing-diode fault:** 1,100 V back-EMF transient (27× transistor breakdown rating)
- **Coil-short fault:** transistor dissipates 1.35 W (vs. 0.6 W rating) — justifies the upstream fuse

## Troubleshooting

**`PaErrorCode -9997 Invalid sample rate`** — your USB mic doesn't support 16 kHz natively. The audio pipeline handles this automatically by resampling; this error means the mic device wasn't detected correctly. Re-run the device-index lookup in step 4.

**Sense HAT not responding** — the Pi may not be detecting the HAT through the Perma-Proto. Add this to `/boot/firmware/config.txt`:

```
dtoverlay=rpi-sense
```

Then reboot.

**GPIO 4 not toggling** — verify with a multimeter probing physical pin 7 (GPIO 4) and physical pin 9 (GND). You should see clean transitions between 0 V and 3.3 V when the FSM toggles state.

**No `psutil` module** — only required for the power-profile version. Install with `pip install psutil --break-system-packages`.

## Acknowledgments

Thanks to **Dr. Cyril Okhio** for guidance and mentorship throughout the project; **Kombete Fumey** and **Kulsum Saber** at the Engineering Technology Center for hardware troubleshooting support; and **Eliot Sanguinetti** for providing the perforated breadboard used in the final assembly.

## License

Educational project — code is provided as-is for academic reference. Vosk is licensed under Apache 2.0. The voice model `vosk-model-small-en-us-0.15` is licensed under Apache 2.0 by Alpha Cephei.
