"""SPE Expert Amplifier Protocol Constants.

Covers Expert 2K-FA, 1.5K-FA, and 1.3K-FA amplifiers.
Derived from SPE Application Programmer's Guide Rev 1.1 and Expert 2K-FA User Manual Rev 3.0.
"""

from enum import IntEnum

# Sync sequences
HOST_SYN = bytes([0x55, 0x55, 0x55])
AMP_SYN = bytes([0xAA, 0xAA, 0xAA])

# Length byte for Status response (67 bytes)
STATUS_DATA_LEN = 0x43  # 67 decimal


class Command(IntEnum):
    """User commands supported by the Expert amplifiers."""

    INPUT = 0x01
    BAND_MINUS = 0x02
    BAND_PLUS = 0x03
    ANTENNA = 0x04
    L_MINUS = 0x05
    L_PLUS = 0x06
    C_MINUS = 0x07
    C_PLUS = 0x08
    TUNE = 0x09
    SWITCH_OFF = 0x0A
    POWER = 0x0B
    DISPLAY = 0x0C
    OPERATE = 0x0D
    CAT = 0x0E
    LEFT_ARROW = 0x0F
    RIGHT_ARROW = 0x10
    SET = 0x11
    BACKLIGHT_ON = 0x82
    BACKLIGHT_OFF = 0x83
    STATUS = 0x90


# Band index to human-readable amateur radio band
BAND_MAP: dict[str, str] = {
    "00": "160m",
    "01": "80m",
    "02": "60m",
    "03": "40m",
    "04": "30m",
    "05": "20m",
    "06": "17m",
    "07": "15m",
    "08": "12m",
    "09": "10m",
    "10": "6m",
    "11": "4m",
}

# Warning code mappings (Table Page 10)
WARNING_MAP: dict[str, str] = {
    "N": "No Warnings",
    "M": "Alarm Amplifier",
    "A": "No Selected Antenna",
    "S": "SWR Antenna",
    "B": "No Valid Band",
    "P": "Power Limit Exceeded",
    "O": "Overheating",
    "Y": "ATU Not Available",
    "W": "Tuning With No Power",
    "K": "ATU Bypassed",
    "R": "Power Switch Held by Remote",
    "T": "Combiner Overheating",
    "C": "Combiner Fault",
}

# Alarm / Protection code mappings (Table Page 10)
ALARM_MAP: dict[str, str] = {
    "N": "No Alarms",
    "S": "SWR Exceeding Limits",
    "A": "Amplifier Protection",
    "D": "Input Overdriving",
    "H": "Excess Overheating",
    "C": "Combiner Fault",
}

# Operating state mappings
OPERATE_STATE_MAP = {
    "O": "OPERATE",
    "S": "STANDBY",
}

TX_STATE_MAP = {
    "T": "TX",
    "R": "RX",
}

POWER_LEVEL_MAP = {
    "L": "LOW",
    "M": "MID",
    "H": "MAX",
}

ATU_STATUS_MAP = {
    "a": "AUTO",
    "b": "BYPASS",
    "t": "TUNABLE",
}
