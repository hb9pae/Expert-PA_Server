"""Unit tests for SPE Expert amplifier protocol codec and parser."""

import pytest
from expertpa.protocol.codec import (
    build_status_packet,
    build_status_request,
    calculate_status_checksum,
    decode_ack,
    encode_command,
)
from expertpa.protocol.constants import (
    AMP_SYN,
    HOST_SYN,
    Command,
)
from expertpa.protocol.parser import parse_status_payload


def test_encode_command_matches_manual_spec():
    """Verify that command encoding matches exact byte sequences in SPE manual."""
    # From Page 5: OPERATE key code is 0x0D -> 0x55 0x55 0x55 0x01 0x0D 0x0D
    operate_pkt = encode_command(Command.OPERATE)
    assert operate_pkt == bytes([0x55, 0x55, 0x55, 0x01, 0x0D, 0x0D])

    # From Page 8: STATUS request is 0x90 -> 0x55 0x55 0x55 0x01 0x90 0x90
    status_pkt = build_status_request()
    assert status_pkt == bytes([0x55, 0x55, 0x55, 0x01, 0x90, 0x90])

    # Power command 0x0B
    pwr_pkt = encode_command(Command.POWER)
    assert pwr_pkt == bytes([0x55, 0x55, 0x55, 0x01, 0x0B, 0x0B])


def test_decode_ack():
    """Test ACK packet validation."""
    ack = bytes([0xAA, 0xAA, 0xAA, 0x01, 0x0D, 0x0D])
    assert decode_ack(ack) == Command.OPERATE

    # ACK with leading noise in buffer
    stream_with_noise = b"\x00\xff" + bytes([0xAA, 0xAA, 0xAA, 0x01, 0x04, 0x04])
    assert decode_ack(stream_with_noise) == Command.ANTENNA

    # Corrupt checksum in ACK
    bad_ack = bytes([0xAA, 0xAA, 0xAA, 0x01, 0x0D, 0x0E])
    assert decode_ack(bad_ack) is None

    # Too short
    assert decode_ack(bytes([0xAA, 0xAA])) is None


def test_calculate_status_checksum():
    """Verify 2-byte checksum formula."""
    data = b"Hello, World!"
    total = sum(data)
    chk0, chk1 = calculate_status_checksum(data)
    assert chk0 == total % 256
    assert chk1 == total // 256


def test_build_status_packet():
    """Verify complete 75-byte response packet construction."""
    payload = "20K,S,R,x,1,00,1a,0r,L,0000, 0.00, 0.00, 0.0, 0.0, 33,  0,  0,N,N,EXTRA"
    # Ensure exact 67 chars
    payload_67 = payload[:67]
    assert len(payload_67) == 67

    packet = build_status_packet(payload_67)
    assert len(packet) == 75
    assert packet[:3] == AMP_SYN
    assert packet[3] == 0x43
    assert packet[4:71] == payload_67.encode("latin1")
    assert packet[73:] == b"\r\n"


def test_parse_status_clean_string():
    """Parse clean status string and verify fields."""
    raw = "20K,O,T,x,2,05,2b,0r,H,1500, 1.15, 1.20,48.0,32.4,045,042,038,N,N"
    telemetry = parse_status_payload(raw)

    assert telemetry is not None
    assert telemetry.model == "20K"
    assert telemetry.is_operate is True
    assert telemetry.operate_mode == "OPERATE"
    assert telemetry.is_transmitting is True
    assert telemetry.tx_mode == "TX"
    assert telemetry.bank == "x"
    assert telemetry.input_port == 2
    assert telemetry.band_code == "05"
    assert telemetry.band_name == "20m"
    assert telemetry.tx_antenna == 2
    assert telemetry.atu_status == "BYPASS"
    assert telemetry.rx_antenna == "0r"
    assert telemetry.power_level == "MAX"
    assert telemetry.power_out_watts == 1500
    assert telemetry.swr_atu == 1.15
    assert telemetry.swr_ant == 1.20
    assert telemetry.v_pa == 48.0
    assert telemetry.i_pa == 32.4
    assert telemetry.temp_upr == 45
    assert telemetry.temp_lwr == 42
    assert telemetry.temp_cmb == 38
    assert telemetry.warning_code == "N"
    assert telemetry.alarm_code == "N"


def test_parse_status_with_header_and_trailer():
    """Parse status string including raw frame header and trailing checksum."""
    raw = "\xAA\xAA\xAA\x43,20K,S,R,x,1,00,1a,0r,L,0000, 0.00, 0.00, 0.0, 0.0, 33, 0, 0,O,S,%^,\r\n"
    telemetry = parse_status_payload(raw)

    assert telemetry is not None
    assert telemetry.model == "20K"
    assert telemetry.is_operate is False
    assert telemetry.operate_mode == "STANDBY"
    assert telemetry.is_transmitting is False
    assert telemetry.tx_mode == "RX"
    assert telemetry.input_port == 1
    assert telemetry.band_name == "160m"
    assert telemetry.tx_antenna == 1
    assert telemetry.atu_status == "AUTO"
    assert telemetry.warning_code == "O"
    assert "Overheating" in telemetry.warning_text
    assert telemetry.alarm_code == "S"
    assert "SWR Exceeding Limits" in telemetry.alarm_text


def test_parse_invalid_status():
    """Ensure invalid status strings return None gracefully."""
    assert parse_status_payload("") is None
    assert parse_status_payload("too,few,fields") is None
