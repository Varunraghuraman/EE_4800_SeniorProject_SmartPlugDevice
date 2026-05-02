"""Sense HAT display controller for state visualization."""

from sense_hat import SenseHat
import time

# Colors
DIM_WHITE = (50, 50, 50)
BLUE = (0, 0, 255)
GREEN = (0, 255, 0)
RED = (255, 0, 0)
OFF = (0, 0, 0)


class Display:
    def __init__(self):
        self.sense = SenseHat()
        self.sense.low_light = True
        self.sense.clear()

    def clear(self):
        self.sense.clear()

    def show_sleeping(self):
        """Scroll 'zzz...zzz...' in dim white — sleep indicator."""
        self.sense.show_message(
            "zzz...zzz...",
            text_colour=DIM_WHITE,
            back_colour=OFF,
            scroll_speed=0.08,
        )

    def show_awake(self):
        """Solid blue fill — listening for command."""
        self.sense.clear(BLUE)

    def show_on_success(self):
        """Flash 'ON' 3 times in green."""
        for _ in range(3):
            self.sense.show_letter("O", text_colour=GREEN, back_colour=OFF)
            time.sleep(0.25)
            self.sense.show_letter("N", text_colour=GREEN, back_colour=OFF)
            time.sleep(0.25)
            self.sense.clear()
            time.sleep(0.15)

    def show_off_success(self):
        """Scroll 'OFF' 3 times in green."""
        for _ in range(3):
            self.sense.show_message(
                "OFF",
                text_colour=GREEN,
                back_colour=OFF,
                scroll_speed=0.05,
            )
            time.sleep(0.1)

    def show_already_on_error(self):
        """Flash 'ON' 3 times in red — already on."""
        for _ in range(3):
            self.sense.show_letter("O", text_colour=RED, back_colour=OFF)
            time.sleep(0.25)
            self.sense.show_letter("N", text_colour=RED, back_colour=OFF)
            time.sleep(0.25)
            self.sense.clear()
            time.sleep(0.15)

    def show_already_off_error(self):
        """Scroll 'OFF' 3 times in red — already off."""
        for _ in range(3):
            self.sense.show_message(
                "OFF",
                text_colour=RED,
                back_colour=OFF,
                scroll_speed=0.05,
            )
            time.sleep(0.1)

    def show_timeout(self):
        """Brief red X — no command heard."""
        self.sense.show_letter("X", text_colour=RED, back_colour=OFF)
        time.sleep(0.8)
        self.sense.clear()