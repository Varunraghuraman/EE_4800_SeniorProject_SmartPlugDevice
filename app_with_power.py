"""Edge Voice Smart Plug — Pi 4 with per-state power tracking.

Entry point. Instantiates the audio pipeline, Sense HAT display,
PowerTracker, and the power-aware StateMachine, then starts the run loop.

Run with:
    python3 app_with_power.py
"""

import os
from audio import AudioPipeline
from display import Display
from state_machine_with_power import StateMachine
from power_tracker import PowerTracker

MIC_DEVICE_INDEX = 3   # change if your USB mic is at a different index
HERE = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(HERE, "model")
POWER_LOG_PATH = os.path.join(HERE, "power_log.csv")


def main():
    print("=" * 50)
    print("  EDGE VOICE SMART PLUG (with power tracking)")
    print("=" * 50)
    print("  Wake word : 'hey scrappy'")
    print("  Commands  : 'lights on' / 'lights off'")
    print(f"  Power log : {POWER_LOG_PATH}")
    print("=" * 50)

    display = Display()
    audio = AudioPipeline(MODEL_PATH, MIC_DEVICE_INDEX)
    audio.start()

    power = PowerTracker(csv_path=POWER_LOG_PATH)
    power.start()

    fsm = StateMachine(audio, display, power_tracker=power)

    try:
        fsm.run()
    finally:
        audio.stop()
        display.clear()
        power.stop_and_report()
        print("\nBye.")


if __name__ == "__main__":
    main()