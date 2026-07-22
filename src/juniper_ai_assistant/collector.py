from __future__ import annotations

import json
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


BLOCKED_TOKENS = {
    "clear",
    "commit",
    "configure",
    "delete",
    "edit",
    "file",
    "load",
    "reboot",
    "request",
    "restart",
    "rollback",
    "set",
    "start",
}


@dataclass(frozen=True)
class Device:
    name: str
    host: str
    username: str
    identity_file: Path
    port: int = 22


def load_inventory(path: str | Path) -> dict[str, Device]:
    inventory_path = Path(path).expanduser()
    with inventory_path.open("r", encoding="utf-8") as fh:
        raw = json.load(fh)

    devices: dict[str, Device] = {}
    for name, config in raw.get("devices", {}).items():
        devices[name] = Device(
            name=name,
            host=config["host"],
            username=config["username"],
            identity_file=Path(config["identity_file"]).expanduser(),
            port=int(config.get("port", 22)),
        )
    return devices


def validate_readonly_command(command: str) -> None:
    normalized = command.strip()
    if not normalized:
        raise ValueError("Command must not be empty.")
    if not normalized.startswith("show "):
        raise ValueError("Only Junos show commands are allowed.")

    tokens = {
        token.strip().lower()
        for token in normalized.replace("|", " ").replace(";", " ").split()
    }
    blocked = sorted(tokens & BLOCKED_TOKENS)
    if blocked:
        raise ValueError(f"Blocked non-read-only token(s): {', '.join(blocked)}")


def run_show_command(device: Device, command: str, timeout: int = 30) -> str:
    validate_readonly_command(command)

    ssh_command = [
        "ssh",
        "-i",
        str(device.identity_file),
        "-o",
        "BatchMode=yes",
        "-o",
        "IdentitiesOnly=yes",
        "-o",
        "StrictHostKeyChecking=accept-new",
        "-o",
        f"ConnectTimeout={min(timeout, 10)}",
        "-p",
        str(device.port),
        f"{device.username}@{device.host}",
        command,
    ]

    result = subprocess.run(
        ssh_command,
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if result.returncode != 0:
        safe_command = " ".join(shlex.quote(part) for part in ssh_command[:1])
        raise RuntimeError(
            f"SSH command failed with exit code {result.returncode}. "
            f"Runner={safe_command}. Error={result.stderr.strip()}"
        )
    return result.stdout


def collect(device: Device, commands: list[str]) -> dict[str, Any]:
    output: dict[str, Any] = {"device": device.name, "host": device.host, "results": []}
    for command in commands:
        output["results"].append(
            {
                "command": command,
                "output": run_show_command(device, command),
            }
        )
    return output
