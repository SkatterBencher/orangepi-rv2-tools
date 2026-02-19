#!/usr/bin/env python3
"""
SpaceMit K1 Register Definitions
Defines all registers, their addresses, and field-level information.
"""

REGISTERS = {
    "MPMU_FCCR": {
        "base": 0xD4050000,
        "offset": 0x008,
        "description": "Frequency Change Control Register",
        "fields": {
            "FCD": {"bits": [29, 29], "description": """I2SCLK307M
                                                        0: PLL1 307.2M/2=153.6M
                                                        1: 307.2M PLL1"""},
            "PLL1FBD": {"bits": [8, 0], "description": "PLL1 FBDIV"},
        }
    },
    "MPMU_POSR": {
        "base": 0xD4050000,
        "offset": 0x010,
        "description": "Power-On Status Register",
        "fields": {
            "PLL3_LOCK": {"bits": [29, 29], "description": """0: Lock Disabled
                                                            1: Lock Enabled"""},
            "PLL2_LOCK": {"bits": [28, 28], "description": """0: Lock Disabled
                                                            1: Lock Enabled"""},
            "PLL1_LOCK": {"bits": [27, 27], "description": """0: Lock Disabled
                                                            1: Lock Enabled"""},
        }
    },

    "PLL3_SW1_CTRL": {
        "base": 0xD4090000,
        "offset": 0x124,
        "description": "PLL3 Switch 1 Control",
        "fields": {
            # REG8 [31:24]
            "INPUT_FREQ_SEL": {"bits": [30, 30], "description": """Input frequency selection
                                                                    0: 24 MHz
                                                                    1: 19.2/38.4 MHz"""},
            "FVCO_SRC": {"bits": [29, 29], "description": """FVCO configuration source
                                                                    0: External value
                                                                    1: Internal default"""},
            "FREQ_19_38_SEL": {"bits": [28, 28], "description": """Select input frequency between 19.2 and 38.4 MHz
                                                                    0: 38.4 MHz
                                                                    1: 19.2 MHz"""},
            "CK_TEST_DRV": {"bits": [27, 26], "description": """CK_test driving capability
                                                                    00: 2 driver cells
                                                                    01: 3 driver cells
                                                                    10: 4 driver cells
                                                                    11: 5 driver cells"""},
            "CK_INPUT_SEL": {"bits": [25, 24], "description": """CK input select
                                                                    00: ckin_1 (div200_aud)
                                                                    01: ckin_2 (div3_soc)
                                                                    10: ckin_3 (div5_soc)
                                                                    11: ckin_4 (clk_dac)"""},
            # REG7 [23:16]
            "BYPASS_PD": {"bits": [23, 23], "description": """Bypass PLL power down
                                                                    0: Controlled by PD
                                                                    1: Always on"""},
            "SSC_EN_SEL": {"bits": [22, 22], "description": """SSC enable select
                                                                    0: LDO_rdy
                                                                    1: Pre_lock"""},
            "VREG_CAL_PERIOD": {"bits": [21, 21], "description": """Vreg calibration period
                                                                    0: 128*Tref
                                                                    1: 256*Tref"""},
            "PLL_FAST_LOCK": {"bits": [20, 20], "description": """Enable PLL fast lock
                                                                    0: disable
                                                                    1: enable"""},
            "FORCE_PLL_LOCK": {"bits": [19, 19], "description": """Force PLL lock},
                                                                    0: disable
                                                                    1: enable"""},
            "ATEST_DTEST": {"bits": [18, 16], "description": "ATEST/DTEST select"},
            # REG6 [15:8]
            "LPF_FACTOR": {"bits": [15, 14], "description": """LPF proportionality factor
                                                                    00: fref = 38.4 MHz
                                                                    01/10: fref = 30/27/26/25/24 MHz
                                                                    11: fref = 19.2 MHz"""},
            "PRE_DIV": {"bits": [13, 12], "description": """PLL pre-divider select
                                                                    00: div1 (1G~2G)
                                                                    01: div2 (2G~4G)
                                                                    10: div3 (4G~6G, default)
                                                                    11: div4"""},
            "HIGH_KVCO": {"bits": [11, 11], "description": """High KVCO enable
                                                                    0: disable
                                                                    1: enable"""},
            "REG_CAL_EN": {"bits": [10, 10], "description": """Enable regulator calibration
                                                                    0: disable
                                                                    1: enable"""},
            "VREF_SEL": {"bits": [9, 8], "description": """Regulator calibration Vref select
                                                                    00: vrefh=727mV, vrefl=626mV
                                                                    01: vrefh=750mV, vrefl=650mV
                                                                    10: vrefh=776mV, vrefl=679mV
                                                                    11: vrefh=802mV, vrefl=707mV"""},
            # REG5 [7:0]
            "CHG_BUMP_CUR": {"bits": [7, 5], "description": """Charge-bump current select
                                                                    000: 0.5 µA
                                                                    100: 0.75 µA (24/25/26/27/30 MHz)
                                                                    010/001: 1.0 µA
                                                                    101: 1.25 µA (19.2 MHz)
                                                                    011/010: 1.5 µA
                                                                    110: 1.75 µA (38.4 MHz)
                                                                    001/011: 2.0 µA
                                                                    111: 2.25 µA"""},
            "DAC_CLK_CFG": {"bits": [4, 4], "description": """Config DAC clock
                                                                    0: T_dac = 10xTvco
                                                                    1: T_dac = 12xTvco"""},
            "ADC_CLK_CFG": {"bits": [3, 3], "description": """Config ADC clock
                                                                    0: T_adc = 10xTvco
                                                                    1: T_adc = 12xTvco"""},
            "VCO_BAND": {"bits": [2, 0], "description": """VCO frequency band select
                                                                    000: 0.61~0.76~0.92 GHz
                                                                    001: 0.85~1.07~1.24 GHz
                                                                    010: 1.24~1.37~1.67 GHz
                                                                    011: 1.34~1.67~2.01 GHz
                                                                    100: 1.68~1.97~2.27 GHz
                                                                    101: 1.94~2.28~2.62 GHz
                                                                    110: 2.19~2.58~2.96 GHz
                                                                    111: 2.45~2.88~3.32 GHz"""},
        }
    },

    "PLL3_SW2_CTRL": {
        "base": 0xD4090000,
        "offset": 0x128,
        "description": "PLL3 Switch 2 Control",
        "fields": {
            "PLL_UPDATE_EN": {"bits": [21, 21], "description": """"PLL div update en
                                                                    0: Disable
                                                                    1: Enable"""},
            "PLL_DIV23_EN": {"bits": [20, 20], "description": """0: Disable
                                                            1: Enable"""},
            "PLL_MON_CFG_EN": {"bits": [19, 19], "description": "Monitor enable"},
            "PLL_MON_CFG_DIV": {"bits": [18, 17], "description": "Monitor divider"},
            "PLL_DIV13_EN": {"bits": [16, 16], "description": """0: Disable
                                                            1: Enable"""},
            "PLL_DIV11_EN": {"bits": [15, 15], "description": """0: Disable
                                                            1: Enable"""},
            "PLL_DIV8_EN": {"bits": [7, 7], "description": """0: Disable
                                                            1: Enable"""},
            "PLL_DIV7_EN": {"bits": [6, 6], "description": """0: Disable
                                                            1: Enable"""},
            "PLL_DIV6_EN": {"bits": [5, 5], "description": """0: Disable
                                                            1: Enable"""},
            "PLL_DIV5_EN": {"bits": [4, 4], "description": """0: Disable
                                                            1: Enable"""},
            "PLL_DIV4_EN": {"bits": [3, 3], "description": """0: Disable
                                                            1: Enable"""},
            "PLL_DIV3_EN": {"bits": [2, 2], "description": """0: Disable
                                                            1: Enable"""},
            "PLL_DIV2_EN": {"bits": [1, 1], "description": """0: Disable
                                                            1: Enable"""},
            "PLL_DIV1_EN": {"bits": [0, 0], "description": """0: Disable
                                                            1: Enable"""},
        }
    },

    "PLL3_SW3_CTRL": {
        "base": 0xD4090000,
        "offset": 0x12C,
        "description": "PLL3 Switch 3 Control",
        "fields": {
            "PLL3_SW_EN": {"bits": [31, 31], "description": """0: PLL EN controlled by PMU HW
                                                            1: SW Force Enabled"""},
            "PLL3_DIV_INT": {"bits": [30, 24], "description": "Integer divider value"},
            "PLL3_DIV_FRC": {"bits": [23, 0], "description": "Fractional divider value"},
        }
    },

    "AP_CLK_CTRL_REG": {
        "base": 0xD4282800,
        "offset": 0x4,
        "description": "AP Clock Control Register",
        "fields": {
            "DDR_FREQ_CHG_REQ": {"bits": [22, 22], "description": """Triggers a frequency change
                                                                0: Disable frequency change
                                                                1: enable frequency change"""},
            "AP_ALLOW_SPD_CHG": {"bits": [18, 18], "description": "Indicates whether the AP is allowed to change speed."},
        }
    },

    "PMU_DM_CC_AP": {
        "base": 0xD4282800,
        "offset": 0x0C,
        "description": "Dummy AP Clock Control Register (Read-only). Monitors AP cluster frequency change status and provides clock divider info.",
        "fields": {
            "AP_C1_FC_DONE": {
                "bits": [30, 30],
                "description": """AP Cluster1 Frequency Change Done Status
                                  0: Frequency change not done
                                  1: Frequency change done"""
            },
            "ACLK_FC_DONE": {
                "bits": [29, 29],
                "description": """ACLK Frequency Change Done Status
                                  0: Frequency change not done
                                  1: Frequency change done"""
            },
            "DCLK_FC_DONE": {
                "bits": [28, 28],
                "description": """DDR Clock Frequency Change Done Status
                                  0: Frequency change not done
                                  1: Frequency change done"""
            },
            "AP_C0_FC_DONE": {
                "bits": [27, 27],
                "description": """AP Cluster0 Frequency Change Done Status
                                  0: Frequency change not done
                                  1: Frequency change done"""
            },
            "AP_RD_STATUS": {
                "bits": [25, 25],
                "description": """AP Read Status
                                  0: Not being read / frequency update not in progress
                                  1: Register being read; one of the cores is updating frequency.
                                  Other cores must wait until cleared (<RD_ST Clear> in AP Clock Control Register)."""
            },
            "C1_ACLK_DIV": {
                "bits": [11, 9],
                "description": """Cluster1 AXI Interface Clock Divider
                                  C1_ACLK = PCLK / (C1_ACLK_DIV + 1)"""
            },
            "C1_CLK_DIV": {
                "bits": [8, 6],
                "description": """Cluster1 PCLK Divider
                                  If FCAP.C1_PLLSEL <= 3:
                                      PCLK = selected PLL / (C1_CLK_DIV + 1)
                                  Else:
                                      PCLK = selected PLL directly"""
            },
            "C0_ACLK_DIV": {
                "bits": [5, 3],
                "description": """Cluster0 AXI Interface Clock Divider
                                  C0_ACLK = PCLK / (C0_ACLK_DIV + 1)"""
            },
            "C0_CLK_DIV": {
                "bits": [2, 0],
                "description": """Cluster0 PCLK Divider
                                  If FCAP.C0_PLLSEL <= 3:
                                      PCLK = selected PLL / (C0_CLK_DIV + 1)
                                  Else:
                                      PCLK = selected PLL directly"""
            },
        }
    },


    "PMU_JPEG_CLK_RES_CTRL": {
        "base": 0xD4282800,
        "offset": 0x20,
        "description": "JPEG Clock Reset Control",
        "fields": {
            "JPG_CLK_FC_REQ": {"bits": [15, 15], "description": """Triggers a frequency change
                                                                0: Disable frequency change
                                                                1: enable frequency change"""},
            "JPG_CLK_DIV": {"bits": [7, 5], "description": "isp_clk = JPEG_CLK_DIV / (this field +1). Only applicable for clock source 0~3 "},
            "JPG_CLK_SEL": {"bits": [4, 2],"description": """000: PLL1_div4_614MHz
                                                             001: PLL1_div6_409MHz
                                                             010: PLL1_div5_491MHz
                                                             011: PLL1_div3_819MHz
                                                             100: PLL1_div2_1228MHz
                                                             101: PLL2_div4_750MHz
                                                             110: PLL2_div3_1000MHz
                                                             111: 0"""},
            "JPG_CLK_EN": {"bits": [1, 1], "description": """Enable JPEG Clock
                                                            0: disable
                                                            1: enable"""},
        }
    },

    "PMU_SDH0_CLK_RES_CTRL": {
        "base": 0xD4282800,
        "offset": 0x54,
        "description": "SDH0 Clock Reset Control",
        "fields": {
        }
    },
    "PMU_SDH1_CLK_RES_CTRL": {
        "base": 0xD4282800,
        "offset": 0x58,
        "description": "SDH1 Clock Reset Control",
        "fields": {
        }
    },
    "PMU_QSPI_CLK_RES_CTRL": {
        "base": 0xD4282800,
        "offset": 0x60,
        "description": "QSPI Clock Reset Control",
        "fields": {
        }
    },
    "PMU_VPU_CLK_RES_CTRL": {
        "base": 0xD4282800,
        "offset": 0xA4,
        "description": "VPU Clock Reset Control",
        "fields": {
            "VPU_CLK_FC_REQ": {"bits": [21, 21], "description": """Triggers a frequency change
                                                                0: Disable frequency change
                                                                1: enable frequency change"""},
            "VPU_CLK_DIV": {"bits": [15, 13], "description": "VPU_CLK = VPU_CLK_SEL / (this field +1).. Only applicable for clock source 0~3 "},
            "VPU_CLK_SEL": {"bits": [12, 10],"description": """000: PLL1_div4_614MHz
                                                               001: PLL1_div5_491MHz
                                                               010: PLL1_div3_819MHz
                                                               011: PLL1_div6_409MHz
                                                               100: PLL3_div6
                                                               101: PLL2_div3
                                                               110: PLL2_div4
                                                               111: PLL2_div5"""},
            "VPU_CLK_EN": {"bits": [3, 3], "description": """Enable VPU Clock
                                                            0: disable
                                                            1: enable"""},
        }
    },
    "PMU_PLL_SEL_STATUS": {
        "base": 0xD4282800,
        "offset": 0xC4,
        "description": "PLL Selection Status",
        "fields": {
            "AP_C1_PLL_SEL": {"bits": [13, 11],"description": """000: 614MHz
                                                                001: 819MHz
                                                                010: 409MHz
                                                                011: 491MHz
                                                                100: 1228MHz
                                                                101: PLL3_DIV3
                                                                110: PLL2_DIV3
                                                                111: PLL3_DIV2"""},
            "AP_C0_PLL_SEL": {"bits": [10, 8],"description": """000: 614MHz
                                                                001: 819MHz
                                                                010: 409MHz
                                                                011: 491MHz
                                                                100: 1228MHz
                                                                101: PLL3_DIV3
                                                                110: PLL2_DIV3
                                                                111: PLL3_DIV2"""},
            "ACLK_PLL_SEL": {"bits": [7, 6], "description": """ACLK PLL Selection
                                                                0: 249 MHz
                                                                1: 312 MHz"""},
        }
    },
    "PMU_GPU_CLK_RES_CTRL": {
        "base": 0xD4282800,
        "offset": 0xCC,
        "description": "GPU Clock Reset Control",
        "fields": {
            "GPU_CLK_SEL": {"bits": [20, 18],"description": """000: PLL1_div4_614MHz
                                                               001: PLL1_div5_491MHz
                                                               010: PLL1_div3_819MHz
                                                               011: PLL1_div6_409MHz
                                                               100: PLL3_div6
                                                               101: PLL2_div3
                                                               110: PLL2_div4
                                                               111: PLL2_div5"""},
            "GPU_CLK_FC_REQ": {"bits": [15, 15], "description": "Triggers a frequency change"},
            "GPU_CLK_DIV": {"bits": [14, 12], "description": "GPU_fnc_clk = GPU_CLK_SEL / (this field +1). Only applicable for clock source 0, 1, 2 "},
            "GPU_CLK_EN": {"bits": [4, 4], "description": """Enable GPU Clock
                                                            0: disable
                                                            1: enable"""},
        }
    },
    "PMU_SDH2_CLK_RES_CTRL": {
        "base": 0xD4282800,
        "offset": 0xE0,
        "description": "SDH2 Clock Reset Control",
        "fields": {
        }
    },
    "PMUA_MC_CTRL": {
        "base": 0xD4282800,
        "offset": 0xE8,
        "description": "Memory Controller AHB Register",
        "fields": {
            "MC_AHBCLK_EN": {"bits": [1, 1], "description": """0: disable
                                                                1 = enable"""},
        }
    },
    "DFC_AP": {
        "base": 0xD4282800,
        "offset": 0x180,
        "description": "Dynamic Frequency Control - AP",
        "fields": {
            "LEVEL": {"bits": [3, 1], "description": "DCLK Frequency Level in Active Mode "},
        }
    },
    "DFC_STATUS": {
        "base": 0xD4282800,
        "offset": 0x188,
        "description": "DFC Status",
        "fields": {
            "TFL": {"bits": [3, 1], "description": "Target Frequency Level of DCLK"},
            "CFL": {"bits": [3, 1], "description": "Current Frequency Level of DCLK"},
            "DFC_STATUS": {"bits": [0, 0], "description": """It indicates the status of DFC for the DCLK, specifying whether a DFC is active
                                                            0: No ongoing DFC
                                                            1: A DFC is currently active"""},
        }
    },
    "DFC_LEVEL_0": {
        "base": 0xD4282800,
        "offset": 0x190,
        "description": "DFC Level 0 Configuration",
        "fields": {
            "PLL_CLK_DIV": {"bits": [15, 14], "description": """PLL Clock Divider Configuration
                                                                11: DIV4
                                                                10: DIV3
                                                                01: DIV2
                                                                b00: DIV1"""},
            "DCLK_POSTDIV": {"bits": [13, 13], "description": """0: no division
                                                                1: divide clk by 2"""},
            "PLL_BYPASS_SEL": {"bits": [12, 12], "description": """0: enable pll
                                                                1: bypass PLL"""},
            "PLL_SEL": {"bits": [8, 8], "description": """PLL Selection; only effective when FREQ_PLL_CHG_MODE = 1
                                                        0: PLL2
                                                        1: PLL1; """},
            "PLL_SEL_OFF": {"bits": [7, 7], "description": """PLL Selection (for disabling Unused PLL); only effective when FREQ_PLL_CHG_MODE = 1
                                                            0: don't disable PLL
                                                            1: disable unused PLL"""},
            "MC_TABLE_NUM_HF": {"bits": [6, 6], "description": "The target frequency is high frequency"},
            "MC_TABLE_NUM_TIMING": {"bits": [5, 4], "description": "Specifies the target timing table number"},
            "VL": {"bits": [3, 0], "description": "Required Voltage Level"},
        }
    },
    "DFC_LEVEL_1": {
        "base": 0xD4282800,
        "offset": 0x194,
        "description": "DFC Level 1 Configuration",
        "fields": {
            "PLL_CLK_DIV": {"bits": [15, 14], "description": """PLL Clock Divider Configuration
                                                                11: DIV4
                                                                10: DIV3
                                                                01: DIV2
                                                                b00: DIV1"""},
            "DCLK_POSTDIV": {"bits": [13, 13], "description": """0: no division
                                                                1: divide clk by 2"""},
            "PLL_BYPASS_SEL": {"bits": [12, 12], "description": """0: enable pll
                                                                1: bypass PLL"""},
            "PLL_SEL": {"bits": [8, 8], "description": """PLL Selection; only effective when FREQ_PLL_CHG_MODE = 1
                                                        0: PLL2
                                                        1: PLL1; """},
            "PLL_SEL_OFF": {"bits": [7, 7], "description": """PLL Selection (for disabling Unused PLL); only effective when FREQ_PLL_CHG_MODE = 1
                                                            0: don't disable PLL
                                                            1: disable unused PLL"""},
            "MC_TABLE_NUM_HF": {"bits": [6, 6], "description": "The target frequency is high frequency"},
            "MC_TABLE_NUM_TIMING": {"bits": [5, 4], "description": "Specifies the target timing table number"},
            "VL": {"bits": [3, 0], "description": "Required Voltage Level"},
        }
    },
    "DFC_LEVEL_2": {
        "base": 0xD4282800,
        "offset": 0x198,
        "description": "DFC Level 2 Configuration",
        "fields": {
            "PLL_CLK_DIV": {"bits": [15, 14], "description": """PLL Clock Divider Configuration
                                                                11: DIV4
                                                                10: DIV3
                                                                01: DIV2
                                                                b00: DIV1"""},
            "DCLK_POSTDIV": {"bits": [13, 13], "description": """0: no division
                                                                1: divide clk by 2"""},
            "PLL_BYPASS_SEL": {"bits": [12, 12], "description": """0: enable pll
                                                                1: bypass PLL"""},
            "PLL_SEL": {"bits": [8, 8], "description": """PLL Selection; only effective when FREQ_PLL_CHG_MODE = 1
                                                        0: PLL2
                                                        1: PLL1; """},
            "PLL_SEL_OFF": {"bits": [7, 7], "description": """PLL Selection (for disabling Unused PLL); only effective when FREQ_PLL_CHG_MODE = 1
                                                            0: don't disable PLL
                                                            1: disable unused PLL"""},
            "MC_TABLE_NUM_HF": {"bits": [6, 6], "description": "The target frequency is high frequency"},
            "MC_TABLE_NUM_TIMING": {"bits": [5, 4], "description": "Specifies the target timing table number"},
            "VL": {"bits": [3, 0], "description": "Required Voltage Level"},
        }
    },
    "DFC_LEVEL_3": {
        "base": 0xD4282800,
        "offset": 0x19C,
        "description": "DFC Level 3 Configuration",
        "fields": {
            "PLL_CLK_DIV": {"bits": [15, 14], "description": """PLL Clock Divider Configuration
                                                                11: DIV4
                                                                10: DIV3
                                                                01: DIV2
                                                                b00: DIV1"""},
            "DCLK_POSTDIV": {"bits": [13, 13], "description": """0: no division
                                                                1: divide clk by 2"""},
            "PLL_BYPASS_SEL": {"bits": [12, 12], "description": """0: enable pll
                                                                1: bypass PLL"""},
            "PLL_SEL": {"bits": [8, 8], "description": """PLL Selection; only effective when FREQ_PLL_CHG_MODE = 1
                                                        0: PLL2
                                                        1: PLL1; """},
            "PLL_SEL_OFF": {"bits": [7, 7], "description": """PLL Selection (for disabling Unused PLL); only effective when FREQ_PLL_CHG_MODE = 1
                                                            0: don't disable PLL
                                                            1: disable unused PLL"""},
            "MC_TABLE_NUM_HF": {"bits": [6, 6], "description": "The target frequency is high frequency"},
            "MC_TABLE_NUM_TIMING": {"bits": [5, 4], "description": "Specifies the target timing table number"},
            "VL": {"bits": [3, 0], "description": "Required Voltage Level"},
        }
    },
    "DFC_LEVEL_4": {
        "base": 0xD4282800,
        "offset": 0x1A0,
        "description": "DFC Level 4 Configuration",
        "fields": {
            "PLL_CLK_DIV": {"bits": [15, 14], "description": """PLL Clock Divider Configuration
                                                                11: DIV4
                                                                10: DIV3
                                                                01: DIV2
                                                                b00: DIV1"""},
            "DCLK_POSTDIV": {"bits": [13, 13], "description": """0: no division
                                                                1: divide clk by 2"""},
            "PLL_BYPASS_SEL": {"bits": [12, 12], "description": """0: enable pll
                                                                1: bypass PLL"""},
            "PLL_SEL": {"bits": [8, 8], "description": """PLL Selection; only effective when FREQ_PLL_CHG_MODE = 1
                                                        0: PLL2
                                                        1: PLL1; """},
            "PLL_SEL_OFF": {"bits": [7, 7], "description": """PLL Selection (for disabling Unused PLL); only effective when FREQ_PLL_CHG_MODE = 1
                                                            0: don't disable PLL
                                                            1: disable unused PLL"""},
            "MC_TABLE_NUM_HF": {"bits": [6, 6], "description": "The target frequency is high frequency"},
            "MC_TABLE_NUM_TIMING": {"bits": [5, 4], "description": "Specifies the target timing table number"},
            "VL": {"bits": [3, 0], "description": "Required Voltage Level"},
        }
    },
    "DFC_LEVEL_5": {
        "base": 0xD4282800,
        "offset": 0x1A4,
        "description": "DFC Level 5 Configuration",
        "fields": {
            "PLL_CLK_DIV": {"bits": [15, 14], "description": """PLL Clock Divider Configuration
                                                                11: DIV4
                                                                10: DIV3
                                                                01: DIV2
                                                                b00: DIV1"""},
            "DCLK_POSTDIV": {"bits": [13, 13], "description": """0: no division
                                                                1: divide clk by 2"""},
            "PLL_BYPASS_SEL": {"bits": [12, 12], "description": """0: enable pll
                                                                1: bypass PLL"""},
            "PLL_SEL": {"bits": [8, 8], "description": """PLL Selection; only effective when FREQ_PLL_CHG_MODE = 1
                                                        0: PLL2
                                                        1: PLL1; """},
            "PLL_SEL_OFF": {"bits": [7, 7], "description": """PLL Selection (for disabling Unused PLL); only effective when FREQ_PLL_CHG_MODE = 1
                                                            0: don't disable PLL
                                                            1: disable unused PLL"""},
            "MC_TABLE_NUM_HF": {"bits": [6, 6], "description": "The target frequency is high frequency"},
            "MC_TABLE_NUM_TIMING": {"bits": [5, 4], "description": "Specifies the target timing table number"},
            "VL": {"bits": [3, 0], "description": "Required Voltage Level"},
        }
    },
    "DFC_LEVEL_6": {
        "base": 0xD4282800,
        "offset": 0x1A8,
        "description": "DFC Level 6 Configuration",
        "fields": {
            "PLL_CLK_DIV": {"bits": [15, 14], "description": """PLL Clock Divider Configuration
                                                                11: DIV4
                                                                10: DIV3
                                                                01: DIV2
                                                                b00: DIV1"""},
            "DCLK_POSTDIV": {"bits": [13, 13], "description": """0: no division
                                                                1: divide clk by 2"""},
            "PLL_BYPASS_SEL": {"bits": [12, 12], "description": """0: enable pll
                                                                1: bypass PLL"""},
            "PLL_SEL": {"bits": [8, 8], "description": """PLL Selection; only effective when FREQ_PLL_CHG_MODE = 1
                                                        0: PLL2
                                                        1: PLL1; """},
            "PLL_SEL_OFF": {"bits": [7, 7], "description": """PLL Selection (for disabling Unused PLL); only effective when FREQ_PLL_CHG_MODE = 1
                                                            0: don't disable PLL
                                                            1: disable unused PLL"""},
            "MC_TABLE_NUM_HF": {"bits": [6, 6], "description": "The target frequency is high frequency"},
            "MC_TABLE_NUM_TIMING": {"bits": [5, 4], "description": "Specifies the target timing table number"},
            "VL": {"bits": [3, 0], "description": "Required Voltage Level"},
        }
    },
    "DFC_LEVEL_7": {
        "base": 0xD4282800,
        "offset": 0x1AC,
        "description": "DFC Level 7 Configuration",
        "fields": {
            "PLL_CLK_DIV": {"bits": [15, 14], "description": """PLL Clock Divider Configuration
                                                                11: DIV4
                                                                10: DIV3
                                                                01: DIV2
                                                                b00: DIV1"""},
            "DCLK_POSTDIV": {"bits": [13, 13], "description": """0: no division
                                                                1: divide clk by 2"""},
            "PLL_BYPASS_SEL": {"bits": [12, 12], "description": """0: enable pll
                                                                1: bypass PLL"""},
            "PLL_SEL": {"bits": [8, 8], "description": """PLL Selection; only effective when FREQ_PLL_CHG_MODE = 1
                                                        0: PLL2
                                                        1: PLL1; """},
            "PLL_SEL_OFF": {"bits": [7, 7], "description": """PLL Selection (for disabling Unused PLL); only effective when FREQ_PLL_CHG_MODE = 1
                                                            0: don't disable PLL
                                                            1: disable unused PLL"""},
            "MC_TABLE_NUM_HF": {"bits": [6, 6], "description": "The target frequency is high frequency"},
            "MC_TABLE_NUM_TIMING": {"bits": [5, 4], "description": "Specifies the target timing table number"},
            "VL": {"bits": [3, 0], "description": "Required Voltage Level"},
        }
    },
    "PMUA_ACLK_CTRL": {
        "base": 0xD4282800,
        "offset": 0x388,
        "description": "ACLK Control",
        "fields": {
            "ACLK_FC_REQ": {"bits": [0, 0], "description": """Enable a frequency change
                                                                0: Disable
                                                                1: Enable"""},
            "ACLK_DIV": {"bits": [2, 1], "description": "ACLK=<ACLK_SEL>/(<ACLK_DIV>+1) "},
            "ACLK_SEL": {"bits": [0, 0], "description": """ACLK Frequency
                                                            0: 249 MHz
                                                            1: 312 MHz"""},
        }
    },
    "PMUA_CPU_C0_CLK_CTRL": {
        "base": 0xD4282800,
        "offset": 0x38C,
        "description": "CPU Cluster 0 Clock Control",
        "fields": {
            "C0_HI_CLK_SEL": {"bits": [13, 13], "description": """CPU cluster0 highest Clock Frequecny Selection. It controls the selection of the highest clock frequency from CPU Cluster 0 based on the configuration of PLL3
                                                                0: PLL3_div2, if PLL3 VCO is 3200M
                                                                1: PLL3_div1, if PLL3 VCO is 1600M"""},
            "C0_CLK_FC_REQ": {"bits": [12, 12], "description": """Enable a frequency change
                                                                0: Disable
                                                                1: Enable"""},
            "C0_TCM_AXI_DIV": {"bits": [11, 9], "description": "C0_TCM_AXI = C0_CORE_CLK / (this field +1)"},            
            "C0_ACE_CLK_DIV": {"bits": [8, 6], "description": "C0_ACE_CLK = C0_CORE_CLK / (this field +1)"},
            "C0_CORE_CLK_DIV": {"bits": [5, 3], "description": "C0_CORE_CLK = Clock Selection / (this field +1)"},
            "C0_CLK_SEL": {"bits": [2, 0], "description": """CPU Cluster0 Clock Selection
                                                            000: PLL1_div4_614MHz
                                                            001: PLL1_div3_819MHz
                                                            010: PLL1_div6_409MHz
                                                            011: PLL1_div5_491MHz
                                                            100: PLL1_div2_1228MHz
                                                            101: PLL3_div3
                                                            110: PLL2_div3_1000MHz
                                                            111: PLL3_div2 if [13]=0, PLL3_div1 if [13]=1"""},
        }
    },
    "PMUA_CPU_C1_CLK_CTRL": {
        "base": 0xD4282800,
        "offset": 0x390,
        "description": "CPU Cluster 1 Clock Control",
        "fields": {
            "C1_HI_CLK_SEL": {"bits": [13, 13], "description": """CPU cluster1 highest Clock Frequecny Selection. It controls the selection of the highest clock frequency from CPU Cluster 0 based on the configuration of PLL3
                                                                0: PLL3_div2, if PLL3 VCO is 3200M
                                                                1: PLL3_div1, if PLL3 VCO is 1600M"""},
            "C1_CLK_FC_REQ": {"bits": [12, 12], "description": """Enable a frequency change
                                                                0: Disable
                                                                1: Enable"""},
            "C1_TCM_AXI_DIV": {"bits": [11, 9], "description": "C1_TCM_AXI = C1_CORE_CLK / (this field +1)"},            
            "C1_ACE_CLK_DIV": {"bits": [8, 6], "description": "C1_ACE_CLK = C1_CORE_CLK / (this field +1)"},
            "C1_CORE_CLK_DIV": {"bits": [5, 3], "description": "C1_CORE_CLK = Clock Selection / (this field +1)"},
            "C1_CLK_SEL": {"bits": [2, 0], "description": """CPU Cluster1 Clock Selection
                                                            000: PLL1_div4_614MHz
                                                            001: PLL1_div3_819MHz
                                                            010: PLL1_div6_409MHz
                                                            011: PLL1_div5_491MHz
                                                            100: PLL1_div2_1228MHz
                                                            101: PLL3_div3
                                                            110: PLL2_div3_1000MHz
                                                            111: PLL3_div2 if [13]=0, PLL3_div1 if [13]=1"""},
        }
    },
}


def categorize_registers():
    """
    Categorize registers into logical groups.
    Returns a dictionary with tab names as keys and register dicts as values.
    """
    tabs = {
        "Info": {},
        "PLL": {},
        "CPU": {},
        "GPU/VPU": {},
        "SDH/QSPI/JPEG": {},
        "DFC": {},
        "MC/ACLK": {},
        "Other": {}
    }
    
    for name, reg_info in REGISTERS.items():
        lname = name.lower()
        if "pll" in lname:
            tabs["PLL"][name] = reg_info
        elif "cpu" in lname or "dm_cc" in lname:
            tabs["CPU"][name] = reg_info
        elif "gpu" in lname or "vpu" in lname:
            tabs["GPU/VPU"][name] = reg_info
        elif any(x in lname for x in ["sdh", "qspi", "jpeg"]):
            tabs["SDH/QSPI/JPEG"][name] = reg_info
        elif "dfc" in lname:
            tabs["DFC"][name] = reg_info
        elif any(x in lname for x in ["mc", "aclk"]):
            tabs["MC/ACLK"][name] = reg_info
        else:
            tabs["Other"][name] = reg_info
    
    return tabs


def get_register_info(reg_name):
    """Get full register information by name."""
    return REGISTERS.get(reg_name)


def extract_field(value, field_info):
    """Extract a field value from a register value."""
    high, low = field_info["bits"]
    mask = ((1 << (high - low + 1)) - 1) << low
    return (value & mask) >> low