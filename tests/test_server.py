"""Integration tests for FastAPI Expert PA monitoring server."""

import asyncio
import pytest
from httpx import ASGITransport, AsyncClient
from expertpa.server.app import create_app
from expertpa.server.config import ServerConfig
from expertpa.simulator.pa_simulator import PASimulator


@pytest.mark.anyio
async def test_server_with_simulator():
    test_port = 22098

    # 1. Start PA Simulator
    simulator = PASimulator(host="127.0.0.1", port=test_port)
    await simulator.start()

    config = ServerConfig(
        ser2net_host="127.0.0.1",
        ser2net_port=test_port,
        poll_interval_ms=50,
        reconnect_interval_s=0.2,
        command_timeout_s=0.5,
    )
    app = create_app(config)
    pa_client = app.state.client

    try:
        await pa_client.start()

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            # Wait for connection and first telemetry
            for _ in range(25):
                res = await client.get("/api/connection")
                data = res.json()
                if data.get("connected") and data.get("total_rx_packets", 0) > 0:
                    break
                await asyncio.sleep(0.05)

            # 2. Check health endpoint
            health_resp = await client.get("/api/health")
            assert health_resp.status_code == 200
            health_data = health_resp.json()
            assert health_data["status"] == "healthy"
            assert health_data["connected_to_pa"] is True

            # 3. Check status endpoint
            status_resp = await client.get("/api/status")
            assert status_resp.status_code == 200
            status_data = status_resp.json()
            assert status_data["model"] == "20K"
            assert status_data["is_operate"] is False
            assert status_data["operate_mode"] == "STANDBY"
            assert status_data["power_level"] == "MID"

            # 4. Send OPERATE command
            cmd_resp = await client.post("/api/command/operate")
            assert cmd_resp.status_code == 200
            cmd_data = cmd_resp.json()
            assert cmd_data["success"] is True
            assert cmd_data["ack_received"] is True
            assert cmd_data["command_code"] == 13

            # Allow poll cycle to refresh status
            await asyncio.sleep(0.1)

            status_resp2 = await client.get("/api/status")
            assert status_resp2.status_code == 200
            assert status_resp2.json()["is_operate"] is True
            assert status_resp2.json()["operate_mode"] == "OPERATE"

            # 5. Cycle Power level
            pwr_resp = await client.post("/api/command/power")
            assert pwr_resp.status_code == 200
            assert pwr_resp.json()["success"] is True

            await asyncio.sleep(0.1)
            status_resp3 = await client.get("/api/status")
            assert status_resp3.json()["power_level"] == "MAX"

            # 6. Test invalid command error handling
            err_resp = await client.post("/api/command/non_existent_command")
            assert err_resp.status_code == 400

            # 7. Test raw hex command (e.g. 0x01 = INPUT)
            raw_resp = await client.post("/api/command/raw/0x01")
            assert raw_resp.status_code == 200
            assert raw_resp.json()["command_code"] == 1
    finally:
        await pa_client.stop()
        await simulator.stop()


@pytest.mark.anyio
async def test_websocket_manager_broadcast():
    from expertpa.server.app import ConnectionManager
    from unittest.mock import AsyncMock

    manager = ConnectionManager()
    mock_ws = AsyncMock()
    await manager.connect(mock_ws)

    test_data = {"model": "20K", "operate": True}
    await manager.broadcast_json(test_data)
    mock_ws.send_json.assert_awaited_once_with(test_data)

    manager.disconnect(mock_ws)
    assert len(manager.active_connections) == 0

