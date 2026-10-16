"""Configuration settings for the Expert PA Monitoring Server."""

import os
from pydantic import BaseModel, Field


class ServerConfig(BaseModel):
    """Runtime configuration for Expert PA server."""

    # ser2net connection settings
    ser2net_host: str = Field(
        default_factory=lambda: os.getenv("EXPERT_PA_HOST", "192.168.84.220")
    )
    ser2net_port: int = Field(
        default_factory=lambda: int(os.getenv("EXPERT_PA_PORT", "22000"))
    )

    # Polling settings
    poll_interval_ms: int = Field(
        default_factory=lambda: int(os.getenv("EXPERT_POLL_INTERVAL_MS", "200"))
    )
    reconnect_interval_s: float = Field(
        default_factory=lambda: float(os.getenv("EXPERT_RECONNECT_INTERVAL_S", "2.0"))
    )
    command_timeout_s: float = Field(
        default_factory=lambda: float(os.getenv("EXPERT_CMD_TIMEOUT_S", "1.0"))
    )

    # Web & API server settings
    api_host: str = Field(
        default_factory=lambda: os.getenv("API_HOST", "0.0.0.0")
    )
    api_port: int = Field(
        default_factory=lambda: int(os.getenv("API_PORT", "8000"))
    )

    @property
    def poll_interval_s(self) -> float:
        return max(0.05, self.poll_interval_ms / 1000.0)
