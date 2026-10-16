#!/usr/bin/env python3
"""CLI runner for SPE Expert Amplifier Simulator."""

import argparse
import asyncio
import logging
from expertpa.simulator.pa_simulator import PASimulator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


async def main():
    parser = argparse.ArgumentParser(description="SPE Expert PA Hardware Simulator")
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host address to bind the simulator to (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=22000,
        help="TCP port to listen on, mimicking ser2net (default: 22000)",
    )
    parser.add_argument(
        "--model",
        default="20K",
        choices=["20K", "1.3K", "1.5K"],
        help="Simulated PA model (default: 20K)",
    )
    args = parser.parse_args()

    sim = PASimulator(host=args.host, port=args.port, model=args.model)
    await sim.start()
    print(f"============================================================")
    print(f" SPE Expert {args.model} Simulator active on {args.host}:{args.port}")
    print(f" Simulating ser2net /dev/ttyUSB0 (115200 8N1)")
    print(f" Press Ctrl+C to terminate.")
    print(f"============================================================")

    stop_event = asyncio.Event()
    try:
        await stop_event.wait()
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
        await sim.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nSimulator shut down.")
