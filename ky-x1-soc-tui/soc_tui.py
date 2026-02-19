#!/usr/bin/env python3
"""
SpaceMit K1 Register Browser TUI 
"""
import os
import mmap
import struct
import curses
import logging
import sys
import time
import traceback

# Setup logging
logging.basicConfig(
    filename='/tmp/k1_tui.log',
    level=logging.ERROR,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Constants
MMAP_SIZE = 0x1000
MIN_TERMINAL_WIDTH = 60
MIN_TERMINAL_HEIGHT = 20
ERROR_SENTINEL = 0xDEADBEEF
MAX_32BIT_VALUE = 0xFFFFFFFF

# Color pairs
COLOR_TITLE = 1
COLOR_TAB_NORMAL = 2
COLOR_TAB_SELECTED = 3
COLOR_ERROR = 4
COLOR_LABEL = 5
COLOR_VALUE = 6

# Try to import frequency calculator
try:
    from spacemit_k1_freq_calc import FrequencyCalculator
    FREQ_CALC_AVAILABLE = True
except ImportError as e:
    FREQ_CALC_AVAILABLE = False
    logging.warning(f"Frequency calculator not available: {e}")


class AppState:
    """Application state container."""
    def __init__(self):
        self.last_message = ""
        self.write_count = 0
        self.current_tab = 0
        self.view_mode = "registers"
        self.field_selected = 0
        self.option_selected = 0
        self.need_full_redraw = True


def parse_hex_input(input_str: str, max_val: int | None = None) -> int:
    """Parse and validate hex input."""
    input_str = input_str.strip()
    if not input_str:
        raise ValueError("Empty input")
    
    if not all(c in '0123456789ABCDEFabcdef' for c in input_str):
        raise ValueError("Invalid hex characters")
    
    val = int(input_str, 16)
    
    if max_val is not None and val > max_val:
        raise ValueError(f"Value exceeds maximum 0x{max_val:X}")
    
    return val


def parse_field_options(description: str) -> list[tuple[int, str]]:
    """Extract value-description pairs from field description."""
    options = []
    if not description or ':' not in description:
        return options
    
    for line in description.split('\n'):
        if ':' not in line:
            continue
        
        try:
            val_str, desc = line.split(':', 1)
            val_str = val_str.strip()
            desc = desc.strip()
            
            if all(c in '01' for c in val_str):
                val = int(val_str, 2)
            else:
                val_str = val_str.lstrip('b')
                if val_str:
                    val = int(val_str)
                else:
                    continue
            
            if desc:
                options.append((val, desc))
        except (ValueError, IndexError):
            continue
    
    return options


def read_register(base_addr: int, offset: int) -> int:
    """Read a 32-bit value from a register."""
    if offset + 4 > MMAP_SIZE:
        raise ValueError(f"Offset exceeds MMAP_SIZE")
    
    fd = None
    try:
        fd = os.open("/dev/mem", os.O_RDONLY | os.O_SYNC)
        page_size = mmap.PAGESIZE
        page_base = base_addr & ~(page_size - 1)
        page_offset = (base_addr - page_base) + offset
        
        if page_offset + 4 > MMAP_SIZE:
            raise ValueError(f"Page offset exceeds MMAP_SIZE")
        
        mem = mmap.mmap(fd, MMAP_SIZE, mmap.MAP_SHARED,
                        mmap.PROT_READ,
                        offset=page_base)
        try:
            mem.seek(page_offset)
            val_bytes = mem.read(4)
            if len(val_bytes) < 4:
                raise IOError("Failed to read 4 bytes")
            return struct.unpack("<I", val_bytes)[0]
        finally:
            mem.close()
    except Exception as e:
        logging.error(f"Read failed at 0x{base_addr:X}+0x{offset:X}: {e}")
        raise
    finally:
        if fd is not None:
            os.close(fd)


def write_register(base_addr: int, offset: int, value: int) -> None:
    """Write a 32-bit value to a register."""
    if offset + 4 > MMAP_SIZE:
        raise ValueError(f"Offset exceeds MMAP_SIZE")
    
    if not (0 <= value <= MAX_32BIT_VALUE):
        raise ValueError(f"Value out of 32-bit range")
    
    fd = None
    try:
        fd = os.open("/dev/mem", os.O_RDWR | os.O_SYNC)
        page_size = mmap.PAGESIZE
        page_base = base_addr & ~(page_size - 1)
        page_offset = (base_addr - page_base) + offset
        
        if page_offset + 4 > MMAP_SIZE:
            raise ValueError(f"Page offset exceeds MMAP_SIZE")
        
        mem = mmap.mmap(fd, MMAP_SIZE, mmap.MAP_SHARED,
                        mmap.PROT_READ | mmap.PROT_WRITE,
                        offset=page_base)
        try:
            mem.seek(page_offset)
            mem.write(struct.pack("<I", value))
        finally:
            mem.close()
        
        logging.warning(f"Wrote 0x{value:08X} to 0x{base_addr:X}+0x{offset:X}")
    except Exception as e:
        logging.error(f"Write failed: {e}")
        raise
    finally:
        if fd is not None:
            os.close(fd)


def safe_read_register(base_addr: int, offset: int) -> int:
    """Safely read a register, returning error sentinel on failure."""
    try:
        return read_register(base_addr, offset)
    except Exception:
        return ERROR_SENTINEL


def get_bits(value: int, lsb: int, msb: int) -> int:
    """Extract bits from value."""
    mask = (1 << (msb - lsb + 1)) - 1
    return (value >> lsb) & mask


def set_bits(orig: int, value: int, lsb: int, msb: int) -> int:
    """Set bits in value."""
    mask = (1 << (msb - lsb + 1)) - 1
    orig &= ~(mask << lsb)
    orig |= (value & mask) << lsb
    return orig


class RegisterTab:
    """Represents a tab of registers."""
    def __init__(self, name: str):
        self.name = name
        self.registers = []
        self.selected = 0
        self.scroll_offset = 0
    
    def add_register(self, name: str, base: int, offset: int, fields: list | None = None) -> None:
        """Add a register to the tab."""
        self.registers.append({
            'name': name,
            'base': base,
            'offset': offset,
            'fields': fields or [],
            'field_objects': []
        })
    
    def get_selected_register(self) -> dict | None:
        """Get currently selected register."""
        if self.selected < len(self.registers):
            return self.registers[self.selected]
        return None


class SummaryTab:
    """Special tab that displays frequency summary."""
    def __init__(self):
        self.name = "Summary"
        self.data = {}
        self.selected = 0
        self.scroll_offset = 0
        self.last_refresh = 0
        self.last_drawn_data = None
        self._refresh_data()
    
    def _refresh_data(self) -> None:
        """Refresh frequency data from registers."""
        try:
            if FREQ_CALC_AVAILABLE:
                calc = FrequencyCalculator(safe_read_register)
                self.data = calc.get_summary()
            else:
                self.data = {"error": "Frequency calculator module not found..."}
        except Exception as e:
            self.data = {"error": f"Failed to calculate frequencies: {e}"}
            logging.error(f"Frequency calculation error: {e}\n{traceback.format_exc()}")
        
        self.last_refresh = time.time()
    
    def refresh(self) -> None:
        """Manually refresh data."""
        self._refresh_data()
    
    def should_refresh(self, interval: float = 0.5) -> bool:
        """Check if enough time has passed to refresh."""
        return time.time() - self.last_refresh >= interval
    
    def data_changed(self) -> bool:
        """Check if data has changed since last draw."""
        if self.last_drawn_data is None:
            return True
        return self.data != self.last_drawn_data
    
    def mark_drawn(self) -> None:
        """Mark current data as drawn."""
        self.last_drawn_data = dict(self.data)


def draw_header(stdscr, current_tab: int, tabs: list) -> None:
    """Draw header and tab bar."""
    stdscr.attron(curses.color_pair(COLOR_TITLE) | curses.A_BOLD)
    stdscr.addstr(0, 0, "SpaceMit K1 Register Browser")
    stdscr.attroff(curses.color_pair(COLOR_TITLE) | curses.A_BOLD)
    
    # Tab bar
    stdscr.move(1, 0)
    stdscr.clrtoeol()
    
    x = 0
    for i, tab in enumerate(tabs):
        tab_str = f" {tab.name} "
        if i == current_tab:
            stdscr.attron(curses.color_pair(COLOR_TAB_SELECTED) | curses.A_BOLD)
            stdscr.addstr(1, x, tab_str)
            stdscr.attroff(curses.color_pair(COLOR_TAB_SELECTED) | curses.A_BOLD)
        else:
            stdscr.attron(curses.color_pair(COLOR_TAB_NORMAL))
            stdscr.addstr(1, x, tab_str)
            stdscr.attroff(curses.color_pair(COLOR_TAB_NORMAL))
        x += len(tab_str)
    
    stdscr.hline(2, 0, curses.ACS_HLINE, curses.COLS)


def draw_summary_data_only(stdscr, summary_tab: SummaryTab) -> None:
    """Draw only the summary data, not the header."""
    start_row = 3
    visible_rows = curses.LINES - start_row - 2
    row = start_row
    
    if not summary_tab.data:
        stdscr.addstr(row, 2, "No frequency data available")
        return
    
    if "error" in summary_tab.data and len(summary_tab.data) == 1:
        stdscr.attron(curses.color_pair(COLOR_ERROR))
        error_msg = summary_tab.data['error']
        for line in error_msg.split('\n'):
            if row >= curses.LINES - 2:
                break
            stdscr.addstr(row, 2, line[:curses.COLS-4])
            row += 1
        stdscr.attroff(curses.color_pair(COLOR_ERROR))
        return
    
    def format_section(title: str, data: dict, row: int) -> int:
        """Format and draw a section of frequency data."""
        if row >= curses.LINES - 2:
            return row
        
        stdscr.attron(curses.A_BOLD | curses.color_pair(COLOR_LABEL))
        stdscr.addstr(row, 2, title)
        stdscr.attroff(curses.A_BOLD | curses.color_pair(COLOR_LABEL))
        row += 1
        
        if isinstance(data, dict):
            for key, value in data.items():
                if row >= curses.LINES - 2:
                    break
                
                if key.startswith("_") or key == "note" or key == "error":
                    continue
                
                display = f"  {key}: {value}"
                
                if len(display) > curses.COLS - 4:
                    display = display[:curses.COLS-7] + "..."
                
                stdscr.addstr(row, 0, display)
                row += 1
        
        row += 1
        return row
    
    if "fixed_clocks" in summary_tab.data:
        row = format_section("FIXED CLOCKS", summary_tab.data["fixed_clocks"], row)
    
    if "cpu_c0" in summary_tab.data and "error" not in summary_tab.data["cpu_c0"]:
        row = format_section("CPU CLUSTER 0", summary_tab.data["cpu_c0"], row)
    
    if "cpu_c1" in summary_tab.data and "error" not in summary_tab.data["cpu_c1"]:
        row = format_section("CPU CLUSTER 1", summary_tab.data["cpu_c1"], row)
    
    if "aclk" in summary_tab.data and "error" not in summary_tab.data["aclk"]:
        row = format_section("ACLK", summary_tab.data["aclk"], row)
    
    if "gpu" in summary_tab.data and "error" not in summary_tab.data["gpu"]:
        row = format_section("GPU", summary_tab.data["gpu"], row)
    
    if "vpu" in summary_tab.data and "error" not in summary_tab.data["vpu"]:
        row = format_section("VPU", summary_tab.data["vpu"], row)
    
    if "jpg" in summary_tab.data and "error" not in summary_tab.data["jpg"]:
        row = format_section("JPEG", summary_tab.data["jpg"], row)
    
    if "dfc" in summary_tab.data and "error" not in summary_tab.data["dfc"]:
        row = format_section("DYNAMIC FREQ CONTROL", summary_tab.data["dfc"], row)


def draw_registers_view(stdscr, tab: RegisterTab) -> None:
    """Draw registers list."""
    FIELD_COL = 25
    start_row = 3
    visible_rows = curses.LINES - start_row - 2
    
    if tab.scroll_offset < 0:
        tab.scroll_offset = 0
    if tab.selected < tab.scroll_offset:
        tab.scroll_offset = tab.selected
    elif tab.selected >= tab.scroll_offset + visible_rows:
        tab.scroll_offset = tab.selected - visible_rows + 1
    
    for visible_idx, reg_idx in enumerate(range(tab.scroll_offset, 
                                                  min(tab.scroll_offset + visible_rows, 
                                                      len(tab.registers)))):
        row = start_row + visible_idx
        if row >= curses.LINES - 1:
            break
        
        reg = tab.registers[reg_idx]
        val = safe_read_register(reg['base'], reg['offset'])
        
        display = f"{reg['name']:<{FIELD_COL}}: 0x{val:08X}"
        
        if reg_idx == tab.selected:
            stdscr.attron(curses.A_REVERSE | curses.A_BOLD)
            stdscr.addstr(row, 0, display[:curses.COLS-1])
            stdscr.attroff(curses.A_REVERSE | curses.A_BOLD)
        else:
            stdscr.addstr(row, 0, display[:curses.COLS-1])
    
    if tab.get_selected_register():
        reg = tab.get_selected_register()
        val = safe_read_register(reg['base'], reg['offset'])
        
        detail_row = curses.LINES - 4
        if reg['fields']:
            info_text = "Fields: "
            for field_name, lsb, msb in reg['fields']:
                field_val = get_bits(val, lsb, msb)
                info_text += f"{field_name}[{msb}:{lsb}]=0x{field_val:X} "
            
            if len(info_text) > curses.COLS - 2:
                info_text = info_text[:curses.COLS-5] + "..."
            
            stdscr.addstr(detail_row, 0, info_text)


def draw_fields_view(stdscr, tab: RegisterTab, field_selected: int) -> None:
    """Draw fields for selected register."""
    reg = tab.get_selected_register()
    if not reg or not reg['fields']:
        return
    
    val = safe_read_register(reg['base'], reg['offset'])
    
    start_row = 3
    
    stdscr.attron(curses.A_BOLD)
    stdscr.addstr(start_row, 0, f"Register: {reg['name']} = 0x{val:08X}")
    stdscr.attroff(curses.A_BOLD)
    
    field_start = start_row + 2
    for visible_idx, (field_idx, (field_name, lsb, msb)) in enumerate(enumerate(reg['fields'])):
        row = field_start + visible_idx
        if row >= curses.LINES - 1:
            break
        
        field_val = get_bits(val, lsb, msb)
        display = f"{field_name}[{msb}:{lsb}] = 0x{field_val:X}"
        
        if field_idx == field_selected:
            stdscr.attron(curses.A_REVERSE | curses.A_BOLD)
            stdscr.addstr(row, 2, display[:curses.COLS-3])
            stdscr.attroff(curses.A_REVERSE | curses.A_BOLD)
        else:
            stdscr.addstr(row, 2, display[:curses.COLS-3])


def draw_options_view(stdscr, tab: RegisterTab, field_selected: int, option_selected: int) -> None:
    """Draw field value options."""
    reg = tab.get_selected_register()
    if not reg or not reg['fields'] or field_selected >= len(reg['fields']):
        return
    
    val = safe_read_register(reg['base'], reg['offset'])
    field_name, lsb, msb = reg['fields'][field_selected]
    field_val = get_bits(val, lsb, msb)
    
    start_row = 3
    
    stdscr.attron(curses.A_BOLD)
    stdscr.addstr(start_row, 0, f"{field_name}[{msb}:{lsb}]")
    stdscr.attroff(curses.A_BOLD)
    
    stdscr.addstr(start_row + 1, 0, f"Current: 0x{field_val:X}")
    
    options = []
    if reg['field_objects'] and field_selected < len(reg['field_objects']):
        field_obj = reg['field_objects'][field_selected]
        options = field_obj.options
    
    if not options:
        stdscr.addstr(start_row + 3, 0, "No predefined options. Press 'w' to write custom value.")
        return
    
    option_start = start_row + 3
    for visible_idx, (opt_idx, (opt_val, opt_desc)) in enumerate(enumerate(options)):
        row = option_start + visible_idx
        if row >= curses.LINES - 1:
            break
        
        marker = "●" if opt_val == field_val else "○"
        display = f"{marker} 0x{opt_val:X}: {opt_desc}"
        
        if len(display) > curses.COLS - 4:
            display = display[:curses.COLS-7] + "..."
        
        if opt_idx == option_selected:
            stdscr.attron(curses.A_REVERSE | curses.A_BOLD)
            stdscr.addstr(row, 2, display)
            stdscr.attroff(curses.A_REVERSE | curses.A_BOLD)
        else:
            stdscr.addstr(row, 2, display)


class RegisterField:
    """Represents a register field with metadata."""
    def __init__(self, name: str, lsb: int, msb: int, description: str = "", options: list | None = None, ftype: str = "int"):
        self.name = name
        self.lsb = lsb
        self.msb = msb
        self.description = description
        self.options = options or []
        self.ftype = ftype


def init_tabs() -> list:
    """Initialize register tabs from spacemit_k1_registers."""
    try:
        try:
            from spacemit_k1_registers import categorize_registers
        except ImportError:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            if current_dir not in sys.path:
                sys.path.insert(0, current_dir)
            from spacemit_k1_registers import categorize_registers
        
        tabs = [SummaryTab()]
        tabs_dict = categorize_registers()
        
        for cat_name, registers in tabs_dict.items():
            tab = RegisterTab(cat_name)
            for reg_name, reg_info in registers.items():
                fields = []
                field_objects = []
                
                if "fields" in reg_info and reg_info["fields"]:
                    for field_name, field_data in reg_info["fields"].items():
                        if "bits" not in field_data:
                            continue
                        
                        bits = field_data["bits"]
                        if not isinstance(bits, (list, tuple)) or len(bits) < 2:
                            continue
                        
                        high, low = bits[0], bits[1]
                        fields.append((field_name, low, high))
                        
                        description = field_data.get("description", "")
                        ftype = field_data.get("type", "int")
                        options = parse_field_options(description)
                        
                        field_obj = RegisterField(field_name, low, high, description, options, ftype)
                        field_objects.append(field_obj)
                
                reg = {
                    'name': reg_name,
                    'base': reg_info["base"],
                    'offset': reg_info["offset"],
                    'fields': fields,
                    'field_objects': field_objects
                }
                tab.registers.append(reg)
            
            if tab.registers:
                tabs.append(tab)
        
        return tabs if tabs else _fallback_tabs()
    
    except ImportError:
        return _fallback_tabs()


def _fallback_tabs() -> list:
    """Fallback tabs if spacemit_k1_registers not available."""
    tabs = [
        SummaryTab(),
        RegisterTab("GPIO"),
        RegisterTab("Clock"),
        RegisterTab("System"),
    ]
    
    tabs[1].add_register("GPIO_OUT", 0xA0000000, 0x00, [("OUT", 0, 31)])
    tabs[1].add_register("GPIO_IN", 0xA0000000, 0x04, [("IN", 0, 31)])
    tabs[2].add_register("CLKSEL", 0xB0000000, 0x00, [("DIV", 0, 4), ("SEL", 5, 7)])
    
    return tabs


def init_colors() -> None:
    """Initialize color pairs."""
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(COLOR_TITLE, curses.COLOR_YELLOW, -1)
    curses.init_pair(COLOR_TAB_NORMAL, curses.COLOR_WHITE, curses.COLOR_BLACK)
    curses.init_pair(COLOR_TAB_SELECTED, curses.COLOR_BLACK, curses.COLOR_YELLOW)
    curses.init_pair(COLOR_ERROR, curses.COLOR_RED, curses.COLOR_BLACK)
    curses.init_pair(COLOR_LABEL, curses.COLOR_CYAN, -1)
    curses.init_pair(COLOR_VALUE, curses.COLOR_GREEN, -1)


def handle_tab_navigation(key: int, state: AppState, tabs: list) -> None:
    """Handle left/right tab navigation."""
    if key == curses.KEY_LEFT:
        state.current_tab = (state.current_tab - 1) % len(tabs)
        state.view_mode = "registers"
        state.field_selected = 0
        state.option_selected = 0
        state.last_message = ""
        state.need_full_redraw = True
    elif key == curses.KEY_RIGHT:
        state.current_tab = (state.current_tab + 1) % len(tabs)
        state.view_mode = "registers"
        state.field_selected = 0
        state.option_selected = 0
        state.last_message = ""
        state.need_full_redraw = True


def handle_summary_tab_input(stdscr, key: int, state: AppState, tabs: list) -> None:
    """Handle input for summary tab."""
    if key == ord('r'):
        tabs[state.current_tab].refresh()
        state.last_message = "Summary refreshed"


def handle_register_view_input(stdscr, key: int, state: AppState, tabs: list) -> None:
    """Handle input in registers view."""
    tab = tabs[state.current_tab]
    
    if key == curses.KEY_DOWN:
        tab.selected = (tab.selected + 1) % len(tab.registers)
        state.last_message = ""
    
    elif key == curses.KEY_UP:
        tab.selected = (tab.selected - 1) % len(tab.registers)
        state.last_message = ""
    
    elif key == ord('\n'):
        reg = tab.get_selected_register()
        if reg and reg['fields']:
            state.view_mode = "fields"
            state.field_selected = 0
            state.last_message = ""
    
    elif key == ord('w'):
        reg = tab.get_selected_register()
        if not reg:
            return
        
        curses.echo()
        try:
            stdscr.addstr(curses.LINES - 3, 0, "New value (hex): 0x")
            stdscr.clrtoeol()
            stdscr.refresh()
            input_str = stdscr.getstr().decode().strip()
            
            if input_str:
                new_val = parse_hex_input(input_str, MAX_32BIT_VALUE)
                write_register(reg['base'], reg['offset'], new_val)
                state.write_count += 1
                state.last_message = f"Wrote 0x{new_val:08X}"
                state.need_full_redraw = True
        except ValueError as e:
            state.last_message = f"Invalid input: {e}"
        except Exception as e:
            state.last_message = f"Write error: {str(e)[:30]}"
        finally:
            curses.noecho()


def handle_fields_view_input(stdscr, key: int, state: AppState, tabs: list) -> None:
    """Handle input in fields view."""
    tab = tabs[state.current_tab]
    reg = tab.get_selected_register()
    if not reg or not reg['fields']:
        state.view_mode = "registers"
        return
    
    if key == curses.KEY_DOWN:
        state.field_selected = (state.field_selected + 1) % len(reg['fields'])
        state.last_message = ""
    
    elif key == curses.KEY_UP:
        state.field_selected = (state.field_selected - 1) % len(reg['fields'])
        state.last_message = ""
    
    elif key == 27:  # ESC
        state.view_mode = "registers"
        state.field_selected = 0
        state.last_message = ""
    
    elif key == ord('\n'):
        state.view_mode = "options"
        state.option_selected = 0
        state.last_message = ""
    
    elif key == ord('w'):
        field_name, lsb, msb = reg['fields'][state.field_selected]
        
        curses.echo()
        try:
            stdscr.addstr(curses.LINES - 3, 0, f"Write {field_name} (hex): 0x")
            stdscr.clrtoeol()
            stdscr.refresh()
            input_str = stdscr.getstr().decode().strip()
            
            if input_str:
                new_fval = parse_hex_input(input_str)
                val = safe_read_register(reg['base'], reg['offset'])
                mask = ((1 << (msb - lsb + 1)) - 1) << lsb
                new_val = (val & ~mask) | ((new_fval << lsb) & mask)
                write_register(reg['base'], reg['offset'], new_val)
                state.write_count += 1
                state.last_message = f"Wrote field: 0x{new_fval:X}"
                state.need_full_redraw = True
        except ValueError as e:
            state.last_message = f"Invalid input: {e}"
        except Exception as e:
            state.last_message = f"Write error: {str(e)[:30]}"
        finally:
            curses.noecho()


def handle_options_view_input(stdscr, key: int, state: AppState, tabs: list) -> None:
    """Handle input in options view."""
    tab = tabs[state.current_tab]
    reg = tab.get_selected_register()
    if not reg or not reg['fields'] or state.field_selected >= len(reg['fields']):
        state.view_mode = "fields"
        return
    
    field_name, lsb, msb = reg['fields'][state.field_selected]
    options = []
    if reg['field_objects'] and state.field_selected < len(reg['field_objects']):
        options = reg['field_objects'][state.field_selected].options
    
    if not options:
        state.view_mode = "fields"
        return
    
    if key == curses.KEY_DOWN:
        state.option_selected = (state.option_selected + 1) % len(options)
        state.last_message = ""
    
    elif key == curses.KEY_UP:
        state.option_selected = (state.option_selected - 1) % len(options)
        state.last_message = ""
    
    elif key == 27:  # ESC
        state.view_mode = "fields"
        state.option_selected = 0
        state.last_message = ""
    
    elif key == ord('\n'):
        if state.option_selected < len(options):
            opt_val, opt_desc = options[state.option_selected]
            
            try:
                val = safe_read_register(reg['base'], reg['offset'])
                mask = ((1 << (msb - lsb + 1)) - 1) << lsb
                new_val = (val & ~mask) | ((opt_val << lsb) & mask)
                write_register(reg['base'], reg['offset'], new_val)
                state.write_count += 1
                state.last_message = f"Wrote {opt_desc} (0x{opt_val:X})"
                state.view_mode = "fields"
                state.need_full_redraw = True
            except Exception as e:
                state.last_message = f"Write error: {str(e)[:30]}"
    
    elif key == ord('w'):
        curses.echo()
        try:
            field_width = msb - lsb + 1
            max_val = (1 << field_width) - 1
            stdscr.addstr(curses.LINES - 3, 0, f"Write {field_name} (hex, max 0x{max_val:X}): 0x")
            stdscr.clrtoeol()
            stdscr.refresh()
            input_str = stdscr.getstr().decode().strip()
            
            if input_str:
                new_fval = parse_hex_input(input_str, max_val)
                val = safe_read_register(reg['base'], reg['offset'])
                mask = ((1 << field_width) - 1) << lsb
                new_val = (val & ~mask) | ((new_fval << lsb) & mask)
                write_register(reg['base'], reg['offset'], new_val)
                state.write_count += 1
                state.last_message = f"Wrote {field_name}: 0x{new_fval:X}"
                state.view_mode = "fields"
                state.need_full_redraw = True
        except ValueError as e:
            state.last_message = f"Invalid input: {e}"
        except Exception as e:
            state.last_message = f"Write error: {str(e)[:30]}"
        finally:
            curses.noecho()


def main(stdscr):
    """Main TUI loop."""
    curses.curs_set(0)
    init_colors()
    
    tabs = init_tabs()
    state = AppState()
    
    try:
        while True:
            height, width = stdscr.getmaxyx()
            
            if height < MIN_TERMINAL_HEIGHT or width < MIN_TERMINAL_WIDTH:
                stdscr.clear()
                warning = f"Terminal too small (min {MIN_TERMINAL_WIDTH}x{MIN_TERMINAL_HEIGHT})"
                stdscr.addstr(height // 2, max((width - len(warning)) // 2, 0), warning)
                stdscr.refresh()
                stdscr.getch()
                continue
            
            # Full redraw for non-Summary tabs or when needed
            if not isinstance(tabs[state.current_tab], SummaryTab) or state.need_full_redraw:
                stdscr.clear()
                draw_header(stdscr, state.current_tab, tabs)
                
                if isinstance(tabs[state.current_tab], SummaryTab):
                    draw_summary_data_only(stdscr, tabs[state.current_tab])
                    tabs[state.current_tab].mark_drawn()
                elif state.view_mode == "registers":
                    
                    draw_registers_view(stdscr, tabs[state.current_tab])
                elif state.view_mode == "fields":
                    draw_fields_view(stdscr, tabs[state.current_tab], state.field_selected)
                elif state.view_mode == "options":
                    draw_options_view(stdscr, tabs[state.current_tab], state.field_selected, state.option_selected)
                
                state.need_full_redraw = False
            else:
                # Partial redraw for Summary tab - only update data area
                summary_tab = tabs[state.current_tab]
                if summary_tab.should_refresh(0.5):
                    summary_tab.refresh()
                    if summary_tab.data_changed():
                        # Clear only the data area (rows 3 onwards)
                        for row in range(3, curses.LINES - 2):
                            stdscr.move(row, 0)
                            stdscr.clrtoeol()
                        draw_summary_data_only(stdscr, summary_tab)
                        summary_tab.mark_drawn()
            
            # Status bar (always redraw)
            status = f"Writes: {state.write_count} | {state.view_mode} | {state.last_message}"
            stdscr.attron(curses.color_pair(COLOR_TAB_NORMAL))
            stdscr.addstr(curses.LINES - 2, 0, status[:curses.COLS-1])
            stdscr.attroff(curses.color_pair(COLOR_TAB_NORMAL))
            
            # Help bar
            if isinstance(tabs[state.current_tab], SummaryTab):
                help_text = "←→:tabs | r:refresh | q:quit"
            elif state.view_mode == "registers":
                help_text = "↑↓:nav | ←→:tabs | Enter:fields | w:write | q:quit"
            elif state.view_mode == "fields":
                help_text = "↑↓:nav | Enter:options | Esc:back | w:write | q:quit"
            else:
                help_text = "↑↓:nav | Enter:write | Esc:back | w:custom | q:quit"
            
            stdscr.addstr(curses.LINES - 1, 0, help_text[:curses.COLS-1])
            stdscr.refresh()
            
            # Input handling - non-blocking for Summary, blocking for others
            if isinstance(tabs[state.current_tab], SummaryTab):
                stdscr.nodelay(True)
                key = stdscr.getch()
                if key == -1:
                    time.sleep(0.05)
                    continue
                stdscr.nodelay(False)
            else:
                key = stdscr.getch()
            
            # Global commands
            if key == ord('q'):
                break
            
            # Tab navigation
            if key in (curses.KEY_LEFT, curses.KEY_RIGHT):
                handle_tab_navigation(key, state, tabs)
                continue
            
            # Summary tab specific
            if isinstance(tabs[state.current_tab], SummaryTab):
                handle_summary_tab_input(stdscr, key, state, tabs)
                continue
            
            # Register tab input handling by view mode
            if state.view_mode == "registers":
                handle_register_view_input(stdscr, key, state, tabs)
            elif state.view_mode == "fields":
                handle_fields_view_input(stdscr, key, state, tabs)
            elif state.view_mode == "options":
                handle_options_view_input(stdscr, key, state, tabs)
    
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logging.critical(f"Critical error in main loop: {e}\n{traceback.format_exc()}")
    
    finally:
        try:
            curses.nocbreak()
            curses.echo()
            curses.curs_set(1)
            stdscr.keypad(False)
        except Exception:
            pass


if __name__ == "__main__":
    try:
        curses.wrapper(main)
    except Exception as e:
        print(f"Fatal error: {e}")
        logging.critical(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)