"""Expert PA Protocol Package."""

from expertpa.protocol.codec import (
    build_status_packet,
    build_status_request,
    calculate_status_checksum,
    decode_ack,
    encode_command,
)
from expertpa.protocol.constants import (
    ALARM_MAP,
    AMP_SYN,
    ATU_STATUS_MAP,
    BAND_MAP,
    HOST_SYN,
    POWER_LEVEL_MAP,
    STATUS_DATA_LEN,
    WARNING_MAP,
    Command,
)
from expertpa.protocol.models import (
    AmplifierTelemetry,
    CommandRequest,
    CommandResponse,
    ConnectionStatus,
)
from expertpa.protocol.parser import parse_status_payload

__all__ = [
    "Command",
    "HOST_SYN",
    "AMP_SYN",
    "STATUS_DATA_LEN",
    "BAND_MAP",
    "WARNING_MAP",
    "ALARM_MAP",
    "POWER_LEVEL_MAP",
    "ATU_STATUS_MAP",
    "AmplifierTelemetry",
    "CommandRequest",
    "CommandResponse",
    "ConnectionStatus",
    "encode_command",
    "decode_ack",
    "calculate_status_checksum",
    "build_status_request",
    "build_status_packet",
    "parse_status_payload",
]
