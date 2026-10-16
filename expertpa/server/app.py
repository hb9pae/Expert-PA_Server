"""FastAPI application for SPE Expert PA remote monitoring and control."""

import json
import logging
from contextlib import asynccontextmanager
from typing import Dict, List, Optional
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from expertpa.protocol.constants import Command
from expertpa.protocol.models import (
    AmplifierTelemetry,
    CommandRequest,
    CommandResponse,
    ConnectionStatus,
)
from expertpa.server.client import ExpertPAClient
from expertpa.server.config import ServerConfig

logger = logging.getLogger("expertpa.server")

# Friendly command aliases
COMMAND_NAME_MAP: Dict[str, Command] = {
    "operate": Command.OPERATE,
    "power": Command.POWER,
    "input": Command.INPUT,
    "band_plus": Command.BAND_PLUS,
    "band_up": Command.BAND_PLUS,
    "band_minus": Command.BAND_MINUS,
    "band_down": Command.BAND_MINUS,
    "ant": Command.ANTENNA,
    "antenna": Command.ANTENNA,
    "tune": Command.TUNE,
    "l_plus": Command.L_PLUS,
    "l_minus": Command.L_MINUS,
    "c_plus": Command.C_PLUS,
    "c_minus": Command.C_MINUS,
    "display": Command.DISPLAY,
    "cat": Command.CAT,
    "left": Command.LEFT_ARROW,
    "left_arrow": Command.LEFT_ARROW,
    "right": Command.RIGHT_ARROW,
    "right_arrow": Command.RIGHT_ARROW,
    "set": Command.SET,
    "backlight_on": Command.BACKLIGHT_ON,
    "backlight_off": Command.BACKLIGHT_OFF,
    "switch_off": Command.SWITCH_OFF,
    "status": Command.STATUS,
}


class ConnectionManager:
    """Manages active WebSocket telemetry connections."""

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast_json(self, data: dict):
        for connection in list(self.active_connections):
            try:
                await connection.send_json(data)
            except Exception:
                self.disconnect(connection)


def create_app(config: Optional[ServerConfig] = None) -> FastAPI:
    """Create and configure FastAPI instance."""
    app_config = config or ServerConfig()
    pa_client = ExpertPAClient(app_config)
    ws_manager = ConnectionManager()

    # Telemetry listener pushing updates to WebSocket clients
    def on_telemetry(telemetry: AmplifierTelemetry):
        import asyncio

        data = telemetry.model_dump()
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(ws_manager.broadcast_json(data))
        except RuntimeError:
            pass

    pa_client.add_telemetry_listener(on_telemetry)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        logger.info(
            f"Starting Expert PA Server connecting to {app_config.ser2net_host}:{app_config.ser2net_port}..."
        )
        await pa_client.start()
        yield
        logger.info("Stopping Expert PA Server...")
        await pa_client.stop()

    app = FastAPI(
        title="SPE Expert PA Monitoring Server",
        description="Remote Control and Real-Time Monitoring API for SPE Expert Amplifiers",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS support for web clients
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Attach client to app state
    app.state.client = pa_client
    app.state.config = app_config

    @app.get("/api/health")
    async def health():
        return {
            "status": "healthy",
            "ser2net_host": app_config.ser2net_host,
            "ser2net_port": app_config.ser2net_port,
            "connected_to_pa": pa_client.connected,
        }

    @app.get("/api/connection", response_model=ConnectionStatus)
    async def get_connection():
        """Retrieve connection details and packet counters."""
        return pa_client.get_connection_status()

    @app.get("/api/status", response_model=Optional[AmplifierTelemetry])
    async def get_status():
        """Retrieve latest telemetry snapshot."""
        if pa_client.latest_telemetry is None:
            return JSONResponse(
                status_code=503 if not pa_client.connected else 200,
                content={"message": "Waiting for telemetry data from amplifier"},
            )
        return pa_client.latest_telemetry

    @app.post("/api/command/{name}", response_model=CommandResponse)
    async def execute_command(name: str):
        """Execute a named button command (e.g. 'operate', 'power', 'tune', 'band_plus')."""
        canonical_name = name.lower().strip()
        if canonical_name not in COMMAND_NAME_MAP:
            valid = list(COMMAND_NAME_MAP.keys())
            raise HTTPException(
                status_code=400,
                detail=f"Unknown command '{name}'. Valid commands: {valid}",
            )

        cmd = COMMAND_NAME_MAP[canonical_name]
        result = await pa_client.send_command(cmd, name=canonical_name.upper())
        if not result.success:
            raise HTTPException(status_code=502, detail=result.message)
        return result

    @app.post("/api/command/raw/{hex_byte}", response_model=CommandResponse)
    async def execute_raw_command(hex_byte: str):
        """Send a raw 1-byte command (e.g. '0x0D' or '0D')."""
        try:
            val = int(hex_byte, 16)
            if not (0 <= val <= 255):
                raise ValueError()
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid hex byte '{hex_byte}'. Expected format: '0x0D' or '0D'.",
            )

        result = await pa_client.send_command(val, name=f"RAW_0x{val:02X}")
        if not result.success:
            raise HTTPException(status_code=502, detail=result.message)
        return result

    @app.websocket("/ws/telemetry")
    async def websocket_telemetry(websocket: WebSocket):
        """WebSocket endpoint streaming live telemetry JSON updates."""
        await ws_manager.connect(websocket)
        try:
            # Immediately push current state if available
            if pa_client.latest_telemetry:
                await websocket.send_json(pa_client.latest_telemetry.model_dump())

            # Listen for incoming client messages (e.g., ping or commands)
            while True:
                msg = await websocket.receive_text()
                try:
                    payload = json.loads(msg)
                    if isinstance(payload, dict) and "command" in payload:
                        cmd_str = payload["command"]
                        if cmd_str.lower() in COMMAND_NAME_MAP:
                            cmd_enum = COMMAND_NAME_MAP[cmd_str.lower()]
                            res = await pa_client.send_command(cmd_enum, name=cmd_str.upper())
                            await websocket.send_json({"command_result": res.model_dump()})
                except Exception:
                    pass
        except WebSocketDisconnect:
            ws_manager.disconnect(websocket)
        except Exception:
            ws_manager.disconnect(websocket)

    return app
