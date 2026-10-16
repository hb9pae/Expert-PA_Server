"""Asyncio TCP client for communicating with ser2net connected to SPE Expert PA."""

import asyncio
import logging
import time
from typing import Callable, List, Optional
from expertpa.protocol.codec import (
    build_status_request,
    decode_ack,
    encode_command,
)
from expertpa.protocol.constants import AMP_SYN, Command
from expertpa.protocol.models import (
    AmplifierTelemetry,
    CommandResponse,
    ConnectionStatus,
)
from expertpa.protocol.parser import parse_status_payload
from expertpa.server.config import ServerConfig

logger = logging.getLogger("expertpa.client")


class ExpertPAClient:
    """Asynchronous client connecting to ser2net."""

    def __init__(self, config: ServerConfig):
        self.config = config
        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None
        self._running = False
        self._poll_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()

        # Telemetry state
        self.latest_telemetry: Optional[AmplifierTelemetry] = None
        self.listeners: List[Callable[[AmplifierTelemetry], None]] = []

        # Diagnostics & Connection Stats
        self.connected = False
        self.reconnect_attempts = 0
        self.total_rx_packets = 0
        self.total_tx_packets = 0
        self.last_packet_time: Optional[float] = None

    def add_telemetry_listener(self, callback: Callable[[AmplifierTelemetry], None]):
        """Register a callback for telemetry updates."""
        if callback not in self.listeners:
            self.listeners.append(callback)

    def remove_telemetry_listener(self, callback: Callable[[AmplifierTelemetry], None]):
        """Unregister a telemetry callback."""
        if callback in self.listeners:
            self.listeners.remove(callback)

    def _notify_listeners(self, telemetry: AmplifierTelemetry):
        for listener in self.listeners:
            try:
                res = listener(telemetry)
                if asyncio.iscoroutine(res):
                    asyncio.create_task(res)
            except Exception as err:
                logger.error(f"Error in telemetry listener: {err}")

    def get_connection_status(self) -> ConnectionStatus:
        """Return diagnostic connection status."""
        return ConnectionStatus(
            connected=self.connected,
            host=self.config.ser2net_host,
            port=self.config.ser2net_port,
            reconnect_attempts=self.reconnect_attempts,
            total_rx_packets=self.total_rx_packets,
            total_tx_packets=self.total_tx_packets,
            last_packet_time=self.last_packet_time,
        )

    async def _connect(self) -> bool:
        """Establish TCP connection to ser2net."""
        try:
            logger.info(
                f"Connecting to ser2net at {self.config.ser2net_host}:{self.config.ser2net_port}..."
            )
            self._reader, self._writer = await asyncio.wait_for(
                asyncio.open_connection(
                    self.config.ser2net_host, self.config.ser2net_port
                ),
                timeout=3.0,
            )
            self.connected = True
            logger.info("Successfully connected to SPE Expert PA via ser2net!")
            return True
        except (OSError, asyncio.TimeoutError) as err:
            self.connected = False
            self.reconnect_attempts += 1
            logger.warning(
                f"Failed to connect to {self.config.ser2net_host}:{self.config.ser2net_port}: {err}"
            )
            return False

    async def _disconnect(self):
        """Close active connection."""
        self.connected = False
        if self._writer:
            try:
                self._writer.close()
                await self._writer.wait_closed()
            except Exception:
                pass
            self._writer = None
            self._reader = None

    async def send_command(self, cmd: int | Command, name: str = "") -> CommandResponse:
        """Send a single command to the amplifier and wait for ACK."""
        cmd_val = int(cmd)
        cmd_name = name or (Command(cmd_val).name if cmd_val in Command._value2member_map_ else f"0x{cmd_val:02X}")

        if not self.connected or not self._writer or not self._reader:
            return CommandResponse(
                success=False,
                command_name=cmd_name,
                command_code=cmd_val,
                ack_received=False,
                message="Not connected to amplifier",
            )

        async with self._lock:
            try:
                req_bytes = encode_command(cmd_val)
                self._writer.write(req_bytes)
                await self._writer.drain()
                self.total_tx_packets += 1

                # Wait for ACK response: 6 bytes
                raw_ack = await asyncio.wait_for(
                    self._reader.read(6), timeout=self.config.command_timeout_s
                )
                ack_cmd = decode_ack(raw_ack)

                if ack_cmd == cmd_val:
                    return CommandResponse(
                        success=True,
                        command_name=cmd_name,
                        command_code=cmd_val,
                        ack_received=True,
                        message=f"Command {cmd_name} executed successfully with ACK",
                    )
                else:
                    return CommandResponse(
                        success=False,
                        command_name=cmd_name,
                        command_code=cmd_val,
                        ack_received=False,
                        message=f"Received invalid ACK: {raw_ack.hex()}",
                    )
            except asyncio.TimeoutError:
                return CommandResponse(
                    success=False,
                    command_name=cmd_name,
                    command_code=cmd_val,
                    ack_received=False,
                    message="Timeout waiting for amplifier ACK",
                )
            except Exception as err:
                logger.error(f"Socket error while sending command {cmd_name}: {err}")
                await self._disconnect()
                return CommandResponse(
                    success=False,
                    command_name=cmd_name,
                    command_code=cmd_val,
                    ack_received=False,
                    message=f"Connection error: {err}",
                )

    async def _query_status_once(self) -> Optional[AmplifierTelemetry]:
        """Send status request and read 75-byte response."""
        if not self._writer or not self._reader:
            return None

        # Build status request
        self._writer.write(build_status_request())
        await self._writer.drain()
        self.total_tx_packets += 1

        # Read response frame (75 bytes)
        resp_data = await asyncio.wait_for(self._reader.read(75), timeout=1.0)
        if len(resp_data) >= 71:
            self.total_rx_packets += 1
            self.last_packet_time = time.time()
            telemetry = parse_status_payload(resp_data)
            if telemetry:
                self.latest_telemetry = telemetry
                self._notify_listeners(telemetry)
                return telemetry
        return None

    async def _polling_loop(self):
        """Continuous background loop for status polling and auto-reconnect."""
        while self._running:
            if not self.connected:
                success = await self._connect()
                if not success:
                    await asyncio.sleep(self.config.reconnect_interval_s)
                    continue

            # Poll status with lock
            try:
                async with self._lock:
                    await self._query_status_once()
            except (OSError, asyncio.TimeoutError) as err:
                logger.warning(f"Connection lost during status poll: {err}")
                await self._disconnect()
                await asyncio.sleep(self.config.reconnect_interval_s)
                continue
            except Exception as err:
                logger.error(f"Unexpected error in status loop: {err}")

            await asyncio.sleep(self.config.poll_interval_s)

    async def start(self):
        """Start the background connection and polling service."""
        if self._running:
            return
        self._running = True
        self._poll_task = asyncio.create_task(self._polling_loop())

    async def stop(self):
        """Stop client and disconnect."""
        self._running = False
        if self._poll_task:
            self._poll_task.cancel()
            try:
                await self._poll_task
            except asyncio.CancelledError:
                pass
            self._poll_task = None
        await self._disconnect()
        logger.info("ExpertPAClient stopped")
