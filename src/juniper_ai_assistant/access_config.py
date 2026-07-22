from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


ROLES = {"readonly", "superuser"}


@dataclass(frozen=True)
class AccessCredential:
    role: str
    username: str
    identity_file: Path


@dataclass(frozen=True)
class AccessProfile:
    name: str
    credentials: dict[str, AccessCredential]

    def credential_for_role(self, role: str) -> AccessCredential:
        if role not in ROLES:
            raise PermissionError(f"Unknown role: {role}")
        if role not in self.credentials:
            raise PermissionError(f"Access profile {self.name} has no {role} credential.")
        return self.credentials[role]


def load_access_profiles(path: str | Path) -> dict[str, AccessProfile]:
    config_path = Path(path).expanduser()
    with config_path.open("r", encoding="utf-8") as fh:
        raw = json.load(fh)

    profiles: dict[str, AccessProfile] = {}
    for name, config in raw.get("profiles", {}).items():
        credentials = {
            role: AccessCredential(
                role=role,
                username=credential["username"],
                identity_file=Path(credential["identity_file"]).expanduser(),
            )
            for role, credential in config.get("credentials", {}).items()
        }
        profiles[name] = AccessProfile(name=name, credentials=credentials)
    return profiles


def write_access_config(
    path: str | Path,
    readonly_username: str,
    readonly_identity_file: str,
    superuser_username: str,
    superuser_identity_file: str,
    profile_name: str = "default",
) -> None:
    config_path = Path(path).expanduser()
    config_path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "profiles": {
            profile_name: {
                "credentials": {
                    "readonly": {
                        "username": readonly_username,
                        "identity_file": readonly_identity_file,
                    },
                    "superuser": {
                        "username": superuser_username,
                        "identity_file": superuser_identity_file,
                    },
                }
            }
        }
    }
    with config_path.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
        fh.write("\n")
    config_path.chmod(0o600)
