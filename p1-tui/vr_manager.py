#!/usr/bin/env python3
"""
VR Manager for SPM8821

Manages the single SPM8821Driver
"""

from spm8821 import SPM8821Driver

class VRManager:
    def __init__(self):
        self.available_drivers = [SPM8821Driver]  # list for TUI compatibility
        self.current_driver = None

    def detect_vrs(self):
        """Return list of detected VRs (currently just the one driver)"""
        detected = []
        for drv_class in self.available_drivers:
            drv = drv_class()
            if drv.detect():
                detected.append(drv_class)
        return detected

    def load_driver(self):
        """Instantiate and open the driver"""
        drv_class = self.available_drivers[0]
        instance = drv_class()
        if instance.detect():
            instance.open()
            self.current_driver = instance
            return instance
        else:
            return None
