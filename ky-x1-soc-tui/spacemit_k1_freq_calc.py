#!/usr/bin/env python3
"""
SpaceMit K1 Frequency Calculator
Reads SoC registers and calculates actual clock frequencies,
including PLL3 VCO from the hardware registers (best-guess if registers are zero).
"""

import logging

# -------------------------------------------------------------------
# PLL3 rate table (matches kernel pll3_rate_tbl)
# Each entry: (frequency MHz, reg5, reg6, reg7, reg8, reg9, div_frac)
PLL3_RATE_TBL = [
    (1600, 0x61, 0xcd, 0x50, 0x00, 0x43, 0xeaaaab),
    (1800, 0x61, 0xcd, 0x50, 0x00, 0x4b, 0x000000),
    (2000, 0x62, 0xdd, 0x50, 0x00, 0x2a, 0xeaaaab),
    (3000, 0x66, 0xdd, 0x50, 0x00, 0x3f, 0xe00000),
    (3200, 0x67, 0xdd, 0x50, 0x00, 0x43, 0xeaaaab),
    (2457.6, 0x64, 0xdd, 0x50, 0x00, 0x33, 0x0ccccd),
]

# Fixed clocks (MHz)
FIXED_CLOCKS = {
    "vctcxo_24": 24,
    "vctcxo_3": 3,
    "vctcxo_1": 1,
    "clk_32k": 0.032768,
    "pll1": 2457.6,
    "pll2": 3000,
}

# CPU core clock sources (derived from PLL2/3 or fixed)
PLL1_DIV = {i: 2457.6 / i for i in range(1, 9)}
PLL2_DIV = {i: 3000 / i for i in range(1, 9)}
PLL3_DIV = {i: None for i in range(1, 9)}  # will be calculated dynamically

CPU_CORE_CLK_SEL = {
    0: PLL1_DIV[4],
    1: PLL1_DIV[3],
    2: PLL1_DIV[6],
    3: PLL1_DIV[5],
    4: PLL1_DIV[2],
    5: None,        # PLL3_div3 will be computed dynamically
    6: PLL2_DIV[3],
    7: None,        # hi_clk_sel
}

CPU_HI_CLK_SEL = {
    0: None,        # will be populated dynamically from PLL3
    1: None,
}

# GPU / VPU / JPEG clocks (placeholders, will patch PLL3 divisors dynamically)
GPU_CLK_SEL = {
    0: PLL1_DIV[4],
    1: PLL1_DIV[5],
    2: PLL1_DIV[3], 
    3: PLL1_DIV[6], 
    4: None,        # PLL3_div6 will be computed dynamically
    5: PLL2_DIV[3], 
    6: PLL2_DIV[4], 
    7: PLL2_DIV[5],
}

VPU_CLK_SEL = {
    0: PLL1_DIV[4],
    1: PLL1_DIV[5],
    2: PLL1_DIV[3], 
    3: PLL1_DIV[6], 
    4: None,        # PLL3_div6 will be computed dynamically
    5: PLL2_DIV[3], 
    6: PLL2_DIV[4], 
    7: PLL2_DIV[5],
}

JPG_CLK_SEL = {
    0: PLL1_DIV[4],
    1: PLL1_DIV[6],
    2: PLL1_DIV[5], 
    3: PLL1_DIV[3], 
    4: PLL1_DIV[2], 
    5: PLL2_DIV[4], 
    6: PLL2_DIV[3], 
    7: None,        # genuinely None
}

# -------------------------------------------------------------------
class FrequencyCalculator:
    """Calculates actual clock frequencies from register values, including PLL3 VCO."""
    def __init__(self, read_register_func):
        self.read_register = read_register_func
        self.error_log = []

        # PLL3 VCO MHz
        self.pll3_vco = self._read_pll3_vco()

        # Populate dynamic PLL3 divisors
        for i in range(1, 9):
            PLL3_DIV[i] = self.pll3_vco / i if self.pll3_vco else None

        # Patch CPU_CORE_CLK_SEL and HI clocks
        CPU_CORE_CLK_SEL[5] = PLL3_DIV[3]  # PLL3_div3
        CPU_HI_CLK_SEL[0] = PLL3_DIV[2]    # C0_HI = PLL3 / 2
        CPU_HI_CLK_SEL[1] = PLL3_DIV[1]    # C1_HI = PLL3 / 1

        # Patch GPU/VPU/JPG clocks that depend on PLL3 divisors
        GPU_CLK_SEL[4] = PLL3_DIV[6] 
        GPU_CLK_SEL[4] = PLL3_DIV[6] 

    # --- Helper functions ---
    def _safe_read(self, base, offset, reg_name=""):
        try:
            return self.read_register(base, offset)
        except Exception as e:
            msg = f"Error reading {reg_name}"
            self.error_log.append(msg)
            logging.error(f"{msg}: {e}")
            return None

    def _extract_bits(self, value, lsb, msb):
        if value is None:
            return None
        mask = ((1 << (msb - lsb + 1)) - 1) << lsb
        return (value & mask) >> lsb

    def _format_freq(self, freq_mhz):
        if freq_mhz is None:
            return "N/A"
        if freq_mhz < 1:
            return f"{freq_mhz*1000:.0f} kHz"
        return f"{freq_mhz:.0f} MHz"

    # --- PLL3 reading ---
    def _read_pll3_vco(self):
        """Read PLL3 configuration and calculate actual VCO frequency in MHz (best guess)."""
        sw3 = self._safe_read(0xD4090000, 0x12C, "PLL3_SW3_CTRL")
        sw1 = self._safe_read(0xD4090000, 0x124, "PLL3_SW1_CTRL")

        if sw1 is None:
            return None

        # Ignore SW3 bit 31 (PLL3 enable)
        # Use SW1 reg5 for best guess
        reg5_val = sw1 & 0xFF
        candidates = [freq for freq, r5, *_ in PLL3_RATE_TBL if r5 == reg5_val]

        if candidates:
            # choose the highest matching frequency as best guess
            return max(candidates)
        return None

    # --- Fixed clocks ---
    def get_fixed_clocks(self):
        return {
            "vctcxo_24": "24 MHz",
            "vctcxo_3": "3 MHz",
            "vctcxo_1": "1 MHz",
            "clk_32k": "32.768 kHz",
            "pll1": "2457.6 MHz",
            "pll2": "3000 MHz",
            "pll3": self._format_freq(self.pll3_vco),
        }

    # --- CPU clusters ---
    def _get_cpu_cluster(self, base_addr, reg_offset, cluster_name, pmu_dm_cc_ap_offset=0x0C):
        clocks = {}

        # --- Read cluster register ---
        reg_val = self._safe_read(base_addr, reg_offset, f"PMUA_{cluster_name}_CLK_CTRL")
        if reg_val is None:
            return {"error": f"Cannot read {cluster_name} register"}

        clk_sel   = self._extract_bits(reg_val, 0, 2)   # Clock source selection
        core_div  = self._extract_bits(reg_val, 3, 5)
        ace_div   = self._extract_bits(reg_val, 6, 8)
        tcm_div   = self._extract_bits(reg_val, 9, 11)
        hi_sel    = self._extract_bits(reg_val, 13, 13)

        # --- Determine HI frequency ---
        hi_freq = CPU_HI_CLK_SEL.get(hi_sel)
        clocks[f"{cluster_name}_HI"] = self._format_freq(hi_freq)

        # --- Determine base/core clock ---
        if clk_sel == 7:  # hi_clk selected
            base_freq = hi_freq
        else:
            base_freq = CPU_CORE_CLK_SEL.get(clk_sel)

        if base_freq:
            core_clk = base_freq / (core_div + 1)
            clocks[f"{cluster_name}_CORE"] = self._format_freq(core_clk)
            clocks[f"{cluster_name}_ACE"]  = self._format_freq(core_clk / (ace_div + 1))
            clocks[f"{cluster_name}_TCM"]  = self._format_freq(core_clk / (tcm_div + 1))
        else:
            clocks[f"{cluster_name}_CORE"] = clocks[f"{cluster_name}_ACE"] = clocks[f"{cluster_name}_TCM"] = "N/A"

        # --- Read PMU_DM_CC_AP for PCLK/ACLK dividers ---
        pmu_val = self._safe_read(base_addr, pmu_dm_cc_ap_offset, "PMU_DM_CC_AP")
        if pmu_val:
            if cluster_name == "C0":
                clk_div  = self._extract_bits(pmu_val, 0, 2)  # C0_CLK_DIV
                aclk_div = self._extract_bits(pmu_val, 3, 5)  # C0_ACLK_DIV
            elif cluster_name == "C1":
                clk_div  = self._extract_bits(pmu_val, 6, 8)  # C1_CLK_DIV
                aclk_div = self._extract_bits(pmu_val, 9, 11) # C1_ACLK_DIV
            else:
                clk_div = aclk_div = None

            # Get PLL / base clock from CPU_CORE_CLK_SEL
            pll_base = CPU_CORE_CLK_SEL.get(clk_sel)

            # If clk_sel = 7, use HI clock directly
            if clk_sel == 7 or pll_base is None:
                pll_base = hi_freq

            # Calculate PCLK / ACLK
            pclk = pll_base / (clk_div + 1) if pll_base is not None else None
            aclk = pclk / (aclk_div + 1) if pclk is not None else None

            clocks[f"{cluster_name}_PCLK"] = self._format_freq(pclk)
            clocks[f"{cluster_name}_ACLK"] = self._format_freq(aclk)

        return clocks


    def get_c0_clocks(self):
        return self._get_cpu_cluster(0xD4282800, 0x38C, "C0")

    def get_c1_clocks(self):
        return self._get_cpu_cluster(0xD4282800, 0x390, "C1")


    # --- GPU / VPU / JPEG / ACLK ---
    def get_gpu_clocks(self):
        clocks = {}
        reg_val = self._safe_read(0xD4282800, 0xCC, "PMU_GPU_CLK_RES_CTRL")
        if reg_val is None: return {"error": "Cannot read GPU register"}
        sel = self._extract_bits(reg_val, 18, 20)
        div = self._extract_bits(reg_val, 12, 14)
        en = self._extract_bits(reg_val, 4, 4)
        if not en:
            clocks["GPU"] = "Disabled"
        else:
            freq = GPU_CLK_SEL.get(sel)
            clocks["GPU"] = self._format_freq(freq / (div + 1)) if freq else "N/A"
        return clocks

    def get_vpu_clocks(self):
        clocks = {}
        reg_val = self._safe_read(0xD4282800, 0xA4, "PMU_VPU_CLK_RES_CTRL")
        if reg_val is None: return {"error": "Cannot read VPU register"}
        sel = self._extract_bits(reg_val, 10, 12)
        div = self._extract_bits(reg_val, 13, 15)
        en = self._extract_bits(reg_val, 3, 3)
        if not en:
            clocks["VPU"] = "Disabled"
        else:
            freq = VPU_CLK_SEL.get(sel)
            clocks["VPU"] = self._format_freq(freq / (div + 1)) if freq else "N/A"
        return clocks

    def get_jpg_clocks(self):
        clocks = {}
        reg_val = self._safe_read(0xD4282800, 0x20, "PMU_JPEG_CLK_RES_CTRL")
        if reg_val is None: return {"error": "Cannot read JPEG register"}
        sel = self._extract_bits(reg_val, 2, 4)
        div = self._extract_bits(reg_val, 5, 7)
        en = self._extract_bits(reg_val, 1, 1)
        if not en:
            clocks["JPEG"] = "Disabled"
        else:
            freq = JPG_CLK_SEL.get(sel)
            clocks["JPEG"] = self._format_freq(freq / (div + 1)) if freq else "N/A"
        return clocks

    def get_aclk(self):
        aclk = {}
        reg_val = self._safe_read(0xD4282800, 0x388, "PMUA_ACLK_CTRL")
        if reg_val is None: return {"error": "Cannot read ACLK register"}
        sel = self._extract_bits(reg_val, 0, 0)
        div = self._extract_bits(reg_val, 1, 2)
        base_freq = 249 if sel == 0 else 312
        aclk["ACLK"] = self._format_freq(base_freq / (div + 1))
        return aclk

    # --- Summary ---
    def get_summary(self):
        return {
            "fixed_clocks": self.get_fixed_clocks(),
            "cpu_c0": self.get_c0_clocks(),
            "cpu_c1": self.get_c1_clocks(),
            "gpu": self.get_gpu_clocks(),
            "vpu": self.get_vpu_clocks(),
            "jpg": self.get_jpg_clocks(),
            "aclk": self.get_aclk(),
        }


# -------------------------------------------------------------------
if __name__ == "__main__":
    # Dummy reader for testing
    def dummy_read(base, offset):
        # Return plausible values for testing
        if offset == 0x124:  # SW1
            return 0x61
        if offset == 0x12C:  # SW3
            return 0x00000000
        return 0x12345678

    calc = FrequencyCalculator(dummy_read)
    summary = calc.get_summary()
    for group, clocks in summary.items():
        print(f"\n{group.upper()}")
        for name, freq in clocks.items():
            print(f"  {name}: {freq}")
