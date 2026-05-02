"""
Power profile monitor for the edge voice smart plug.

Logs CPU utilization, frequency, temperature, and estimated power draw
to a CSV file. Run this in a separate terminal alongside app.py.

Usage:
    python3 power_monitor.py [duration_seconds] [output_csv]

Example:
    python3 power_monitor.py 120 power_log.csv
"""

import csv
import sys
import time
import subprocess
import psutil

# Pi 4 power model — empirically derived from published measurements.
# Idle baseline (board, RAM, ethernet down, wifi up) ~ 2.7 W
# Each 25% CPU load adds ~ 0.7 W on average across the four cores
# USB peripherals (mic) add ~ 0.3 W
# HDMI active adds ~ 0.4 W
# Sense HAT idle adds ~ 0.1 W; full LED matrix adds ~ 0.3 W
PI4_IDLE_W = 2.7
PI4_PER_PCT_CPU_W = 0.028   # watts per percent CPU utilization (averaged)
USB_PERIPHERAL_W = 0.3      # USB mic
HDMI_W = 0.4                # if monitor connected
SENSE_HAT_AVG_W = 0.2       # average across animations


def get_cpu_temp_c():
    """Read CPU temperature in Celsius via vcgencmd."""
    try:
        out = subprocess.check_output(
            ["vcgencmd", "measure_temp"], text=True
        ).strip()
        return float(out.split("=")[1].split("'")[0])
    except Exception:
        return float("nan")


def get_cpu_freq_mhz():
    """Read current CPU clock frequency in MHz."""
    try:
        out = subprocess.check_output(
            ["vcgencmd", "measure_clock", "arm"], text=True
        ).strip()
        hz = int(out.split("=")[1])
        return hz / 1_000_000
    except Exception:
        return float("nan")


def estimate_power_w(cpu_pct):
    """Empirical model: convert CPU load to estimated wattage."""
    return (
        PI4_IDLE_W
        + PI4_PER_PCT_CPU_W * cpu_pct
        + USB_PERIPHERAL_W
        + HDMI_W
        + SENSE_HAT_AVG_W
    )


def main():
    duration = int(sys.argv[1]) if len(sys.argv) > 1 else 120
    output = sys.argv[2] if len(sys.argv) > 2 else "power_log.csv"

    print(f"[power] Logging for {duration}s to {output}")
    print(f"[power] Sample rate: 2 Hz (every 0.5 s)")
    print(f"[power] Press Ctrl+C to stop early.\n")

    start = time.monotonic()
    samples = 0
    cpu_total = 0.0
    power_total = 0.0
    power_peak = 0.0

    with open(output, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "elapsed_s",
            "cpu_pct",
            "cpu_freq_mhz",
            "cpu_temp_c",
            "mem_used_mb",
            "estimated_power_w",
        ])

        try:
            while time.monotonic() - start < duration:
                cpu_pct = psutil.cpu_percent(interval=0.5)
                cpu_freq = get_cpu_freq_mhz()
                cpu_temp = get_cpu_temp_c()
                mem_mb = psutil.virtual_memory().used / (1024 * 1024)
                power_w = estimate_power_w(cpu_pct)

                elapsed = time.monotonic() - start
                writer.writerow([
                    f"{elapsed:.2f}",
                    f"{cpu_pct:.1f}",
                    f"{cpu_freq:.0f}",
                    f"{cpu_temp:.1f}",
                    f"{mem_mb:.0f}",
                    f"{power_w:.2f}",
                ])
                f.flush()

                samples += 1
                cpu_total += cpu_pct
                power_total += power_w
                power_peak = max(power_peak, power_w)

                print(
                    f"  t={elapsed:5.1f}s  "
                    f"CPU={cpu_pct:5.1f}%  "
                    f"freq={cpu_freq:4.0f}MHz  "
                    f"temp={cpu_temp:4.1f}C  "
                    f"mem={mem_mb:5.0f}MB  "
                    f"power={power_w:.2f}W"
                )
        except KeyboardInterrupt:
            print("\n[power] Stopped by user.")

    if samples > 0:
        print("\n" + "=" * 60)
        print(f"  Samples collected: {samples}")
        print(f"  Avg CPU:           {cpu_total / samples:.1f} %")
        print(f"  Avg power:         {power_total / samples:.2f} W")
        print(f"  Peak power:        {power_peak:.2f} W")
        print(f"  CSV saved to:      {output}")
        print("=" * 60)


if __name__ == "__main__":
    main()
