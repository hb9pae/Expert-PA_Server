"""Frame encoding and decoding for SPE Expert amplifier protocol."""

from typing import Optional
from expertpa.protocol.constants import AMP_SYN, HOST_SYN, Command


def encode_command(cmd: int | Command) -> bytes:
    """Encode a command byte into a host packet.

    Format:
    [0x55, 0x55, 0x55] (3 sync bytes)
    [0x01] (count: 1 data byte follows)
    [cmd] (data byte)
    [cmd] (modulo-256 checksum of single byte is byte itself)
    """
    val = int(cmd) & 0xFF
    return HOST_SYN + bytes([0x01, val, val])


def calculate_status_checksum(data: bytes) -> tuple[int, int]:
    """Calculate 2-byte checksum for the 67-byte status payload.

    CHK byte0 = SUM(DATA0 --> DATA66) % 256
    CHK byte1 = SUM(DATA0 --> DATA66) // 256
    """
    total = sum(data)
    chk0 = total % 256
    chk1 = total // 256
    return chk0, chk1


def decode_ack(packet: bytes) -> Optional[int]:
    """Decode an ACK packet from the amplifier.

    Expected format:
    0xAA 0xAA 0xAA 0x01 <CMD> <CMD>
    Returns the command integer if valid ACK, None otherwise.
    """
    if len(packet) < 6:
        return None
    # Find sync sequence
    idx = packet.find(AMP_SYN)
    if idx == -1 or len(packet) < idx + 6:
        return None

    cnt = packet[idx + 3]
    if cnt != 1:
        return None

    cmd = packet[idx + 4]
    chk = packet[idx + 5]
    if cmd == chk:
        return cmd
    return None


def build_status_request() -> bytes:
    """Build the 0x90 GET STATUS request packet."""
    return encode_command(Command.STATUS)


def build_status_packet(payload_67_ascii: str) -> bytes:
    """Build a complete amplifier status response packet (useful for simulator and tests).

    Format:
    0xAA 0xAA 0xAA (3 sync bytes)
    0x43 (data length = 67 decimal)
    67 ASCII bytes
    CHK0 (sum % 256)
    CHK1 (sum // 256)
    0x0D 0x0A (CR LF)
    Total: 75 bytes
    """
    if len(payload_67_ascii) != 67:
        raise ValueError(f"Payload must be exactly 67 characters, got {len(payload_67_ascii)}")

    raw_data = payload_67_ascii.encode("latin1")
    chk0, chk1 = calculate_status_checksum(raw_data)
    return AMP_SYN + bytes([0x43]) + raw_data + bytes([chk0, chk1, 0x0D, 0x0A])
