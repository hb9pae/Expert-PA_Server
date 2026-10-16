#!/usr/bin/env python3
"""CLI runner for SPE Expert PA Monitoring Server."""

import argparse
import asyncio
import logging
import sys
import uvicorn
from expertpa.server.app import create_app
from expertpa.server.config import ServerConfig
from expertpa.simulator.pa_simulator import PASimulator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("expertpa.main")


async def run_server(args):
    simulator = None
    if args.simulator:
        logger.info(
            f"Starting integrated SPE PA simulator on {args.pa_host}:{args.pa_port}..."
        )
        simulator = PASimulator(host=args.pa_host, port=args.pa_port)
        await simulator.start()

    config = ServerConfig(
        ser2net_host=args.pa_host,
        ser2net_port=args.pa_port,
        poll_interval_ms=args.poll_interval,
        api_host=args.host,
        api_port=args.port,
    )

    app = create_app(config)

    print("=================================================================")
    print(" SPE Expert PA Monitoring Server")
    print(f" Target ser2net PA: {args.pa_host}:{args.pa_port}")
    print(f" Polling interval:  {args.poll_interval} ms")
    print(f" REST API:          http://{args.host}:{args.port}/api/status")
    print(f" Swagger API Docs:  http://{args.host}:{args.port}/docs")
    print(f" WebSocket Stream:  ws://{args.host}:{args.port}/ws/telemetry")
    if args.simulator:
        print(" PA Simulator:      ACTIVE (local mock)")
    print("=================================================================")

    uvicorn_config = uvicorn.Config(
        app,
        host=args.host,
        port=args.port,
        log_level="info",
        access_log=False,
    )
    server = uvicorn.Server(uvicorn_config)

    try:
        await server.serve()
    finally:
        if simulator:
            logger.info("Stopping integrated PA simulator...")
            await simulator.stop()


def main():
    parser = argparse.ArgumentParser(
        description="SPE Expert PA Monitoring Server (Raspberry Pi & Desktop)"
    )
    parser.add_argument(
        "--pa-host",
        default="192.168.84.220",
        help="IP address of ser2net device / Raspberry Pi (default: 192.168.84.220)",
    )
    parser.add_argument(
        "--pa-port",
        type=int,
        default=22000,
        help="TCP port of ser2net (default: 22000)",
    )
    parser.add_argument(
        "--poll-interval",
        type=int,
        default=200,
        help="Status poll interval in milliseconds (default: 200 ms)",
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host address for FastAPI HTTP/WS server (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port for FastAPI HTTP/WS server (default: 8000)",
    )
    parser.add_argument(
        "--simulator",
        action="store_true",
        help="Run with integrated local PA hardware simulator on pa-host:pa-port",
    )
    args = parser.parse_args()

    # In simulator mode on localhost, default pa-host to 127.0.0.1 if user left default
    if args.simulator and args.pa_host == "192.168.84.220":
        args.pa_host = "127.0.0.1"

    try:
        asyncio.run(run_server(args))
    except KeyboardInterrupt:
        print("\nServer shutdown completed.")


if __name__ == "__main__":
    main()
