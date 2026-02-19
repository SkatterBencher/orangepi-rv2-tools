#!/usr/bin/env python3
import os
import time
import glob
import argparse
import datetime
import csv
import re
from collections import OrderedDict
import threading
import curses
import signal

_prev_cpu_times = None

# === UTILITY FUNCTIONS ===
def read_file(path):
    try:
        with open(path, "r") as f:
            return f.read().strip()
    except Exception:
        return None

# === BASIC CLOCK FREQUENCIES ===
CLK_ORDERED = OrderedDict([
    ("cpu_c0_hi_clk",       "cpu_c0_hi_clk"),
    ("cpu_c0_core_clk",     "cpu_c0_core_clk"),
    ("cpu_c0_tcm_clk",      "cpu_c0_tcm_clk"),
    ("cpu_c0_ace_clk",      "cpu_c0_ace_clk"),
    ("cpu_c1_hi_clk",       "cpu_c1_hi_clk"),
    ("cpu_c1_pclk",         "cpu_c1_pclk"),
    ("cpu_c1_ace_clk",      "cpu_c1_ace_clk"),
    ("ddr",                 "ddr"),
    ("gpu_clk",             "gpu_clk"),
    ("jpg_clk",             "jpg_clk"),
    ("vpu_clk",             "vpu_clk"),
    ("v2d_clk",             "v2d_clk"),
    ("emmc_clk",            "emmc_clk"),
    ("emmc_x_clk",          "emmc_x_clk"),
    ("sdh0_clk",            "sdh0_clk"),
    ("dpu_hclk",            "dpu_hclk"),
    ("dpu_pxclk",           "dpu_pxclk"),
    ("dpu_mclk",            "dpu_mclk"),
    ("dpu_bit_clk",         "dpu_bit_clk"),
    ("sdh_axi_aclk",        "sdh_axi_aclk"),
    ("isp_clk",             "isp_clk"),
    ("hdmi_mclk",           "hdmi_mclk"),
    ("csi_clk",             "csi_clk"),
    ("uart2_clk",           "uart2_clk"),
])

def read_clk_summary():
    try:
        with open("/sys/kernel/debug/clk/clk_summary") as f:
            return f.readlines()
    except Exception:
        return []

def get_clk_frequency_cached(keyword, lines):
    """
    Parse clk_summary, matching actual clock definitions, not consumer entries.
    Clock lines start with whitespace followed by the clock name.
    """
    for line in lines:
        if keyword not in line:
            continue
        parts = line.split()
        if len(parts) < 5:
            continue
        if parts[0] == keyword:
            try:
                freq_hz = int(parts[4])
                if freq_hz == 0:
                    return 0
                return round(freq_hz / 1_000_000, 1)
            except (ValueError, IndexError):
                return None
    
    return None


# === VOLTAGES ===
def get_sorted_regulator_voltages():
    voltages = []
    for reg in glob.glob("/sys/class/regulator/regulator.*"):
        name = read_file(os.path.join(reg, "name"))
        cur_uV = read_file(os.path.join(reg, "microvolts"))
        max_uV = read_file(os.path.join(reg, "max_microvolts"))
        if not name or not cur_uV or not max_uV:
            continue
        try:
            voltages.append(
                (name, int(cur_uV) // 1000, int(max_uV) // 1000)
            )
        except ValueError:
            continue
    return sorted(voltages, key=lambda x: x[0])

# === TEMPERATURES ===
def get_temperatures():
    temps = []
    for hwmon in glob.glob("/sys/class/hwmon/hwmon*"):
        name = read_file(os.path.join(hwmon, "name"))
        temp = read_file(os.path.join(hwmon, "temp1_input"))
        if name and temp:
            try:
                temps.append((name, round(int(temp) / 1000, 1)))
            except ValueError:
                continue
    return sorted(temps, key=lambda x: x[0])

# === CPU LOAD ===
def read_cpu_times():
    with open("/proc/stat") as f:
        for line in f:
            if line.startswith("cpu"):
                parts = line.split()
                yield parts[0], list(map(int, parts[1:]))

def get_cpu_usages():
    global _prev_cpu_times
    curr = dict(read_cpu_times())

    if _prev_cpu_times is None:
        _prev_cpu_times = curr
        return {}

    usage = {}
    for cpu, new in curr.items():
        if cpu == "cpu":
            continue  # skip aggregate
        old = _prev_cpu_times.get(cpu)
        if not old:
            continue

        total_d = sum(new) - sum(old)
        idle_d = (new[3] + new[4]) - (old[3] + old[4])
        if total_d > 0:
            usage[cpu.upper()] = round(100 * (1 - idle_d / total_d), 1)

    _prev_cpu_times = curr
    return usage

# === GOVERNORS ===
def get_governors():
    governors = {}
    paths = {f"CPU{i}": f"/sys/devices/system/cpu/cpu{i}/cpufreq/scaling_governor" for i in range(8)}
    paths["PCIE"] = "/sys/module/pcie_aspm/parameters/policy"

    for label, path in paths.items():
        val = read_file(path)
        if not val:
            continue
        match = re.search(r"\[([^\]]+)\]", val)
        governors[label] = match.group(1) if match else val
    return governors

# === TUI ===
def tui_main(stdscr, args):
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_YELLOW, -1)

    stdscr.nodelay(True)
    curses.curs_set(0)

    def handle_resize(signum, frame):
        stdscr.clear()

    signal.signal(signal.SIGWINCH, handle_resize)

    COLUMN_MAP = {'t': 1, 'f': 0, 'g': 1, 'v': 2, 'l': 1}

    while True:
        stdscr.erase()
        max_y, max_x = stdscr.getmaxyx()
        col_width = max(20, max_x // 3 - 1)
        start_row = 5
        cols = [[], [], []]

        header = "Ky X1 Telemetry (TUI) for Orange RV2 by SkatterBencher (v0.1) - Press 'q' to quit"
        stdscr.addstr(0, 0, header[:max_x - 1], curses.color_pair(1) | curses.A_BOLD)
        stdscr.addstr(2, 0, f"Update interval: {args.i:.1f}s"[:max_x - 1], curses.A_DIM)
        stdscr.addstr(3, 0, f"Logging: {'ENABLED' if args.log else 'DISABLED'}"[:max_x - 1], curses.A_DIM)

        def add_lines(lines, col):
            for line in lines:
                cols[col].append((line, 0) if isinstance(line, str) else line)

        # Frequencies
        if args.f:
            clk_lines = read_clk_summary()
            lines = [("## Frequencies ##", curses.color_pair(1) | curses.A_BOLD)]
            for key, label in CLK_ORDERED.items():
                freq = get_clk_frequency_cached(label, clk_lines)
                if freq is not None:
                    # Check if freq is a string or number
                    if isinstance(freq, str):
                        lines.append(f"{key:<20} {freq}")
                    else:
                        lines.append(f"{key:<20} {freq:.0f} MHz")
            add_lines(lines + [""], COLUMN_MAP['f'])

        # Temperatures
        if args.t:
            lines = [("## Temperatures ##", curses.color_pair(1) | curses.A_BOLD)]
            for name, temp in get_temperatures():
                lines.append(f"{name:<20} {temp:.1f} °C")
            add_lines(lines + [""], COLUMN_MAP['t'])

        # Governors
        if args.g:
            lines = [("## Governors ##", curses.color_pair(1) | curses.A_BOLD)]
            for k, v in get_governors().items():
                lines.append(f"{k:<20} {v}")
            add_lines(lines + [""], COLUMN_MAP['g'])

        # Voltages
        if args.v:
            lines = [("## Voltages ##", curses.color_pair(1) | curses.A_BOLD)]
            for name, cur, maxv in get_sorted_regulator_voltages():
                lines.append(f"{name:<10} {cur} mV (Max {maxv})")
            add_lines(lines + [""], COLUMN_MAP['v'])

        # Loads
        if args.l:
            lines = [("## Loads ##", curses.color_pair(1) | curses.A_BOLD)]
            for k, v in get_cpu_usages().items():
                lines.append(f"{k:<20} {v:.1f} %")
            add_lines(lines + [""], COLUMN_MAP['l'])

        # Draw columns
        for col_idx, col in enumerate(cols):
            x = col_idx * (col_width + 1)
            for i, (text, attr) in enumerate(col):
                y = start_row + i
                if y < max_y:
                    stdscr.addstr(y, x, text[:col_width], attr)

        stdscr.refresh()
        if stdscr.getch() == ord('q'):
            break
        curses.napms(int(args.i * 1000))

# === LOGGER ===
def start_logger(args, stop_event):
    now = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    log_filename = f"telemetry-{now}.csv"
    with open(log_filename, mode="w", newline="") as log_file:
        csv_writer = csv.writer(log_file)
        wrote_header = False

        while not stop_event.is_set():
            row = [datetime.datetime.now().isoformat()]
            headers = ["Timestamp"]

            # Frequencies
            if args.f:
                clk_lines = read_clk_summary()
                for key, label in CLK_ORDERED.items():
                    freq = get_clk_frequency_cached(label, clk_lines)
                    if freq is not None:
                        if isinstance(freq, str):
                            row.append(freq)
                        else:
                            row.append(freq)
                        headers.append(key + " (MHz)")

            # Voltages
            if args.v:
                for name, cur, maxv in get_sorted_regulator_voltages():
                    row.extend([cur, maxv])
                    headers.extend([f"{name}_cur (mV)", f"{name}_max (mV)"])

            # Temperatures
            if args.t:
                for name, temp in get_temperatures():
                    row.append(temp)
                    headers.append(name + " (°C)")

            # Governors
            if args.g:
                for k, v in get_governors().items():
                    row.append(v)
                    headers.append(k + " Governor")

            # CPU Usage
            if args.l:
                for k, v in get_cpu_usages().items():
                    row.append(v)
                    headers.append(k + " Usage (%)")

            if not wrote_header:
                csv_writer.writerow(headers)
                wrote_header = True
            csv_writer.writerow(row)
            time.sleep(args.i)

# === MAIN ===
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", action="store_true", help="Show frequencies")
    parser.add_argument("-v", action="store_true", help="Show voltages")
    parser.add_argument("-l", action="store_true", help="Show loads")
    parser.add_argument("-t", action="store_true", help="Show temperatures")
    parser.add_argument("-g", action="store_true", help="Show governors")
    parser.add_argument("-log", action="store_true", help="Log to CSV")
    parser.add_argument("-i", type=float, default=2.0, help="Refresh interval in seconds")
    parser.add_argument("-tui", action="store_true", help="Run with TUI interface")
    parser.add_argument("-no-tui", action="store_true", help="Disable TUI even if no flags are set")
    args = parser.parse_args()

    # Default behavior: enable TUI if no explicit flags and not disabled
    if not any([args.f, args.v, args.l, args.t, args.g, args.tui]) and not args.no_tui:
        args.tui = True

    # Enable all metrics if TUI is used
    if args.tui:
        args.f = args.v = args.l = args.t = args.g = True

    # Start logger thread if needed
    stop_event = threading.Event()
    log_thread = None
    if args.log:
        log_thread = threading.Thread(target=start_logger, args=(args, stop_event), daemon=True)
        log_thread.start()

    # Run TUI if enabled
    try:
        if args.tui:
            curses.wrapper(tui_main, args)
    except KeyboardInterrupt:
        pass
    finally:
        stop_event.set()
        if log_thread:
            log_thread.join()

if __name__ == "__main__":
    main()
