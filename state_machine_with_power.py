"""State machine for the Edge Voice Smart Plug — power-profiling version.

Same FSM logic as the base state_machine.py, but accepts a PowerTracker
instance and reports state transitions and command executions to it
so per-state energy can be attributed.
"""

import time
from enum import Enum
import RPi.GPIO as GPIO


class State(Enum):
    SLEEPING = "SLEEPING"
    AWAKE = "AWAKE"


WAKE_PHRASES = ["hey scrappy", "scrappy"]
ON_PHRASES = ["lights on", "turn on", "light on"]
OFF_PHRASES = ["lights off", "turn off", "light off"]

COMMAND_TIMEOUT_SEC = 5.0

# ── GPIO CONFIG ──────────────────────────────────────────
# BCM GPIO 4 = physical pin 7 = labeled "#4" on Perma-Proto HAT
RELAY_PIN = 4
# Active-LOW relay: IN pin LOW energizes the coil -> lamp ON
RELAY_ACTIVE = GPIO.LOW
RELAY_INACTIVE = GPIO.HIGH


def any_match(text, phrases):
    t = text.lower()
    return any(p in t for p in phrases)


class StateMachine:
    def __init__(self, audio, display, power_tracker=None):
        self.audio = audio
        self.display = display
        self.power = power_tracker
        self.state = State.SLEEPING
        self.lamp_is_on = False
        self._running = False

        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(RELAY_PIN, GPIO.OUT)
        GPIO.output(RELAY_PIN, RELAY_INACTIVE)
        print(f"[fsm] GPIO {RELAY_PIN} initialized, relay OFF")

    def _set_state(self, new_state: State):
        self.state = new_state
        if self.power:
            self.power.set_state(new_state.value)

    def _execute_on(self):
        if self.power:
            self.power.set_state("EXECUTING_ON")
        if self.lamp_is_on:
            print("[fsm] Already ON — error animation")
            self.display.show_already_on_error()
            if self.power:
                self.power.record_command("ON_DUPLICATE")
        else:
            print(f"[fsm] Lamp ON (GPIO {RELAY_PIN} -> LOW)")
            self.lamp_is_on = True
            GPIO.output(RELAY_PIN, RELAY_ACTIVE)
            self.display.show_on_success()
            if self.power:
                self.power.record_command("ON")

    def _execute_off(self):
        if self.power:
            self.power.set_state("EXECUTING_OFF")
        if not self.lamp_is_on:
            print("[fsm] Already OFF — error animation")
            self.display.show_already_off_error()
            if self.power:
                self.power.record_command("OFF_DUPLICATE")
        else:
            print(f"[fsm] Lamp OFF (GPIO {RELAY_PIN} -> HIGH)")
            self.lamp_is_on = False
            GPIO.output(RELAY_PIN, RELAY_INACTIVE)
            self.display.show_off_success()
            if self.power:
                self.power.record_command("OFF")

    def _run_sleeping(self):
        print("\n[fsm] STATE: SLEEPING — waiting for 'hey scrappy'")
        self._set_state(State.SLEEPING)
        self.audio.flush()
        while self._running:
            self.display.show_sleeping()
            while True:
                phrase = self.audio.get_phrase(timeout=0.01)
                if phrase is None:
                    break
                print(f"[fsm] heard: '{phrase}'")
                if any_match(phrase, WAKE_PHRASES):
                    print("[fsm] Wake word detected")
                    self._set_state(State.AWAKE)
                    return

    def _run_awake(self):
        print("[fsm] STATE: AWAKE — listening for command")
        self.display.show_awake()
        self.audio.flush()
        deadline = time.monotonic() + COMMAND_TIMEOUT_SEC
        while self._running and time.monotonic() < deadline:
            phrase = self.audio.get_phrase(timeout=0.2)
            if phrase is None:
                continue
            print(f"[fsm] heard: '{phrase}'")
            if any_match(phrase, ON_PHRASES):
                self._execute_on()
                self._set_state(State.SLEEPING)
                return
            if any_match(phrase, OFF_PHRASES):
                self._execute_off()
                self._set_state(State.SLEEPING)
                return
        print("[fsm] Command window timed out")
        self.display.show_timeout()
        self._set_state(State.SLEEPING)

    def run(self):
        self._running = True
        try:
            while self._running:
                if self.state == State.SLEEPING:
                    self._run_sleeping()
                elif self.state == State.AWAKE:
                    self._run_awake()
        except KeyboardInterrupt:
            print("\n[fsm] Interrupted")
        finally:
            self._running = False
            self.display.clear()
            GPIO.output(RELAY_PIN, RELAY_INACTIVE)
            GPIO.cleanup()
            print("[fsm] GPIO cleaned up, relay OFF.")

    def stop(self):
        self._running = False