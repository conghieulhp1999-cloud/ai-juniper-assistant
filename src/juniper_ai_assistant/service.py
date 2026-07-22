from __future__ import annotations

import argparse
import json
import logging
import os
import signal
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from .access_config import load_access_profiles
from .accounts import AccountStore
from .ai_config import load_ai_providers
from .collector import load_inventory


LOGGER = logging.getLogger("juniper_ai_assistant.service")


@dataclass(frozen=True)
class ServiceConfig:
    inventory: Path
    access_config: Path
    accounts: Path
    ai_config: Path
    interval: int = 60


def load_service_config_from_env() -> ServiceConfig:
    return ServiceConfig(
        inventory=Path(os.environ.get("JUNIPER_AI_INVENTORY", "config/devices.local.json")),
        access_config=Path(
            os.environ.get("JUNIPER_AI_ACCESS_CONFIG", "config/juniper-access.local.json")
        ),
        accounts=Path(os.environ.get("JUNIPER_AI_ACCOUNTS", "config/accounts.local.json")),
        ai_config=Path(
            os.environ.get("JUNIPER_AI_PROVIDERS", "config/ai-providers.local.json")
        ),
        interval=int(os.environ.get("JUNIPER_AI_SERVICE_INTERVAL", "60")),
    )


def validate_service_config(config: ServiceConfig) -> dict:
    devices = load_inventory(config.inventory)
    access_profiles = load_access_profiles(config.access_config)
    accounts = AccountStore(config.accounts).load_raw().get("accounts", {})
    providers = load_ai_providers(config.ai_config)

    missing_access_profiles = sorted(
        {
            device.access_profile
            for device in devices.values()
            if device.access_profile not in access_profiles
        }
    )
    if missing_access_profiles:
        raise ValueError(
            "Device inventory references unknown access profile(s): "
            + ", ".join(missing_access_profiles)
        )

    missing_env = sorted(
        {
            provider.api_key_env
            for provider in providers.values()
            if provider.api_key_env and provider.api_key_env not in os.environ
        }
    )

    return {
        "devices": len(devices),
        "access_profiles": len(access_profiles),
        "accounts": len(accounts),
        "ai_providers": len(providers),
        "missing_ai_key_env": missing_env,
    }


class ShutdownFlag:
    def __init__(self) -> None:
        self.stop = False

    def request_stop(self, signum: int, _frame) -> None:
        LOGGER.info("received shutdown signal", extra={"signal": signum})
        self.stop = True


def run_service(config: ServiceConfig) -> int:
    shutdown = ShutdownFlag()
    signal.signal(signal.SIGTERM, shutdown.request_stop)
    signal.signal(signal.SIGINT, shutdown.request_stop)

    LOGGER.info("service starting", extra={"config": asdict(config)})
    try:
        summary = validate_service_config(config)
    except Exception:
        LOGGER.exception("service config validation failed")
        return 1

    LOGGER.info("service config loaded", extra={"summary": summary})
    while not shutdown.stop:
        LOGGER.info("service heartbeat", extra={"summary": summary})
        time.sleep(max(config.interval, 5))

    LOGGER.info("service stopped")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the Juniper AI Assistant service.")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate service configuration and exit.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(
        level=os.environ.get("JUNIPER_AI_LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    args = build_parser().parse_args(argv)
    config = load_service_config_from_env()

    if args.check:
        try:
            summary = validate_service_config(config)
        except Exception as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(json.dumps(summary, indent=2))
        return 0

    return run_service(config)


if __name__ == "__main__":
    raise SystemExit(main())
