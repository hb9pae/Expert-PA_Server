"""Status packet parser for SPE Expert amplifiers."""

import re
import time
from typing import Optional
from expertpa.protocol.constants import (
    ALARM_MAP,
    ATU_STATUS_MAP,
    BAND_MAP,
    POWER_LEVEL_MAP,
    WARNING_MAP,
)
from expertpa.protocol.models import AmplifierTelemetry


def _safe_int(val: str, default: int = 0) -> int:
    """Parse integer, removing spaces and non-numeric chars."""
    clean = re.sub(r"[^\d\-]", "", val.strip())
    try:
        return int(clean) if clean else default
    except ValueError:
        return default


def _safe_float(val: str, default: float = 0.0) -> float:
    """Parse float, handling underscores and spaces."""
    clean = val.strip().replace("_", "").replace(" ", "")
    try:
        return float(clean) if clean else default
    except ValueError:
        return default


def parse_status_payload(raw_input: str | bytes) -> Optional[AmplifierTelemetry]:
    """Parse a status message into an AmplifierTelemetry model.

    Can accept:
    - Raw bytes with 0xAA 0xAA 0xAA prefix
    - Decoded string with or without header/trailer
    """
    if isinstance(raw_input, bytes):
        # Decode latin1 so all bytes are preserved
        text = raw_input.decode("latin1", errors="ignore")
    else:
        text = str(raw_input)

    parts = text.split(",")
    if len(parts) < 19:
        return None

    # Find the offset of the model identifier (20K, 13K, 15K, 1K)
    offset = None
    for idx, p in enumerate(parts):
        token = p.strip()
        if token in ("20K", "13K", "15K", "1K") or token.endswith("K"):
            offset = idx
            break

    if offset is None:
        # Fallback: if at least 19 fields, assume offset 0 or 1
        if len(parts) >= 20 and parts[1].strip() in ("20K", "13K", "15K"):
            offset = 1
        elif len(parts) >= 19:
            offset = 0
        else:
            return None

    if len(parts) < offset + 19:
        return None

    try:
        model = parts[offset].strip()
        op_char = parts[offset + 1].strip().upper()
        tx_char = parts[offset + 2].strip().upper()
        bank = parts[offset + 3].strip()
        input_port = _safe_int(parts[offset + 4], default=1)
        band_code = parts[offset + 5].strip()
        tx_ant_raw = parts[offset + 6].strip()
        rx_ant = parts[offset + 7].strip()
        p_level_raw = parts[offset + 8].strip().upper()
        p_out_raw = parts[offset + 9].strip()
        swr_atu_raw = parts[offset + 10].strip()
        swr_ant_raw = parts[offset + 11].strip()
        v_pa_raw = parts[offset + 12].strip()
        i_pa_raw = parts[offset + 13].strip()
        temp_upr_raw = parts[offset + 14].strip()
        temp_lwr_raw = parts[offset + 15].strip()
        temp_cmb_raw = parts[offset + 16].strip()
        warn_char = parts[offset + 17].strip().upper()
        alarm_char = parts[offset + 18].strip().upper()

        # Parse antenna and ATU
        # Format usually: '1a', '2b', '3t'
        tx_ant_num = 1
        atu_code = "a"
        if len(tx_ant_raw) >= 1 and tx_ant_raw[0].isdigit():
            tx_ant_num = int(tx_ant_raw[0])
        if len(tx_ant_raw) >= 2:
            atu_code = tx_ant_raw[1].lower()

        atu_status = ATU_STATUS_MAP.get(atu_code, "AUTO")

        is_operate = op_char == "O"
        operate_mode = "OPERATE" if is_operate else "STANDBY"

        is_transmitting = tx_char == "T"
        tx_mode = "TX" if is_transmitting else "RX"

        band_name = BAND_MAP.get(band_code, f"{band_code}?")
        power_level = POWER_LEVEL_MAP.get(p_level_raw, "LOW")

        warning_text = WARNING_MAP.get(warn_char, f"Warning {warn_char}")
        alarm_text = ALARM_MAP.get(alarm_char, f"Alarm {alarm_char}")

        return AmplifierTelemetry(
            model=model,
            is_operate=is_operate,
            operate_mode=operate_mode,
            is_transmitting=is_transmitting,
            tx_mode=tx_mode,
            bank=bank,
            input_port=input_port,
            band_code=band_code,
            band_name=band_name,
            tx_antenna=tx_ant_num,
            atu_status=atu_status,
            rx_antenna=rx_ant,
            power_level=power_level,
            power_out_watts=_safe_int(p_out_raw),
            swr_atu=_safe_float(swr_atu_raw),
            swr_ant=_safe_float(swr_ant_raw),
            v_pa=_safe_float(v_pa_raw),
            i_pa=_safe_float(i_pa_raw),
            temp_upr=_safe_int(temp_upr_raw),
            temp_lwr=_safe_int(temp_lwr_raw),
            temp_cmb=_safe_int(temp_cmb_raw),
            warning_code=warn_char,
            warning_text=warning_text,
            alarm_code=alarm_char,
            alarm_text=alarm_text,
            raw_status=text.strip(),
            timestamp=time.time(),
        )
    except Exception:
        return None
