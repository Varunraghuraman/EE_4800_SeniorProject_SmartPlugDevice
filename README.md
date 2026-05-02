# Edge Voice Smart Plug

Voice-activated smart plug using on-device speech recognition. Built for the Senior Design (DB&T) project at Kennesaw State University, Spring 2026.

**Team J:** Nathan Kirkwood, Varun Raghuraman, Javon Barron
**Faculty Mentor:** Dr. Cyril Okhio
**Department:** Electrical and Computer Engineering, KSU

Say `"hey scrappy"` to wake the device, then `"lights on"` or `"lights off"` to toggle a 120 V AC load via a relay. All speech recognition runs locally on a Raspberry Pi 4 — no internet connection required.

## Files

| File | Purpose |
|---|---|
| `app.py` | Main entry point. Wires together audio, display, and state machine. |
| `app_with_power.py` | Same as `app.py`, but also instantiates `PowerTracker` and writes `power_log.csv`. |
| `audio.py` | Audio capture pipeline. Uses `sounddevice` to read from the USB mic and feeds 16 kHz samples to Vosk for recognition. |
| `display.py` | Sense HAT animations for each state (sleeping, awake, on, off, errors, timeout). |
| `state_machine.py` | Two-state FSM (`SLEEPING` → `AWAKE`), wake-word and command matching, GPIO control of the relay. |
| `state_machine_with_power.py` | Same as `state_machine.py`, but reports state transitions and commands to the `PowerTracker`. |
| `power_tracker.py` | Background sampler that attributes CPU/power to the current FSM state and writes per-event rows to a CSV. |
| `power_monitor.py` | Standalone tool. Logs estimated power consumption over a fixed duration without running the voice pipeline. |

## Setup

Install dependencies:

```bash
sudo apt install -y portaudio19-dev unzip wget python3-numpy
pip install vosk sounddevice RPi.GPIO --break-system-packages
pip install psutil --break-system-packages   # only for power-profile version
```

Download the Vosk speech recognition model:

```bash
wget https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
unzip vosk-model-small-en-us-0.15.zip
mv vosk-model-small-en-us-0.15 model
rm vosk-model-small-en-us-0.15.zip
```

This creates a `model/` folder next to the Python files. The code expects this folder to exist.

Find your USB mic's device index and update `MIC_DEVICE_INDEX` at the top of `app.py` (and `app_with_power.py` if you're using it):

```bash
python3 -c "import sounddevice as sd; print(sd.query_devices())"
```

## Run

Base version:

```bash
python3 app.py
```

With power profiling:

```bash
python3 app_with_power.py
```

Press Ctrl+C to stop. The power version prints a summary report and writes `power_log.csv`.

## Hardware

- Raspberry Pi 4 (4 GB)
- Audio-Technica ATR4650-USB microphone
- Raspberry Pi Sense HAT (Rev 2)
- 5 V single-channel relay (active-low) wired to GPIO 4
- 1N4148 flyback diode, 20D201K MOV, 10 A slow-blow fuse on the AC side

## Acknowledgments

Thanks to Dr. Cyril Okhio for guidance throughout the project, Kombete Fumey and Kulsum Saber at the Engineering Technology Center for hardware support, and Eliot Sanguinetti for the perforated breadboard.
