from __future__ import annotations

import json
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .access_config import AccessCredential, AccessProfile, load_access_profiles


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
    access_profile: str
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
            access_profile=config.get("access_profile", "default"),
            port=int(config.get("port", 22)),
        )
    return devices


def resolve_credential(
    device: Device,
    access_profiles: dict[str, AccessProfile],
    role: str,
) -> AccessCredential:
    if device.access_profile not in access_profiles:
        raise PermissionError(
            f"Device {device.name} references unknown access profile "
            f"{device.access_profile}."
        )
    return access_profiles[device.access_profile].credential_for_role(role)


def validate_command(
    command: str,
    role: str = "readonly",
    allow_state_changing: bool = False,
) -> None:
    normalized = command.strip()
    if not normalized:
        raise ValueError("Command must not be empty.")
    if role == "readonly" or not allow_state_changing:
        if not normalized.startswith("show "):
            raise ValueError("Only Junos show commands are allowed.")

        tokens = {
            token.strip().lower()
            for token in normalized.replace("|", " ").replace(";", " ").split()
        }
        blocked = sorted(tokens & BLOCKED_TOKENS)
        if blocked:
            raise ValueError(f"Blocked non-read-only token(s): {', '.join(blocked)}")


def validate_readonly_command(command: str) -> None:
    validate_command(command, role="readonly")


def run_command(
    device: Device,
    command: str,
    access_profiles: dict[str, AccessProfile],
    role: str = "readonly",
    allow_state_changing: bool = False,
    timeout: int = 30,
) -> str:
    validate_command(command, role=role, allow_state_changing=allow_state_changing)
    credential = resolve_credential(device, access_profiles, role)

    ssh_command = [
        "ssh",
        "-i",
        str(credential.identity_file),
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
        f"{credential.username}@{device.host}",
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


def run_show_command(
    device: Device,
    command: str,
    access_profiles: dict[str, AccessProfile],
    timeout: int = 30,
) -> str:
    return run_command(
        device,
        command,
        access_profiles=access_profiles,
        role="readonly",
        timeout=timeout,
    )


def collect(
    device: Device,
    commands: list[str],
    access_profiles: dict[str, AccessProfile],
    role: str = "readonly",
    allow_state_changing: bool = False,
) -> dict[str, Any]:
    output: dict[str, Any] = {
        "device": device.name,
        "host": device.host,
        "role": role,
        "results": [],
    }
    for command in commands:
        output["results"].append(
            {
                "command": command,
                "output": run_command(
                    device,
                    command,
                    access_profiles=access_profiles,
                    role=role,
                    allow_state_changing=allow_state_changing,
                ),
            }
        )
    return output


def load_inventory_and_access(
    inventory_path: str | Path,
    access_config_path: str | Path,
) -> tuple[dict[str, Device], dict[str, AccessProfile]]:
    return load_inventory(inventory_path), load_access_profiles(access_config_path)
