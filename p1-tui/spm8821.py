#!/usr/bin/env python3
"""
SPM8821 PMIC Voltage Regulator Driver

Standalone driver for SpaceMit P1 and compatible platforms.
No base class required.
"""

import os
import struct
import fcntl

def _IOWR(magic, nr, size):
    """Python equivalent of kernel _IOWR macro"""
    _IOC_NRBITS = 8
    _IOC_TYPEBITS = 8
    _IOC_SIZEBITS = 14
    _IOC_NRSHIFT = 0
    _IOC_TYPESHIFT = _IOC_NRSHIFT + _IOC_NRBITS
    _IOC_SIZESHIFT = _IOC_TYPESHIFT + _IOC_TYPEBITS
    _IOC_DIRSHIFT = _IOC_SIZESHIFT + _IOC_SIZEBITS

    _IOC_READ = 2
    _IOC_WRITE = 1

    return ((_IOC_READ | _IOC_WRITE) << _IOC_DIRSHIFT) | \
           (ord(magic) << _IOC_TYPESHIFT) | \
           (nr << _IOC_NRSHIFT) | \
           (size << _IOC_SIZESHIFT)


class SPM8821Driver:
    """Driver for SPM8821 PMIC"""

    DRIVER_NAME = "SPM8821"
    DRIVER_VERSION = "2.0"
    CHIP_MODEL = "SPM8821"
    I2C_BUS = 8
    I2C_ADDR = 0x41

    DEVICE_PATH = "/dev/spm8821_vr"
    REGULATOR_SYSFS = "/sys/class/regulator"

    # ioctl commands
    VR_IOCTL_MAGIC = 'v'
    VR_GET_VOLTAGE = _IOWR(VR_IOCTL_MAGIC, 0, 36)
    VR_SET_VOLTAGE_DIRECT = _IOWR(VR_IOCTL_MAGIC, 2, 44)

    def __init__(self):
        self.device = None
        self.regulators = []
        self.constraints = {}
        self.num_users = {}

    def detect(self) -> bool:
        """Check if SPM8821 is present"""
        if not os.path.exists(self.DEVICE_PATH):
            return False
        i2c_device = f"/sys/bus/i2c/devices/{self.I2C_BUS}-00{self.I2C_ADDR:02x}"
        return os.path.exists(i2c_device)

    def open(self):
        """Open connection to kernel module"""
        if not os.path.exists(self.DEVICE_PATH):
            raise RuntimeError(f"{self.DEVICE_PATH} not found. Is the kernel module loaded?")
        self.device = os.open(self.DEVICE_PATH, os.O_RDWR)
        self.regulators = self._discover_regulators()
        self._load_metadata()

    def close(self):
        if self.device is not None:
            os.close(self.device)
            self.device = None

    def _discover_regulators(self):
        regs = []
        if not os.path.exists(self.REGULATOR_SYSFS):
            return regs
        for fname in os.listdir(self.REGULATOR_SYSFS):
            if not fname.startswith("regulator."):
                continue
            reg_num = fname.split(".")[-1]
            if not reg_num.isdigit():
                continue
            index = int(reg_num)
            reg_path = os.path.join(self.REGULATOR_SYSFS, fname)
            reg_type = "voltage"
            type_path = os.path.join(reg_path, "type")
            if os.path.exists(type_path):
                with open(type_path) as f:
                    reg_type = f.read().strip()
            name_path = os.path.join(reg_path, "name")
            if os.path.exists(name_path):
                with open(name_path) as f:
                    reg_name = f.read().strip()
                    if reg_type == "voltage":
                        regs.append((index, reg_name, reg_type))
        return sorted(regs)

    def _load_metadata(self):
        for idx, name, _ in self.regulators:
            reg_path = f"{self.REGULATOR_SYSFS}/regulator.{idx}"
            min_uv = 500000
            max_uv = 3450000
            try:
                with open(f"{reg_path}/min_microvolts") as f:
                    min_uv = int(f.read().strip())
            except:
                pass
            try:
                with open(f"{reg_path}/max_microvolts") as f:
                    max_uv = int(f.read().strip())
            except:
                pass
            self.constraints[name] = (min_uv, max_uv)
            try:
                with open(f"{reg_path}/num_users") as f:
                    self.num_users[name] = int(f.read().strip())
            except:
                self.num_users[name] = 0

    def get_regulator_list(self):
        return self.regulators

    def get_voltage(self, regulator_name: str) -> int:
        if self.device is None:
            raise RuntimeError("Device not opened")
        name_bytes = regulator_name.encode('utf-8').ljust(32, b'\x00')
        buf = struct.pack('32si', name_bytes, 0)
        result = fcntl.ioctl(self.device, self.VR_GET_VOLTAGE, buf)
        _, voltage = struct.unpack('32si', result)
        return voltage

    def set_voltage(self, regulator_name: str, voltage_uv: int) -> int:
        if self.device is None:
            raise RuntimeError("Device not opened")
        name_bytes = regulator_name.encode('utf-8').ljust(32, b'\x00')
        buf = struct.pack('32siii', name_bytes, 0, voltage_uv, voltage_uv)
        result = fcntl.ioctl(self.device, self.VR_SET_VOLTAGE_DIRECT, buf)
        _, actual_voltage, _, _ = struct.unpack('32siii', result)
        return actual_voltage

    def get_voltage_constraints(self, regulator_name: str):
        return self.constraints.get(regulator_name, (500000, 3450000))

    def get_num_users(self, regulator_name: str) -> int:
        return self.num_users.get(regulator_name, 0)

    def get_info(self):
        """Return dict with basic info for TUI display"""
        return {
            'driver_name': self.DRIVER_NAME,
            'driver_version': self.DRIVER_VERSION,
            'chip_model': self.CHIP_MODEL,
            'i2c_bus': self.I2C_BUS,
            'i2c_addr': hex(self.I2C_ADDR)
        }
