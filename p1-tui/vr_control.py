#!/usr/bin/env python3
"""
SkatterBencher SBC VR Control TUI v4
SPM8821-only version, no I2C explorer
"""

import curses
import platform
from spm8821 import SPM8821Driver

def init_colors():
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_YELLOW)  # Header: black on yellow
    curses.init_pair(2, curses.COLOR_WHITE, -1)                   # Default text
    curses.init_pair(3, curses.COLOR_CYAN, -1)                    # Help
    curses.init_pair(4, curses.COLOR_RED, -1)                     # Errors
    curses.init_pair(5, curses.COLOR_GREEN, -1)                   # Success
    curses.init_pair(6, curses.COLOR_YELLOW, -1)                  # Highlights (selection)

class SkatterBencherTUI:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.selected_idx = 0
        self.edit_mode = False
        self.edit_value = ""
        self.status_msg = ""

        # VR state
        self.current_vr = SPM8821Driver()
        if not self.current_vr.detect():
            raise RuntimeError("SPM8821 VR not detected")
        self.current_vr.open()
        self.regulators = self.current_vr.get_regulator_list()
        self.voltages = {}
        self.constraints = {}
        self.num_users = {}
        self.refresh_vr_data()

        init_colors()
        self.stdscr.keypad(True)
        curses.curs_set(0)
        y=0

    # -------------------
    # Helper Functions
    # -------------------
    def refresh_vr_data(self):
        for idx, name, _ in self.regulators:
            try:
                self.voltages[name] = self.current_vr.get_voltage(name)
                self.constraints[name] = self.current_vr.get_voltage_constraints(name)
                self.num_users[name] = self.current_vr.get_num_users(name)
            except:
                self.voltages[name] = None
                self.constraints[name] = (0, 5000000)
                self.num_users[name] = 0

    def draw_header(self):
        h, w = self.stdscr.getmaxyx()
        header_text = "SKATTERBENCHER ORANGEPI RV2 SPM8821 VR Control TUI"
        self.stdscr.attron(curses.color_pair(1) | curses.A_BOLD)
        self.stdscr.addstr(0, 0, header_text.center(w))
        self.stdscr.attroff(curses.color_pair(1) | curses.A_BOLD)

    def draw_board_info(self):
        """Show board name and kernel info above the VR name"""
        board = platform.node()
        kernel = platform.release()
        self.stdscr.addstr(2, 2, f"Board: {board} | Kernel: {kernel}", curses.color_pair(2))

    def draw_vr_control(self):
        y = 4
        info = self.current_vr.get_info()
        self.stdscr.addstr(y, 2, f"VR: {info['driver_name']} (Bus {self.current_vr.I2C_BUS}, Addr 0x{self.current_vr.I2C_ADDR:02X})", curses.A_BOLD)
        y += 2

        # Table header
        header_fmt = "{:<3} {:<20} {:>10} {:>12} {:>6}"
        self.stdscr.addstr(y, 2, header_fmt.format("ID", "Name", "Voltage(mV)", "Range", "Users"), curses.A_BOLD)
        y += 1

        for idx, name, _ in self.regulators:
            vol = self.voltages.get(name)
            min_mv, max_mv = self.constraints.get(name, (0, 5000000))
            users = self.num_users.get(name, 0)

            # Default attribute
            attr = curses.color_pair(2)
            if vol is None or vol < min_mv or vol > max_mv:
                attr = curses.color_pair(4) | curses.A_BOLD  # Red for out-of-range

            range_str = f"{min_mv//1000}-{max_mv//1000}"
            vol_str = "ERR" if vol is None else f"{vol/1000:>7.1f}"
            row = header_fmt.format(idx, name[:20], vol_str, range_str, users)

            # Highlight selected line fully
            if idx == self.selected_idx and not self.edit_mode:
                self.stdscr.attron(curses.color_pair(6) | curses.A_REVERSE)
                self.stdscr.addstr(y, 2, row.ljust(curses.COLS - 4))  # full line highlight
                self.stdscr.attroff(curses.color_pair(6) | curses.A_REVERSE)
            else:
                self.stdscr.addstr(y, 2, row, attr)
            y += 1

        # Edit mode
        if self.edit_mode:
            _, name, _ = self.regulators[self.selected_idx]
            min_mv, max_mv = self.constraints.get(name, (0, 5000000))
            self.stdscr.attron(curses.color_pair(2) | curses.A_REVERSE)
            self.stdscr.addstr(y+1, 2, f" Set {name} voltage [{min_mv//1000}-{max_mv//1000} mV]: {self.edit_value}_ ")
            self.stdscr.attroff(curses.color_pair(2) | curses.A_REVERSE)


    def draw_footer(self):
        h, w = self.stdscr.getmaxyx()
        help_text = "↑↓ Select | Enter Edit | Q Quit"
        self.stdscr.addstr(h-2, 2, help_text, curses.color_pair(3))
        # Status message
        status_attr = curses.color_pair(5) if "set to" in self.status_msg else curses.color_pair(4)
        self.stdscr.addstr(h-1, 0, f" {self.status_msg}"[:w-1], status_attr)

    # -------------------
    # Input Handling
    # -------------------
    def handle_input(self, key):
        if self.edit_mode:
            if key in (curses.KEY_ENTER, 10, 13):
                try:
                    val = int(float(self.edit_value) * 1000)
                    _, name, _ = self.regulators[self.selected_idx]
                    actual = self.current_vr.set_voltage(name, val)
                    self.voltages[name] = actual
                    self.status_msg = f"{name} set to {actual/1000:.1f} mV"
                except:
                    self.status_msg = "Invalid voltage"
                self.edit_mode = False
                self.edit_value = ""
            elif key == 27:  # ESC
                self.edit_mode = False
                self.edit_value = ""
            elif key in (curses.KEY_BACKSPACE, 127, 8):
                self.edit_value = self.edit_value[:-1]
            elif 48 <= key <= 57 or key == 46:  # 0-9 and dot
                self.edit_value += chr(key)
        else:
            if key == curses.KEY_UP:
                self.selected_idx = max(0, self.selected_idx-1)
            elif key == curses.KEY_DOWN:
                self.selected_idx = min(len(self.regulators)-1, self.selected_idx+1)
            elif key in (curses.KEY_ENTER, 10, 13):
                self.edit_mode = True
                self.edit_value = ""

    # -------------------
    # Main Loop
    # -------------------
    def run(self):
        while True:
            self.stdscr.clear()
            self.draw_header()
            self.draw_board_info()
            self.draw_vr_control()
            self.draw_footer()
            self.stdscr.refresh()

            key = self.stdscr.getch()
            if key in (ord('q'), ord('Q')):
                break
            self.handle_input(key)

def main(stdscr):
    tui = SkatterBencherTUI(stdscr)
    tui.run()

if __name__ == "__main__":
    curses.wrapper(main)
