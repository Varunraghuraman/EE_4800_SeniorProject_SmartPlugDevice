"""Edge Voice Smart Plug — Pi 4."""

import os
from audio import AudioPipeline
from display import Display
from state_machine import StateMachine

MIC_DEVICE_INDEX = 1  # change if your USB mic is at a different index
MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "model")


def main():
    print("=" * 50)
    print("  EDGE VOICE SMART PLUG")
    print("=" * 50)
    print("  Wake word : 'hey scrappy'")
    print("  Commands  : 'lights on' / 'lights off'")
    print("=" * 50)

    display = Display()
    audio = AudioPipeline(MODEL_PATH, MIC_DEVICE_INDEX)
    audio.start()

    fsm = StateMachine(audio, display)
    try:
        fsm.run()
    finally:
        audio.stop()
        display.clear()
        print("\nBye.")


if __name__ == "__main__":
    main()