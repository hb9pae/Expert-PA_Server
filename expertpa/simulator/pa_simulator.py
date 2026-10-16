"""SPE Expert PA Hardware Simulator over TCP (mimics ser2net /dev/ttyUSB0)."""

import asyncio
import logging
from typing import Optional
from expertpa.protocol.codec import build_status_packet, calculate_status_checksum
from expertpa.protocol.constants import AMP_SYN, HOST_SYN, Command

logger = logging.getLogger("expertpa.simulator")


class PASimulator:
    """Simulates an SPE Expert 2K-FA / 1.3K-FA amplifier over TCP socket."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 22000,
        model: str = "20K",
    ):
        self.host = host
        self.port = port
        self.model = model

        # Internal simulated PA state
        self.is_powered_on = True
        self.is_operate = False  # False = STANDBY, True = OPERATE
        self.is_tx = False  # False = RX, True = TX
        self.bank = "x"  # 'x' for 2K-FA
        self.input_port = 1  # 1 or 2
        self.band_idx = 5  # 5 = 20m default
        self.tx_antenna = 1  # 1 to 6
        self.atu_mode = "a"  # 'a' = auto, 'b' = bypass, 't' = tunable
        self.rx_antenna = "0r"
        self.power_level = "M"  # 'L', 'M', 'H'
        self.warning_code = "N"
        self.alarm_code = "N"
        self.backlight = True

        # Telemetry values
        self.temp_upr = 33
        self.temp_lwr = 31
        self.temp_cmb = 29
        self.custom_power_out: Optional[int] = None
        self.custom_swr: Optional[float] = None

        self._server: Optional[asyncio.Server] = None
        self._running = False

    @property
    def band_code(self) -> str:
        return f"{self.band_idx:02d}"

    def build_67byte_status_payload(self) -> str:
        """Construct the 67-byte payload conforming to SPE specifications."""
        op_char = "O" if self.is_operate else "S"
        tx_char = "T" if self.is_tx else "R"

        # Output power and SWR depending on TX/RX
        if self.is_tx:
            if self.custom_power_out is not None:
                p_out = self.custom_power_out
            else:
                p_out = 1500 if self.power_level == "H" else (1000 if self.power_level == "M" else 500)
            swr_atu = self.custom_swr if self.custom_swr is not None else 1.15
            swr_ant = swr_atu + 0.05
            v_pa = 48.0 if self.power_level == "H" else (35.0 if self.power_level == "M" else 30.0)
            i_pa = round(p_out / max(v_pa, 1.0) * 1.05, 1)
        else:
            p_out = 0
            swr_atu = 0.0
            swr_ant = 0.0
            v_pa = 0.0
            i_pa = 0.0

        p_out_str = f"{p_out:04d}"
        swr_atu_str = f"{swr_atu:5.2f}"
        swr_ant_str = f"{swr_ant:5.2f}"
        v_pa_str = f"{v_pa:4.1f}"
        i_pa_str = f"{i_pa:4.1f}"
        t_upr_str = f"{self.temp_upr:3d}"
        t_lwr_str = f"{self.temp_lwr:3d}"
        t_cmb_str = f"{self.temp_cmb:3d}"
        tx_ant_atu = f"{self.tx_antenna}{self.atu_mode}"

        fields = [
            "",  # Leading comma
            self.model,
            op_char,
            tx_char,
            self.bank,
            str(self.input_port),
            self.band_code,
            tx_ant_atu,
            self.rx_antenna,
            self.power_level,
            p_out_str,
            swr_atu_str,
            swr_ant_str,
            v_pa_str,
            i_pa_str,
            t_upr_str,
            t_lwr_str,
            t_cmb_str,
            self.warning_code,
            self.alarm_code,
            "",  # Trailing comma
        ]
        payload = ",".join(fields)
        if len(payload) != 67:
            # Safety adjustment if formatting shifted
            payload = payload.ljust(67)[:67]
        return payload

    def handle_command(self, cmd_byte: int) -> bytes:
        """Process incoming command byte and return ACK response."""
        logger.info(f"Simulator received command: 0x{cmd_byte:02X}")

        if cmd_byte == Command.OPERATE:
            self.is_operate = not self.is_operate
        elif cmd_byte == Command.POWER:
            levels = ["L", "M", "H"]
            cur = levels.index(self.power_level) if self.power_level in levels else 0
            self.power_level = levels[(cur + 1) % len(levels)]
        elif cmd_byte == Command.INPUT:
            self.input_port = 2 if self.input_port == 1 else 1
        elif cmd_byte == Command.BAND_PLUS:
            self.band_idx = (self.band_idx + 1) % 11
        elif cmd_byte == Command.BAND_MINUS:
            self.band_idx = (self.band_idx - 1) % 11
        elif cmd_byte == Command.ANTENNA:
            self.tx_antenna = (self.tx_antenna % 6) + 1
        elif cmd_byte == Command.TUNE:
            modes = ["a", "b", "t"]
            idx = modes.index(self.atu_mode) if self.atu_mode in modes else 0
            self.atu_mode = modes[(idx + 1) % len(modes)]
        elif cmd_byte == Command.BACKLIGHT_ON:
            self.backlight = True
        elif cmd_byte == Command.BACKLIGHT_OFF:
            self.backlight = False
        elif cmd_byte == Command.SWITCH_OFF:
            self.is_operate = False

        # ACK format: 0xAA 0xAA 0xAA 0x01 <CMD> <CMD>
        return AMP_SYN + bytes([0x01, cmd_byte, cmd_byte])

    async def _client_connected_handler(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ):
        addr = writer.get_extra_info("peername")
        logger.info(f"Client connected to simulator from {addr}")
        buffer = bytearray()

        try:
            while self._running:
                data = await reader.read(256)
                if not data:
                    break
                buffer.extend(data)

                # Look for command packet: 0x55 0x55 0x55 CNT CMD CHK
                while len(buffer) >= 6:
                    idx = buffer.find(HOST_SYN)
                    if idx == -1:
                        buffer.clear()
                        break
                    if idx > 0:
                        del buffer[:idx]

                    if len(buffer) < 6:
                        break

                    cnt = buffer[3]
                    cmd = buffer[4]
                    chk = buffer[5]

                    if cmd != chk:
                        # Corrupted byte, remove one byte and retry
                        del buffer[0]
                        continue

                    # Valid command packet recognized!
                    del buffer[:6]

                    if cmd == Command.STATUS:
                        payload = self.build_67byte_status_payload()
                        resp = build_status_packet(payload)
                        writer.write(resp)
                        await writer.drain()
                    else:
                        ack = self.handle_command(cmd)
                        writer.write(ack)
                        await writer.drain()
        except asyncio.CancelledError:
            pass
        except Exception as err:
            logger.warning(f"Error handling simulator client: {err}")
        finally:
            writer.close()
            await writer.wait_closed()
            logger.info(f"Client {addr} disconnected from simulator")

    async def start(self):
        """Start the simulated TCP server."""
        self._running = True
        self._server = await asyncio.start_server(
            self._client_connected_handler, self.host, self.port
        )
        logger.info(f"SPE Expert Simulator listening on {self.host}:{self.port}")

    async def stop(self):
        """Stop the simulated TCP server."""
        self._running = False
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            logger.info("SPE Expert Simulator stopped")
