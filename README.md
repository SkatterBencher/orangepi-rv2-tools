OrangePi RV2 (Ky X1 / SpaceMit K1) -- Tuning & Overclocking Research
===================================================================

This repository contains all tools, experiments, kernel patches, and documentation related to my work on the **OrangePi RV2 8GB** featuring the **Ky X1** SoC (a re-branded SpaceMit K1).

The goal of this project is to build the technical foundation for a future **SkatterBencher overclocking guide** by developing:

- Telemetry tools
- Performance governor controls
- Runtime voltage control
- Frequency scaling patches
- Low-level SoC register access

This is active research. Some components are experimental or alpha quality.

* * * * *

Hardware Platform
-----------------
- **Board:** OrangePi RV2 8GB
- **SoC:** Ky X1 (SpaceMit K1)
- **PMIC:** SpaceMit Power Stone P1 (SPM8821)
- **Architecture:** 8-core RISC-V

* * * * *

Repository Structure
--------------------
| Folder | Description |
| --- | --- |
| ky-x1-kernel/ | Relevant kernel files |
| ky-x1-soc-tui/ | SoC register TUI (alpha) |
| p1-tui/ | SPM8821 PMIC voltage control TUI |
| rv2-device-tree/ | Device tree modifications & experiments |
| rv2-docs/ | Documentation |
| rv2-perf-governors/ | Performance governor setup scripts + service |
| rv2-telemetry-tui/ | Live telemetry + CSV export tool |

* * * * *

Project Overview
----------------

### 1\. Telemetry (rv2-telemetry-tui)

The telemetry tool reads directly from existing Linux kernel interfaces:

| Domain | Source |
| --- | --- |
| Frequency | /sys/kernel/debug/clk/clk_summary |
| Voltage | /sys/class/regulator/regulator.* |
| Temperature | /sys/class/hwmon/hwmon*/ |
| CPU Usage | /proc/stat |
| Governors | cpufreq + pcie_aspm |

* * * * *

### 2\. Performance Governors (rv2-perf-governors)

To prepare for tuning, all governors are locked to **performance** mode.

echo powersave | tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor\
echo performance | tee /sys/module/pcie_aspm/parameters/policy\
echo performance | tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor

A systemd service is included for automatic startup. After locking governors, CPU runs at 1.6 GHz (stock maximum).

* * * * *

### 3\. Voltage Control (p1-tui)

The OrangePi RV2 uses the **SpaceMit Power Stone P1 PMIC (SPM8821)**.

**Kernel Module:**

- Registers `/dev/spm8821_vr`
- Provides direct I2C access to the PMIC
- Allows voltage read/write via `ioctl`
- Bypasses the standard DVFS control path

Build and load:

cd module/\
make\
sudo insmod spm8821.ko

Run vr_control.py for realtime voltage access.

* * * * *

### 4\. Overclocking

1800 MHz limit:

The stock kernel limits the Ky X1 to 1600 MHz (ky-cpufreq.c): #define K1_MAX_FREQ_LIMITATION (1600000)

After patching and recompiling the kernel 1800 MHz boots correctly, but seems unstable for now

OPP:
Device tree location: ky/x1_orangepi-rv2.dtb

Convert DTB to DTS: dtc -I dtb -O dts -o x1_orangepi-rv2.dts x1_orangepi-rv2.dtb

Modify OPP tables, recompile to DTB: dtc -I dts -O dtb -o x1_orangepi-rv2_mod.dtb x1_orangepi-rv2.dts

replace, and reboot.

* * * * *

### 6\. SoC Register TUI (ky-x1-soc-tui)

Alpha tool for:

- Reading SoC registers
- Writing selected registers

* * * * *

Current Status
--------------

- Performance governors working
- Telemetry system working
- Runtime voltage override working
- 1800 MHz unlocked via kernel patch
- 2000 MHz unstable
- PLL3 runtime control restricted
- Full overclocking path not yet complete

* * * * *

Goal
----

The long-term goal is to produce a complete **SkatterBencher overclocking guide** for the OrangePi RV2, similar to previous SBC deep dives.

This repository documents the technical groundwork required to make that possible.\
More updates to follow.
