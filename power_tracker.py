"""Per-state power tracker.

Samples CPU/power in a background thread, attributes time and energy
to whichever state the system is currently in.
"""

import csv
import subprocess
import threading
import time
from collections import defaultdict

import psutil

# Same power model as power_monitor.py
PI4_IDLE_W = 2.7
PI4_PER_PCT_CPU_W = 0.028
USB_PERIPHERAL_W = 0.3
HDMI_W = 0.4
SENSE_HAT_AVG_W = 0.2

SAMPLE_INTERVAL_SEC = 0.5


def _get_cpu_temp_c():
    try:
        out = subprocess.check_output(
            ["vcgencmd", "measure_temp"], text=True
        ).strip()
        return float(out.split("=")[1].split("'")[0])
    except Exception:
        return float("nan")


def estimate_power_w(cpu_pct: float) -> float:
    return (
        PI4_IDLE_W
        + PI4_PER_PCT_CPU_W * cpu_pct
        + USB_PERIPHERAL_W
        + HDMI_W
        + SENSE_HAT_AVG_W
    )


class PowerTracker:
    """Background sampler that attributes power and time per labeled state."""

    def __init__(self, csv_path: str = "power_log.csv"):
        self.csv_path = csv_path
        self.current_state = "INITIALIZING"
        self._stop = threading.Event()
        self._lock = threading.Lock()

        self.time_in_state = defaultdict(float)
        self.energy_in_state = defaultdict(float)   # joules
        self.command_count = defaultdict(int)

        self._start_time = None
        self._csv_file = None
        self._csv_writer = None

    def set_state(self, state: str):
        """Called by the state machine on every transition."""
        with self._lock:
            ts = time.monotonic() - self._start_time if self._start_time else 0
            print(f"[power] {ts:6.2f}s  state -> {state}")
            self.current_state = state
            if self._csv_writer is not None:
                self._csv_writer.writerow([f"{ts:.2f}", "STATE_CHANGE", state, "", "", ""])
                self._csv_file.flush()

    def record_command(self, command: str):
        """Called when a voice command is executed."""
        with self._lock:
            self.command_count[command] += 1
            ts = time.monotonic() - self._start_time if self._start_time else 0
            print(f"[power] {ts:6.2f}s  command executed: {command}")
            if self._csv_writer is not None:
                self._csv_writer.writerow([f"{ts:.2f}", "COMMAND", command, "", "", ""])
                self._csv_file.flush()

    def _sample_loop(self):
        last_t = time.monotonic()
        while not self._stop.is_set():
            cpu_pct = psutil.cpu_percent(interval=SAMPLE_INTERVAL_SEC)
            now = time.monotonic()
            dt = now - last_t
            last_t = now

            power_w = estimate_power_w(cpu_pct)
            energy_j = power_w * dt
            cpu_temp = _get_cpu_temp_c()

            with self._lock:
                state = self.current_state
                self.time_in_state[state] += dt
                self.energy_in_state[state] += energy_j

                if self._csv_writer is not None:
                    elapsed = now - self._start_time
                    self._csv_writer.writerow([
                        f"{elapsed:.2f}",
                        "SAMPLE",
                        state,
                        f"{cpu_pct:.1f}",
                        f"{cpu_temp:.1f}",
                        f"{power_w:.2f}",
                    ])

    def start(self):
        self._start_time = time.monotonic()
        self._csv_file = open(self.csv_path, "w", newline="")
        self._csv_writer = csv.writer(self._csv_file)
        self._csv_writer.writerow([
            "elapsed_s", "event_type", "state_or_cmd",
            "cpu_pct", "cpu_temp_c", "power_w"
        ])
        self._stop.clear()
        self._thread = threading.Thread(target=self._sample_loop, daemon=True)
        self._thread.start()
        print(f"[power] tracker started (logging to {self.csv_path})")

    def stop_and_report(self):
        self._stop.set()
        self._thread.join(timeout=2.0)
        if self._csv_file:
            self._csv_file.close()

        total_time = sum(self.time_in_state.values())
        total_energy_j = sum(self.energy_in_state.values())
        total_energy_wh = total_energy_j / 3600

        print("\n" + "=" * 64)
        print("  POWER PROFILE SUMMARY")
        print("=" * 64)
        print(f"  Total runtime:         {total_time:.1f} s")
        print(f"  Total energy:          {total_energy_j:.1f} J  ({total_energy_wh:.4f} Wh)")
        if total_time > 0:
            print(f"  Avg power overall:     {total_energy_j / total_time:.2f} W")
        print()
        print(f"  {'State':<25} {'Time (s)':>10} {'Energy (J)':>12} {'Avg W':>8}")
        print(f"  {'-'*25} {'-'*10} {'-'*12} {'-'*8}")
        for state in sorted(self.time_in_state.keys()):
            t = self.time_in_state[state]
            e = self.energy_in_state[state]
            avg_w = e / t if t > 0 else 0
            print(f"  {state:<25} {t:>10.2f} {e:>12.2f} {avg_w:>8.2f}")
        print()
        print(f"  Commands executed:")
        for cmd, count in sorted(self.command_count.items()):
            print(f"    {cmd}: {count}")
        if total_time > 0 and self.command_count:
            total_cmds = sum(self.command_count.values())
            j_per_cmd = total_energy_j / total_cmds if total_cmds else 0
            print(f"\n  Energy per command (avg): {j_per_cmd:.2f} J")
        if total_time > 60:
            kwh_per_year = (total_energy_wh / total_time) * 3600 * 24 * 365 / 1000
            cost_per_year = kwh_per_year * 0.14
            print(f"  Projected if always on:")
            print(f"    Annual energy: {kwh_per_year:.1f} kWh/year")
            print(f"    Annual cost:   ${cost_per_year:.2f}/year (at $0.14/kWh)")
        print("=" * 64)
...
