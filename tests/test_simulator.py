"""Tests for the SPE Expert PA hardware simulator."""

import asyncio
import pytest
from expertpa.protocol.codec import build_status_request, decode_ack, encode_command
from expertpa.protocol.constants import Command
from expertpa.protocol.parser import parse_status_payload
from expertpa.simulator.pa_simulator import PASimulator


@pytest.mark.anyio
async def test_simulator_status_and_commands():
    # Start simulator on dynamic port
    sim = PASimulator(host="127.0.0.1", port=22099)
    await sim.start()

    try:
        reader, writer = await asyncio.open_connection("127.0.0.1", 22099)

        # 1. Query initial status
        writer.write(build_status_request())
        await writer.drain()

        resp = await reader.read(75)
        assert len(resp) == 75
        assert resp[:3] == bytes([0xAA, 0xAA, 0xAA])
        assert resp[3] == 0x43

        telemetry = parse_status_payload(resp)
        assert telemetry is not None
        assert telemetry.model == "20K"
        assert telemetry.is_operate is False
        assert telemetry.operate_mode == "STANDBY"
        assert telemetry.power_level == "MID"

        # 2. Send OPERATE command
        writer.write(encode_command(Command.OPERATE))
        await writer.drain()

        ack = await reader.read(6)
        assert decode_ack(ack) == Command.OPERATE

        # 3. Query status again to confirm state transition to OPERATE
        writer.write(build_status_request())
        await writer.drain()

        resp2 = await reader.read(75)
        telemetry2 = parse_status_payload(resp2)
        assert telemetry2 is not None
        assert telemetry2.is_operate is True
        assert telemetry2.operate_mode == "OPERATE"

        # 4. Cycle Power: MID -> MAX
        writer.write(encode_command(Command.POWER))
        await writer.drain()
        ack = await reader.read(6)
        assert decode_ack(ack) == Command.POWER

        writer.write(build_status_request())
        await writer.drain()
        resp3 = await reader.read(75)
        telemetry3 = parse_status_payload(resp3)
        assert telemetry3 is not None
        assert telemetry3.power_level == "MAX"

        writer.close()
        await writer.wait_closed()
    finally:
        await sim.stop()
