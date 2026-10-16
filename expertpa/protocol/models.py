"""Pydantic models for SPE Expert amplifier status and commands."""

import time
from typing import Optional
from pydantic import BaseModel, Field


class AmplifierTelemetry(BaseModel):
    """Complete parsed telemetry from the 67-byte status message."""

    model: str = Field(description="Amplifier model ID, e.g. '20K' or '13K'")
    is_operate: bool = Field(description="True if in OPERATE mode, False if STANDBY")
    operate_mode: str = Field(description="'OPERATE' or 'STANDBY'")
    is_transmitting: bool = Field(description="True if transmitting (TX)")
    tx_mode: str = Field(description="'TX' or 'RX'")
    bank: str = Field(description="Memory bank ('x' for 2K-FA, 'A'/'B' for 1.3K-FA)")
    input_port: int = Field(description="Selected RF input (1 or 2)")
    band_code: str = Field(description="Raw band code, e.g. '00'")
    band_name: str = Field(description="Human-readable band name, e.g. '20m'")
    tx_antenna: int = Field(description="Selected TX antenna port (1 to 6)")
    atu_status: str = Field(description="ATU status: 'AUTO', 'BYPASS', or 'TUNABLE'")
    rx_antenna: str = Field(description="RX antenna designation (e.g. '0r', '3r')")
    power_level: str = Field(description="Power level setting: 'LOW', 'MID', 'MAX'")
    power_out_watts: int = Field(description="Current measured output power in Watts")
    swr_atu: float = Field(description="VSWR before ATU")
    swr_ant: float = Field(description="VSWR of antenna system")
    v_pa: float = Field(description="PA supply voltage in Volts")
    i_pa: float = Field(description="PA current in Amperes")
    temp_upr: int = Field(description="Upper heatsink temperature in °C")
    temp_lwr: int = Field(description="Lower heatsink temperature in °C (0 on 1.3K)")
    temp_cmb: int = Field(description="Combiner temperature in °C (0 on 1.3K)")
    warning_code: str = Field(description="Single-character warning code, 'N' if none")
    warning_text: str = Field(description="Human-readable warning description")
    alarm_code: str = Field(description="Single-character alarm code, 'N' if none")
    alarm_text: str = Field(description="Human-readable alarm description")
    raw_status: Optional[str] = Field(default=None, description="Raw 67-byte payload")
    timestamp: float = Field(default_factory=time.time, description="Unix timestamp of reception")


class CommandRequest(BaseModel):
    """Request payload to send a command to the amplifier."""

    command: str = Field(description="Command name (e.g. 'OPERATE', 'POWER', 'TUNE') or hex code")


class CommandResponse(BaseModel):
    """Result of executing a command."""

    success: bool
    command_name: str
    command_code: int
    ack_received: bool
    message: str


class ConnectionStatus(BaseModel):
    """Status of the connection to ser2net."""

    connected: bool
    host: str
    port: int
    reconnect_attempts: int
    total_rx_packets: int
    total_tx_packets: int
    last_packet_time: Optional[float] = None
